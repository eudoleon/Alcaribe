from datetime import datetime, timedelta
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

from odoo import models, fields, api, _, tools
from odoo.exceptions import UserError
import openerp.addons.decimal_precision as dp
import logging

import io
from io import BytesIO

import xlsxwriter
import shutil
import base64
import csv
import xlwt
import xml.etree.ElementTree as ET
class HrEmployeeArcLine(models.Model): #2
    _name = "hr.employee.arc_line"

    employee_arc_id = fields.Many2one('hr.employee.arc')
    nro_mes = fields.Integer()
    mes = fields.Char()
    valor_remuneracion = fields.Float(default=0)
    porcentaje = fields.Float(default=0)
    impuesto_ret = fields.Float(default=0)
    company_id = fields.Many2one('res.company','Company',default=lambda self: self.env.company.id)



class HrEmployeeArc(models.Model): #2
    _name = "hr.employee.arc"

    employee_id = fields.Many2one('hr.employee')
    company_id = fields.Many2one('res.company','Company',default=lambda self: self.env.company.id)
    line_arc  = fields.One2many('hr.employee.arc_line','employee_arc_id', string='Lineas')


class WizardReport_5(models.TransientModel): # aqui declaro las variables del wizar que se usaran para el filtro del pdf
    _name = 'wizard.rep.arc'
    _description = "Reporte Retenciones de ISLR"

    date_from  = fields.Date('Date From', default=lambda *a:(datetime.now() - timedelta(days=(1))).strftime('%Y-%m-%d'))
    date_to = fields.Date(string='Date To', default=lambda *a:datetime.now().strftime('%Y-%m-%d'))
    #fecha = fields.Datetime(default=fields.Datetime.now)
    company_id = fields.Many2one('res.company','Company',default=lambda self: self.env.company.id)
    employee_ids = fields.Many2many('hr.employee')
    line_employee  = fields.Many2many(comodel_name='hr.employee.arc', string='Lineas')

    def rif(self,aux):
        #nro_doc=self.partner_id.vat
        busca_partner = self.env['res.partner'].search([('id','=',aux)])
        for det in busca_partner:
            tipo_doc=busca_partner.doc_type
            nro_doc=str(busca_partner.vat)
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
        resultado=str(tipo_doc)+"-"+str(nro_doc)
        return resultado

    def periodo(self,date):
        fecha = str(date)
        fecha_aux=fecha
        mes=fecha[5:7] 
        resultado=mes
        return resultado

    def formato_fecha(self,date):
        fecha = str(date)
        fecha_aux=fecha
        ano=fecha_aux[0:4]
        mes=fecha[5:7]
        dia=fecha[8:10]  
        resultado=dia+"/"+mes+"/"+ano
        return resultado

    def float_format(self,valor):
        #valor=self.base_tax
        if valor:
            result = '{:,.2f}'.format(valor)
            result = result.replace(',','*')
            result = result.replace('.',',')
            result = result.replace('*','.')
        else:
            result="0,00"
        return result

    def formato_fecha_normal(self,date):
        if not date:
            date=self.date_actual
            fecha = str(date)+' 16:00:00'
        else:
            fecha = str(date)
        fecha_aux=fecha
        ano=fecha_aux[0:4]
        mes=fecha[5:7]
        dia=fecha[8:10]  
        resultado=dia+"/"+mes+"/"+ano
        return resultado

    def formato_hora_normal(self,date):
        if not date:
            date=self.date_actual
            fecha = str(date)+' 16:00:00'
        else:
            fecha = str(date)
        fecha_aux=fecha 
        hora=fecha[11:13]
        minutos=fecha[14:16]
        segundos=fecha[17:19]
        hora_ajus=int(hora)-4
        hora_completa=str(hora_ajus)+':'+minutos+':'+segundos
        resultado=hora_completa
        return resultado



    def print_rep_arc(self):
        t=self.env['hr.employee.arc'].search([])
        w=self.env['wizard.rep.arc'].search([('id','!=',self.id)])
        z=self.env['hr.employee.arc_line'].search([])
        t.unlink()
        w.unlink()
        z.unlink()

        if self.employee_ids:  
            for employee in self.employee_ids:
                values={
                'employee_id':employee.id,
                }
                employee_arc_id=self.env['hr.employee.arc'].create(values)
        else:
            for employee in self.env['hr.employee'].search([]):
                values={
                'employee_id':employee.id,
                }
                employee_arc_id=self.env['hr.employee.arc'].create(values)

        valor=0
        lista=self.env['hr.employee.arc'].search([])
        if lista:
            for det in lista:
                self.construye(det)
                payslip_line=self.env['hr.payslip.line'].search([('salary_rule_id.islr','=',True),('employee_id','=',det.employee_id.id),('date_from','>=',self.date_from),('date_to','<=',self.date_to)],order='date_from asc')
                #raise UserError(_('payslip_line=%s')%payslip_line)
                if payslip_line:
                    for item in payslip_line:
                        self.actualiza(det,item)
                        #valor=valor+item.amount
        #raise UserError(_('valor=%s')%valor)
        self.line_employee=self.env['hr.employee.arc'].search([])
        return {'type': 'ir.actions.report','report_name': 'hr_rep_arc_islr.reporte_arc','report_type':"qweb-pdf"}

       


    def construye(self,det):
        for j in range(13):
            if j!=0:
                if j==1:
                    mes='Enero'
                if j==2:
                    mes='Febrero'
                if j==3:
                    mes='Marzo'
                if j==4:
                    mes='Abril'
                if j==5:
                    mes='Mayo'
                if j==6:
                    mes='Junio'
                if j==7:
                    mes='Julio'
                if j==8:
                    mes='Agosto'
                if j==9:
                    mes='Septiembre'
                if j==10:
                    mes='Octubre'
                if j==11:
                    mes='Noviembre'
                if j==12:
                    mes='Diciembre'

                values={
                'nro_mes':j,
                'employee_arc_id':det.id,
                'mes':mes,
                }
                self.env['hr.employee.arc_line'].create(values)


    def actualiza(self,det,item):
        nro_mes=int(self.periodo(item.date_to))
        busca=self.env['hr.employee.arc_line'].search([('nro_mes','=',nro_mes),('employee_arc_id','=',det.id)])
        if busca:
            for roc in busca:
                valor=roc.impuesto_ret
                valor=valor+item.amount
                roc.impuesto_ret=valor

                valor2=roc.valor_remuneracion
                valor2=valor2+(item.amount/(item.slip_id.contract_id.islr_withholding_value/100))#item.slip_id.sueldo
                roc.valor_remuneracion=valor2

                roc.porcentaje=roc.impuesto_ret*100/roc.valor_remuneracion if roc.valor_remuneracion!=0 else 0
        #raise UserError(_('mes=%s')%nro_mes)