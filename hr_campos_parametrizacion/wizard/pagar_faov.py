# # -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from odoo import models, fields, api, _, tools
from odoo.exceptions import UserError, ValidationError
import openerp.addons.decimal_precision as dp
import logging

import io
from io import BytesIO
from io import StringIO

import xlsxwriter
import shutil
import base64
import csv

import urllib.request

import requests

_logger = logging.getLogger(__name__)

"""def rif_format(valor):
    if valor:
        return valor.replace('-','')
    return '0'"""

def tipo_format(valor):
    if valor and valor=='in_refund':
        return '03'
    return '01'

def float_format(valor):
    if valor:
        result = '{:,.2f}'.format(valor)
        #_logger.info('Result 1: %s' % result)
        result = result.replace(',','')
        #_logger.info('Result 2: %s' % result)
        return result
    return valor

def elimina_espacio(valor):
    if valor:
        result=valor.replace('')

def delimitador_coma(valor):
    #valor=self.base_tax
    if valor:
        valor = valor.replace('.',',')
    else:
        valor="0,00"
    return valor

def completar_cero(campo,digitos):
    valor=len(campo)
    campo=str(campo)
    nro_ceros=digitos-valor+1
    for i in range(1,nro_ceros,1):
        campo=" "+campo
    return campo

def formato_periodo(valor):
        fecha = str(valor)
        fecha_aux=fecha
        ano=fecha_aux[0:4]
        mes=fecha[5:7]
        dia=fecha[8:10]  
        resultado=dia+"-"+mes+"-"+ano
        return resultado

def rif_format(aux,aux_type):
    nro_doc=aux
    tipo_doc=aux_type
    nro_doc=nro_doc.replace('V','')
    nro_doc=nro_doc.replace('v','')
    nro_doc=nro_doc.replace('E','')
    nro_doc=nro_doc.replace('e','')
    nro_doc=nro_doc.replace('G','')
    nro_doc=nro_doc.replace('g','')
    nro_doc=nro_doc.replace('J','')
    nro_doc=nro_doc.replace('j','')
    nro_doc=nro_doc.replace('P','')
    nro_doc=nro_doc.replace('p','')
    nro_doc=nro_doc.replace('-','')
    if tipo_doc=="v":
        tipo_doc="V"
    if tipo_doc=="e":
        tipo_doc="E"
    if tipo_doc=="g":
        tipo_doc="G"
    if tipo_doc=="j":
        tipo_doc="J"
    if tipo_doc=="p":
        tipo_doc="P"
    if tipo_doc=="c":
        tipo_doc="C"
    resultado=str(tipo_doc)+str(nro_doc)
    return resultado
    #raise UserError(_('cedula: %s')%resultado)

class PagarInce(models.TransientModel):
    _name = 'snc.wizard.pagar_faov'
    _description = 'Total a pagar FAOV'

    date_from = fields.Date(string='Fecha Desde', default=lambda *a:datetime.now().strftime('%Y-%m-%d'))
    date_to = fields.Date(string='Fecha Hasta', default=lambda *a:datetime.now().strftime('%Y-%m-%d'))
    grupo_nomina = fields.Many2one('hr.payroll.structure.type')
    company_id = fields.Many2one('res.company','Company',default=lambda self: self.env.company.id)
    line  = fields.Many2many(comodel_name='hr.resumen.pago_faov', string='Lineas')
    ret_patrono = fields.Float(compute='_compute_retenciones')
    ret_empleado = fields.Float(compute='_compute_retenciones')

    @api.onchange('grupo_nomina')
    def _compute_retenciones(self):
        aux1=aux2=0
        busca=self.env['hr.payroll.indicadores.economicos'].search(['|',('code','=','FAOVP'),('code','=','FAOVE')])
        if busca:
            for rec in busca:
                if rec.code=='FAOVP':
                    aux1=rec.valor
                if rec.code=='FAOVE':
                    aux2=rec.valor
        self.ret_patrono=aux1
        self.ret_empleado=aux2

    def action_generate_reporte(self):
        t=self.env['hr.resumen.pago_faov']
        d=t.search([]).unlink()
        empleados = self.env['hr.employee'].search([('contract_id.structure_type_id','=',self.grupo_nomina.id),('contract_id.state','=','open')])
        #raise UserError(_('empelados %s')%empleados)
        if not self.grupo_nomina:
            raise UserError(_('Debe seleccionar el tipo de Nómina.'))
        if empleados:
            for det in empleados:
                employee_id=det.id
                #sueldo_base= det.contract_id.wage
                busca_tipo_nom=self.env['hr.config.faov'].search([('grup_nomina_id','=',self.grupo_nomina.id)])
                #raise UserError(_('busca_tipo_nom %s')%busca_tipo_nom)
                if busca_tipo_nom:
                    for rec in busca_tipo_nom:
                        tipo_pago_id=rec.tipo_pago_id.id  #
                        reglas=rec.line_reglas
                        pagos_nomina=rec.id
                        sueldo_base=self.sueldo_base(employee_id,tipo_pago_id,rec.regla_sueldo_base)
                sueldo_integral=self.calcula(employee_id,tipo_pago_id,reglas)
                asignaciones_adicionales=abs(sueldo_integral-sueldo_base)

                values={
                'employee_id':employee_id,
                'sueldo_base':sueldo_base,
                'sueldo_integral':sueldo_integral,
                'asignaciones_adicionales':asignaciones_adicionales,
                'pagos_nomina':pagos_nomina,
                }
                crea=t.create(values)
            self.line = self.env['hr.resumen.pago_faov'].search([])
        return {'type': 'ir.actions.report','report_name': 'hr_campos_parametrizacion.reporte_monto_faov','report_type':"qweb-pdf"}



    def calcula(self,employee_id,tipo_pago_id,reglas):
        total=0
        pago_nomina=self.env['hr.payslip'].search([('struct_id','=',tipo_pago_id),('state','=','done'),('employee_id','=',employee_id),('date_from','>=',self.date_from),('date_to','<=',self.date_to)])
        #raise UserError(_('reglas %s')%reglas)
        if pago_nomina:
            for slip in pago_nomina:
                if reglas:
                    for salary_regla in reglas:
                        salary_regla.regla_id.id
                        for line_slip in slip.line_ids:
                            if salary_regla.regla_id.id==line_slip.salary_rule_id.id:
                                total=total+line_slip.total
                            #raise UserError(_('line_slip %s')%slip.line_ids)

        return total



    def sueldo_base(self,employee_id,tipo_pago_id,regla_sueldo_base_id):
        totales=0
        pago_nomina=self.env['hr.payslip'].search([('struct_id','=',tipo_pago_id),('state','=','done'),('employee_id','=',employee_id),('date_from','>=',self.date_from),('date_to','<=',self.date_to)])
        if pago_nomina:
            for slip in pago_nomina:
                for line_slip in slip.line_ids:
                    if line_slip.salary_rule_id.id==regla_sueldo_base_id.id:
                        totales=totales+line_slip.total
        return totales



class ResumenPagoFaov(models.Model):
    _name = "hr.resumen.pago_faov"

    company_id = fields.Many2one('res.company','Company',default=lambda self: self.env.company.id)
    pagos_nomina = fields.Many2one('hr.config.faov')
    currency_id = fields.Many2one('res.currency',default=lambda self: self.env.company.currency_id.id,string="Moneda de pago")
    employee_id = fields.Many2one('hr.employee')
    sueldo_base = fields.Monetary()
    asignaciones_adicionales = fields.Monetary()
    sueldo_integral = fields.Monetary()