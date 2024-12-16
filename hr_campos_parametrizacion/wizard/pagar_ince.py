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
    _name = 'snc.wizard.pagar_ince'
    _description = 'Total a pagar INCE'

    date_from = fields.Date(string='Fecha de Llegada', default=lambda *a:datetime.now().strftime('%Y-%m-%d'))
    trimestre = fields.Selection([('1', '1er Trimestre'),('2','2do Trimestre'),('3','3er Trimestre'),('4','4to Trimestre')])
    company_id = fields.Many2one('res.company','Company',default=lambda self: self.env.company.id)
    line  = fields.Many2many(comodel_name='hr.resumen.pago_ince', string='Lineas')
    ano = fields.Char()
    ret_patrono = fields.Float(compute='_compute_retenciones')
    ret_empleado = fields.Float(compute='_compute_retenciones')

    @api.onchange('trimestre')
    def _compute_retenciones(self):
        aux1=aux2=0
        busca=self.env['hr.payroll.indicadores.economicos'].search(['|',('code','=','INP'),('code','=','INE')])
        if busca:
            for rec in busca:
                if rec.code=='INP':
                    aux1=rec.valor
                if rec.code=='INE':
                    aux2=rec.valor
        self.ret_patrono=aux1
        self.ret_empleado=aux2

    def ano(self,date):
        fecha = str(date)
        fecha_aux=fecha
        ano=fecha_aux[0:4]  
        resultado=ano
        return int(resultado)

    def mes(self,date):
        fecha = str(date)
        fecha_aux=fecha
        mes=fecha[5:7]
        resultado=mes
        return int(resultado)

    def action_generate_reporte(self):
        monto_1=monto_2=monto_3=0
        ano=str(self.ano(self.date_from))
        self.ano=ano
        if self.trimestre=='1':
            fecha_desde=ano+"-01-01"
            fecha_hasta=ano+"-03-31"
        if self.trimestre=='2':
            fecha_desde=ano+"-04-01"
            fecha_hasta=ano+"-06-30"
        if self.trimestre=='3':
            fecha_desde=ano+"-07-01"
            fecha_hasta=ano+"-09-30"
        if self.trimestre=='4':
            fecha_desde=ano+"-10-01"
            fecha_hasta=ano+"-12-31"
        #fecha_desde=datetime.strptime(str(fecha_desde),'%Y-%m-%d')
        fecha_desde=str(fecha_desde)
        fecha_hasta=str(fecha_hasta)
        t=self.env['hr.resumen.pago_ince']
        d=t.search([]).unlink()
        #raise UserError(_('payslip=%s')%fecha_hasta)
        nom_ince=self.env['hr.config.ince'].search([('activo','=',True)])
        if nom_ince:
            for det in nom_ince:
                pagos_nomina=det.id
                payslip=self.env['hr.payslip'].search([('struct_id','=',det.tipo_pago_id.id),('date_from','>=',fecha_desde),('date_to','<=',fecha_hasta),('state','=','done')],order='employee_id ASC,date_from ASC')
                monto_1=monto_2=monto_3=monto_4=0
                employee_aux=0
                mes_aux=0
                if payslip:
                    for rec in payslip:
                        ########## TRIMESTRE 1 #########
                        if str(rec.date_from) >=ano+'-01-01' and str(rec.date_to)<=ano+'-03-31':
                            if mes_aux!=rec.mes(rec.date_from) or employee_aux!=rec.employee_id.id:
                                if rec.mes(rec.date_from)==1:
                                    monto_1=monto_1+rec.employee_id.salario
                                if rec.mes(rec.date_from)==2:
                                    monto_2=monto_2+rec.employee_id.salario
                                if rec.mes(rec.date_from)==3:
                                    monto_3=monto_3+rec.employee_id.salario
                                employee_aux=rec.employee_id.id
                                mes_aux=rec.mes(rec.date_from)

                        ########## TRIMESTRE 2 #########
                        if str(rec.date_from) >=ano+'-04-01' and str(rec.date_to)<=ano+'-06-31':
                            if mes_aux!=rec.mes(rec.date_from) or employee_aux!=rec.employee_id.id:
                                if rec.mes(rec.date_from)==4:
                                    monto_1=monto_1+rec.employee_id.salario
                                if rec.mes(rec.date_from)==5:
                                    monto_2=monto_2+rec.employee_id.salario
                                if rec.mes(rec.date_from)==6:
                                    monto_3=monto_3+rec.employee_id.salario
                                employee_aux=rec.employee_id.id
                                mes_aux=rec.mes(rec.date_from)

                        ########## TRIMESTRE 3 #########
                        if str(rec.date_from) >=ano+'-07-01' and str(rec.date_to)<=ano+'-09-31':
                            if mes_aux!=rec.mes(rec.date_from) or employee_aux!=rec.employee_id.id:
                                if rec.mes(rec.date_from)==7:
                                    monto_1=monto_1+rec.employee_id.salario
                                if rec.mes(rec.date_from)==8:
                                    monto_2=monto_2+rec.employee_id.salario
                                if rec.mes(rec.date_from)==9:
                                    monto_3=monto_3+rec.employee_id.salario
                                employee_aux=rec.employee_id.id
                                mes_aux=rec.mes(rec.date_from)

                        ########## TRIMESTRE 4 #########
                        if str(rec.date_from) >=ano+'-10-01' and str(rec.date_to)<=ano+'-12-31':
                            if mes_aux!=rec.mes(rec.date_from) or employee_aux!=rec.employee_id.id:
                                if rec.mes(rec.date_from)==10:
                                    monto_1=monto_1+rec.employee_id.salario
                                if rec.mes(rec.date_from)==11:
                                    monto_2=monto_2+rec.employee_id.salario
                                if rec.mes(rec.date_from)==12:
                                    monto_3=monto_3+rec.employee_id.salario
                                employee_aux=rec.employee_id.id
                                mes_aux=rec.mes(rec.date_from)

                    values={
                    'pagos_nomina':pagos_nomina,
                    'cuota_1':monto_1,
                    'cuota_2':monto_2,
                    'cuota_3':monto_3,
                    'cuota_4':monto_4,
                    'trimestre':self.trimestre,
                    }
                    crea=t.create(values)
                    self.line = self.env['hr.resumen.pago_ince'].search([])
                #else:
                    #raise UserError(_('No hay nomina ejecutadas en el trimestre %s')%self.trimestre)
        return {'type': 'ir.actions.report','report_name': 'hr_campos_parametrizacion.reporte_monto_ince','report_type':"qweb-pdf"}


class ResumenPagoInce(models.Model):
    _name = "hr.resumen.pago_ince"

    company_id = fields.Many2one('res.company','Company',default=lambda self: self.env.company.id)
    trimestre = fields.Char() 
    pagos_nomina = fields.Many2one('hr.config.ince')
    currency_id = fields.Many2one('res.currency',default=lambda self: self.env.company.currency_id.id,string="Moneda de pago")
    cuota_1 = fields.Monetary()
    cuota_2 = fields.Monetary()
    cuota_3 = fields.Monetary()
    cuota_4 = fields.Monetary()