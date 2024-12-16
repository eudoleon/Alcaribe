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

class LoteResumen(models.Model):# 1
    _name = "pre.nomina.resu_lote"

    payslip_run_id = fields.Many2one('hr.payslip.run')
    line_departamento = fields.One2many('pre.nomina.resu_dep','lote_run_id', string='Lineas')
    line_analytic_account = fields.One2many('pre.analytic.account','lote_run_id')


class PreNominaResumido(models.Model):
    _name = "pre.nomina.resu_dep"

    lote_run_id = fields.Many2one('pre.nomina.resu_lote')
    department_id = fields.Many2one('hr.department')
    line_rule  = fields.One2many('pre.nomina.resu_concepto','department_res_id', string='Lineas')


class PreNominaResumidoReglas(models.Model):
    _name = "pre.nomina.resu_concepto"

    department_res_id = fields.Many2one('pre.nomina.resu_dep')
    cuenta_ana_id = fields.Many2one('pre.analytic.account')
    salary_rule_id = fields.Many2one('hr.salary.rule')
    total = fields.Float()


class DepartamentoTemp(models.Model):
    _name = "hr.department2"

    department_id=fields.Many2one('hr.department')


class LibroComprasModelo(models.Model):
    _name = "pre.monina.pdf"

    #name = fields.Char()
    employee_id = fields.Many2one('hr.employee')
    payslip_run_id = fields.Many2one('hr.payslip.run')
    payslip_id = fields.Many2one('hr.payslip')

    #currency_id = fields.Many2one('res.currency',default=lambda self: self.env.company.currency_id.id)
    #total_deposito = fields.Monetary()
    #total_bono = fields.Monetary(default=0)
    #total_desc_prestamo = fields.Monetary()


class CuentaAnaliticaAux(models.Model): #2
    _name = "pre.analytic.account"

    lote_run_id = fields.Many2one('pre.nomina.resu_lote')
    account_analytic_id = fields.Many2one('account.analytic.account')
    line_rule  = fields.One2many('pre.nomina.resu_concepto','cuenta_ana_id', string='Lineas')



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
    _name = 'wizard.pre.nomina'
    _description = "Reoirte Resumen Nómina"

    #date_from  = fields.Date('Date From', default=lambda *a:(datetime.now() - timedelta(days=(1))).strftime('%Y-%m-%d'))
    #date_to = fields.Date(string='Date To', default=lambda *a:datetime.now().strftime('%Y-%m-%d'))
    fecha = fields.Datetime(default=fields.Datetime.now)
    lote_ids = fields.Many2many('hr.payslip.run')
    departamento = fields.Many2many('hr.department')
    tip_report = fields.Selection([('d', 'Detallado'),('r', 'Resumido'),('c', 'Cuenta Analitica')],default='d')
    company_id = fields.Many2one('res.company','Company',default=lambda self: self.env.company.id)
    line  = fields.Many2many(comodel_name='pre.monina.pdf', string='Lineas')
    line_lote  = fields.Many2many(comodel_name='pre.nomina.resu_lote', string='Lineas')

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



    def print_pre_nomina(self):
        t=self.env['pre.monina.pdf'].search([])
        w=self.env['wizard.pre.nomina'].search([('id','!=',self.id)])
        z=self.env['hr.department2'].search([])
        t.unlink()
        w.unlink()
        z.unlink()

        for slip_run in self.lote_ids:
            busca_payslip=self.env['hr.payslip'].search([('payslip_run_id','=',slip_run.id)])
            if busca_payslip:
                for rec in busca_payslip:
                    values=({
                        'employee_id':rec.employee_id.id,
                        'payslip_run_id':slip_run.id,
                        'payslip_id':rec.id,
                        })
                    pre_id = t.create(values)
                    self.funcion_departamento(rec.employee_id.department_id.id)
        self.line=self.env['pre.monina.pdf'].search([])

        if not self.departamento:
            lista_dep=self.env['hr.department2'].search([])
            listt=[]
            if lista_dep:
                for item in lista_dep:
                    if item.department_id:
                        listt.append(item.department_id.id)
                self.departamento=listt

        return {'type': 'ir.actions.report','report_name': 'hr_rep_pre_nomina.reporte_pre_nomina','report_type':"qweb-pdf"}

    def funcion_departamento(self,id_departamento):
        valida = self.env['hr.department2'].search([('department_id','=',id_departamento)])
        if not valida:
            vols=({
                'department_id':id_departamento,
                })
            self.env['hr.department2'].create(vols)


    def print_pre_nomina_resumen(self):
        x=self.env['pre.nomina.resu_lote'].search([])
        y=self.env['pre.nomina.resu_dep'].search([])
        z=self.env['pre.nomina.resu_concepto'].search([])
        x.unlink()
        y.unlink()
        z.unlink()
        for det in self.lote_ids:
            values=({
                'payslip_run_id':det.id,
                })
            x.create(values)

        for det in self.env['pre.nomina.resu_lote'].search([]):
            lista_payslip=self.env['hr.payslip'].search([('payslip_run_id','=',det.payslip_run_id.id)])
            #raise UserError(_('lista_payslip=%s')%lista_payslip)
            for item in lista_payslip:
                if not self.departamento:
                    departamento=item.employee_id.department_id.id
                    busca=self.env['pre.nomina.resu_dep'].search([('department_id','=',departamento),('lote_run_id','=',det.id)])
                    if not busca:
                        registros=({
                            'department_id':departamento,#item.employee_id.department_id.id,
                            'lote_run_id':det.id
                            })
                        self.env['pre.nomina.resu_dep'].create(registros)
                else:
                    for departamento in self.departamento:
                        busca=self.env['pre.nomina.resu_dep'].search([('department_id','=',departamento.id),('lote_run_id','=',det.id)])
                        if not busca:
                            registros=({
                                'department_id':departamento.id,#item.employee_id.department_id.id,
                                'lote_run_id':det.id
                                })
                            self.env['pre.nomina.resu_dep'].create(registros)


        for rec in self.env['pre.nomina.resu_lote'].search([]):
            lista_payslip_s=self.env['hr.payslip'].search([('payslip_run_id','=',rec.payslip_run_id.id)])
            if lista_payslip_s:
                for items in lista_payslip_s:
                    departamento=items.employee_id.department_id.id
                    department_res_id=self.get_dep_res(departamento,rec.id)
                    if items.line_ids:
                        for rule in items.line_ids:
                            busca2=self.env['pre.nomina.resu_concepto'].search([('department_res_id','=',department_res_id),('salary_rule_id','=',rule.salary_rule_id.id)])
                            #busca2=self.env['pre.nomina.resu_concepto'].search([('salary_rule_id','=',rule.salary_rule_id.id)])
                            if not busca2 and department_res_id:
                                valores=({
                                    'salary_rule_id':rule.salary_rule_id.id,
                                    'department_res_id':department_res_id,
                                    'total':0, #rule.total,
                                    })
                                self.env['pre.nomina.resu_concepto'].create(valores)
        
        lista_reglas=self.env['pre.nomina.resu_concepto'].search([])
        if lista_reglas:
            for deta in lista_reglas:
                deta.total=self.busca_saldo(deta.salary_rule_id,deta.department_res_id)



        self.line_lote=self.env['pre.nomina.resu_lote'].search([])

        #raise UserError(_('Reporte en Construcción'))

        return {'type': 'ir.actions.report','report_name': 'hr_rep_pre_nomina.reporte_pre_nomina_resu','report_type':"qweb-pdf"}



    def get_dep_res(self,dept_res,lote):
        idd=''
        valida=self.env['pre.nomina.resu_dep'].search([('lote_run_id','=',lote),('department_id','=',dept_res)])
        if valida:
            for roc in valida:
                idd=roc.id
        return idd

    def busca_saldo(self,rule_id,dep_res_id):
        valor=0
        cursor=self.env['hr.payslip.line'].search([('salary_rule_id','=',rule_id.id),('slip_id.payslip_run_id','=',dep_res_id.lote_run_id.payslip_run_id.id),('slip_id.employee_id.department_id','=',dep_res_id.department_id.id)])
        #cursor=self.env['hr.payslip.line'].search([('salary_rule_id','=',rule_id.id),('slip_id.payslip_run_id','=',dep_res_id.lote_run_id.payslip_run_id.id)])
        #raise UserError(_('cursor=%s')%cursor)
        if cursor:
            for rec in cursor:
                valor=valor+rec.total
        return valor

    def print_pre_nomina_cuenta_analyc(self):
        #raise UserError(_('En construccion'))
        x=self.env['pre.nomina.resu_lote'].search([])
        y=self.env['pre.analytic.account'].search([])
        z=self.env['pre.nomina.resu_concepto'].search([])
        x.unlink()
        y.unlink()
        z.unlink()
        for det in self.lote_ids:
            values=({
                'payslip_run_id':det.id,
                })
            x.create(values)
        for det in self.env['pre.nomina.resu_lote'].search([]):
            lista_payslip=self.env['hr.payslip'].search([('payslip_run_id','=',det.payslip_run_id.id)])
            #raise UserError(_('valor=%s')%lista_payslip)
            for item in lista_payslip:
                #raise UserError(_('valor=%s')%item.line_ids)
                if item.employee_id.contract_id.analytic_account_id:
                    self.registra_cuenta(det,item.employee_id.contract_id.analytic_account_id)
                
                #if item.line_ids:
                    #for line in item.line_ids:
                        #raise UserError(_('valor=%s')%line.salary_rule_id.analytic_account_id)
                        #if line.salary_rule_id.analytic_account_id:
                            #self.registra_cuenta(det,line.salary_rule_id.analytic_account_id)

        for rec in self.env['pre.nomina.resu_lote'].search([]):
            for line_ana in rec.line_analytic_account:
                id_cta_anali=line_ana.account_analytic_id
                id_lote=rec.payslip_run_id
                #raise UserError(_('valor=%s')%id_cta_anali)
                lista=self.env['hr.payslip.line'].search([('slip_id.payslip_run_id','=',rec.payslip_run_id.id),('slip_id.employee_id.contract_id.analytic_account_id','=',line_ana.account_analytic_id.id)])
                if lista:
                    for roc in lista:
                        busca=self.env['pre.nomina.resu_concepto'].search([('cuenta_ana_id','=',line_ana.id),('salary_rule_id','=',roc.salary_rule_id.id)])
                        if not busca:
                            registro=({
                                'cuenta_ana_id':line_ana.id,
                                'salary_rule_id':roc.salary_rule_id.id,
                                'total':roc.total,
                                })
                            self.env['pre.nomina.resu_concepto'].create(registro)
                        else:
                            for deta in busca:
                                deta.total=deta.total+roc.total

        self.line_lote=self.env['pre.nomina.resu_lote'].search([])
        return {'type': 'ir.actions.report','report_name': 'hr_rep_pre_nomina.reporte_pre_cta_analyt','report_type':"qweb-pdf"}



    def registra_cuenta(self,lote,cuenta_ana_id): #3
        #raise UserError(_('valor=%s y %s')%(lote,cuenta_ana_id))
        verifica=self.env['pre.analytic.account'].search([('lote_run_id','=',lote.id),('account_analytic_id','=',cuenta_ana_id.id)])

        if not verifica:
            values=({
                'lote_run_id':lote.id,
                'account_analytic_id':cuenta_ana_id.id,
                })
            self.env['pre.analytic.account'].create(values)




    