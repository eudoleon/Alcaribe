from datetime import datetime, timedelta
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT

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

class LibroComprasModelo(models.Model):
    _name = "resumen.monina.pdf"

    name = fields.Char()
    employee_id = fields.Many2one('hr.employee')
    payslip_run_id = fields.Many2one('hr.payslip.run')
    payslip_id = fields.Many2one('hr.payslip')
    currency_id = fields.Many2one('res.currency',default=lambda self: self.env.company.currency_id.id)
    total_deposito = fields.Monetary()
    total_bono = fields.Monetary(default=0)
    total_desc_prestamo = fields.Monetary()
    total_cesta_tiket = fields.Monetary()


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

class WizardReport_1(models.TransientModel): # aqui declaro las variables del wizar que se usaran para el filtro del pdf
    _name = 'wizard.resumen.nomina'
    _description = "Reoirte Resumen Nómina"

    date_from  = fields.Date('Date From', default=lambda *a:(datetime.now() - timedelta(days=(1))).strftime('%Y-%m-%d'))
    date_to = fields.Date(string='Date To', default=lambda *a:datetime.now().strftime('%Y-%m-%d'))
    #lote_bono_id = fields.Many2one('hr.payslip.run')
    #lote_ids = fields.Many2one('hr.payslip.run')
    #lote_bono_id = fields.Many2many('hr.payslip.run')
    lote_ids = fields.Many2many('hr.payslip.run')

    company_id = fields.Many2one('res.company','Company',default=lambda self: self.env.company.id)
    line  = fields.Many2many(comodel_name='resumen.monina.pdf', string='Lineas')

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

    def float_format2(self,valor):
        #valor=self.base_tax
        if valor:
            result = '{:,.2f}'.format(valor)
            result = result.replace(',','*')
            result = result.replace('.',',')
            result = result.replace('*','.')
        else:
            result="0,00"
        return result



    def print_resumen_nomina(self):
        t=self.env['resumen.monina.pdf'].search([])
        w=self.env['wizard.resumen.nomina'].search([('id','!=',self.id)])
        t.unlink()
        w.unlink()
        for slip_run in self.lote_ids:
            if slip_run.tipo_pago_lote!='bono':
                busca_payslip=self.env['hr.payslip'].search([('payslip_run_id','=',slip_run.id)])
                if busca_payslip:
                    for rec in busca_payslip:
                        total_pagado=0
                        total_desc_prestamo=0
                        total_bono=0
                        total_cesta_tiket=0
                        for det in rec.line_ids:
                            if det.code=='NET':
                                total_pagado=det.total
                            if det.code=='DPPEM':
                                total_desc_prestamo=det.total
                        total_bono=self.bono(self.lote_ids,rec.employee_id.id)
                        total_cesta_tiket=self.cesta_tiket(self.lote_ids,rec.employee_id.id)
                        if total_desc_prestamo==0:
                            total_desc_prestamo=self.prestamo(self.lote_ids,rec.employee_id.id)
                        values=({
                            'employee_id':rec.employee_id.id,
                            'payslip_run_id':slip_run.id,
                            'payslip_id':rec.id,
                            'total_deposito':total_pagado,
                            'total_desc_prestamo':total_desc_prestamo,
                            'total_bono':total_bono,
                            'total_cesta_tiket':total_cesta_tiket,
                            })
                        resumen_id = t.create(values)
                    #raise UserError(_('valor = %s')%busca_payslip)
        
        self.line=self.env['resumen.monina.pdf'].search([])
        return {'type': 'ir.actions.report','report_name': 'hr_infor_resumen_nom.reporte_resumen_nomina','report_type':"qweb-pdf"}
        #raise UserError(_('lista_mov_line = %s')%self.line)

    def bono(self,slip_runs,employee_id):
        total_bono=0
        for slip_run in slip_runs:
            #total_bono=0
            if slip_run.tipo_pago_lote=='bono':
                busca_payslip2=self.env['hr.payslip'].search([('payslip_run_id','=',slip_run.id),('employee_id','=',employee_id)])
                if busca_payslip2:
                    for item in busca_payslip2: 
                        for dett in item.line_ids:
                            if dett.code=='NET':
                                total_bono=dett.total
        return total_bono

    def cesta_tiket(self,slip_runs,employee_id):
        total_cesta=0
        for slip_run in slip_runs:
            if slip_run.tipo_pago_lote=='cesta':
                busca_payslip2=self.env['hr.payslip'].search([('payslip_run_id','=',slip_run.id),('employee_id','=',employee_id)])
                if busca_payslip2:
                    for rec in busca_payslip2:
                        for roc in rec.line_ids:
                            if roc.code=='CESTIK':
                                total_cesta=roc.total
        return total_cesta


    def prestamo(self,slip_runs,employee_id):
        prestamo=0
        for slip_run in slip_runs:
            #prestamo=0
            if slip_run.tipo_pago_lote=='bono':
                busca_payslip2=self.env['hr.payslip'].search([('payslip_run_id','=',slip_run.id),('employee_id','=',employee_id)])
                if busca_payslip2:
                    for item in busca_payslip2: 
                        for dett in item.line_ids:
                            if dett.code=='DPPEM':
                                prestamo=dett.total
        return prestamo