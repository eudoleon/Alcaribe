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


class HrEmployeeList(models.Model): #2
    _name = "hr.employee.list"

    employee_id = fields.Many2one('hr.employee')
    department_id = fields.Many2one('hr.department')
    company_id = fields.Many2one('res.company','Company',default=lambda self: self.env.company.id)


class WizardReport_6(models.TransientModel): # aqui declaro las variables del wizar que se usaran para el filtro del pdf
    _name = 'wizard.rep.lista_empleados'
    _description = "Reporte Lista Empleados"

    #3date_from  = fields.Date('Date From', default=lambda *a:(datetime.now() - timedelta(days=(1))).strftime('%Y-%m-%d'))
    #date_to = fields.Date(string='Date To', default=lambda *a:datetime.now().strftime('%Y-%m-%d'))
    #fecha = fields.Datetime(default=fields.Datetime.now)
    company_id = fields.Many2one('res.company','Company',default=lambda self: self.env.company.id)
    department_ids = fields.Many2many('hr.department')
    state_contract = fields.Selection([('c', 'Con Contrato'),('s', 'Sin Contratos')])
    line_employee  = fields.Many2many(comodel_name='hr.employee.list', string='Lineas')


    def periodo(self,date):
        fecha = str(date)
        fecha_aux=fecha
        mes=fecha[5:7] 
        resultado=mes
        return resultado

    def formato_fecha(self,date):
        if date:
            fecha = str(date)
            fecha_aux=fecha
            ano=fecha_aux[0:4]
            mes=fecha[5:7]
            dia=fecha[8:10]  
            resultado=dia+"/"+mes+"/"+ano
        else:
            resultado='--'
        return resultado

    def status(self,valor):
        result='Sin Contrato'
        if valor=='draft':
            result='Nuevo'
        if valor=='open':
            result='Activo'
        if valor=='close':
            result='Inactivo'
        if valor=='cancel':
            result='Cancelado'
        return result

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



    def print_rep_list(self):
        t=self.env['hr.employee.list'].search([])
        w=self.env['wizard.rep.lista_empleados'].search([('id','!=',self.id)])
        #z=self.env['hr.employee.arc_line'].search([])
        t.unlink()
        w.unlink()
        #z.unlink()

        if self.department_ids:  
            for department in self.department_ids:
                lista_empleado=self.env['hr.employee'].search([('department_id','=',department.id)],order='department_id asc')
                if lista_empleado:
                    for det in lista_empleado:
                        if self.state_contract=='c':
                            if det.contract_id:
                                values={
                                'employee_id':det.id,
                                'department_id':department.id,
                                }
                                employee_list_id=self.env['hr.employee.list'].create(values)
                        if self.state_contract=='s':
                            if not det.contract_id:
                                values={
                                'employee_id':det.id,
                                'department_id':department.id,
                                }
                                employee_list_id=self.env['hr.employee.list'].create(values)
        else:
            for department in self.env['hr.department'].search([]):
                lista_empleado=self.env['hr.employee'].search([('department_id','=',department.id)],order='department_id asc')
                if lista_empleado:
                    for det in lista_empleado:
                        if self.state_contract=='c':
                            if det.contract_id:
                                values={
                                'employee_id':det.id,
                                'department_id':department.id,
                                }
                                employee_list_id=self.env['hr.employee.list'].create(values)
                        if self.state_contract=='s':
                            if not det.contract_id:
                                values={
                                'employee_id':det.id,
                                'department_id':department.id,
                                }
                                employee_list_id=self.env['hr.employee.list'].create(values)

        self.line_employee=self.env['hr.employee.list'].search([])
        return {'type': 'ir.actions.report','report_name': 'hr_rep_list_empleado.reporte_list','report_type':"qweb-pdf"}