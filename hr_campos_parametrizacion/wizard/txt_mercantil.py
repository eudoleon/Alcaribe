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
        valor = valor.replace(' ',',')
        valor = valor.replace(',,',',')
    else:
        valor="0,00"
    return valor

def completar_cero(campo,digitos):
    entero=int(campo)
    decimal=round(campo-entero,2)
    decimal=str(decimal)
    decimal=decimal.replace('.','')
    cuenta=decimal
    cuenta=len(decimal)
    if cuenta<=2:
        campo=str(round(campo,2))+"0"
    else:
        campo=str(round(campo,2))

    campo=campo.replace('.','')
    valor=len(campo)
    nro_ceros=digitos-valor+1
    for i in range(1,nro_ceros,1):
        campo="0"+campo

    return campo


def completar_cero_cedula(campo,digitos):
    campo=campo.replace('.','')
    cuenta=len(campo)
    nro_ceros=digitos-cuenta+1
    for i in range(1,nro_ceros,1):
        campo="0"+campo
    return campo

def formato_periodo(valor):
        fecha = str(valor)
        fecha_aux=fecha
        ano=fecha_aux[0:4]
        mes=fecha[5:7]
        dia=fecha[8:10]  
        resultado=dia+mes+ano
        return resultado

def formato_periodo2(valor):
        fecha = str(valor)
        fecha_aux=fecha
        ano=fecha_aux[0:4]
        mes=fecha[5:7]
        dia=fecha[8:10]  
        resultado=mes+ano
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



class BsoftContratFaov(models.TransientModel):
    _name = 'snc.wizard.mercantil'
    _description = 'Generar archivo TXT del MERCANTIL'

    delimiter = '\t'
    quotechar = "'"
    date_from = fields.Date(string='Periodo', default=lambda *a:datetime.now().strftime('%Y-%m-%d'))
    payslip_run_id = fields.Many2one('hr.payslip.run')
    forma_de_pago = fields.Selection([('1', 'Abono de cuentas'),('2','Transferencias otros bancos')],default='1')
    bank_ids = fields.Many2one('res.partner.bank')
    file_data = fields.Binary('Archivo TXT', filters=None, help="")
    file_name = fields.Char('txt_generacion.txt', size=256, required=False, help="",)
    company_id = fields.Many2one('res.company','Company',default=lambda self: self.env.company.id)

    def calcula_monto(self,employee_id,slip_id):
        monto=0.0
        xxx=self.env['hr.payslip.line'].search([('employee_id','=',employee_id),('slip_id','=',slip_id),('code','=','NET')])
        if xxx:
            for rec in xxx:
                monto=rec.total
        return monto

    def show_view(self, name, model, id_xml, res_id=None, view_mode='tree,form', nodestroy=True, target='new'):
        context = self._context
        mod_obj = self.env['ir.model.data']
        view_obj = self.env['ir.ui.view']
        module = ""
        view_id = self.env.ref(id_xml).id
        if view_id:
            view = view_obj.browse(view_id)
            view_mode = view.type
        ctx = context.copy()
        ctx.update({'active_model': model})
        res = {'name': name,
                'view_type': 'form',
                'view_mode': view_mode,
                'view_id': view_id,
                'res_model': model,
                'res_id': res_id,
                'nodestroy': nodestroy,
                'target': target,
                'type': 'ir.actions.act_window',
                'context': ctx,
                }
        return res

    


    # def action_generate_txt(self):
    #     if not self.payslip_run_id:
    #         raise UserError(_('Ingrese un lote de pago procesado'))
    #     cursor=self.env['hr.payslip'].search([('payslip_run_id','=',self.payslip_run_id.id)])
    #     if not cursor:
    #         raise UserError(_(' No hay registros para este lote'))

    #     self.file_name = 'txt_generacion_mercantil.txt'


    #     with open(ruta, "w") as file:

    #         for det in cursor:
    #             if det.employee_id:
    #                 file.write('2')
    #                 file.write(',')

    #                 if det.employee_id.tipo_contribuyente:
    #                     tipo_contribuyente=det.employee_id.tipo_contribuyente
    #                 else:
    #                     tipo_contribuyente='?'
    #                 file.write(str(tipo_contribuyente))# cedula 1
    #                 file.write(',')

    #                 if det.employee_id.identification_id:
    #                     identification_id=det.employee_id.identification_id
    #                 else:
    #                     identification_id='?'
    #                 file.write(completar_cero_cedula(identification_id,15))# cedula 1
    #                 file.write(',')

    #                 file.write(self.forma_de_pago)
    #                 file.write(',')

    #                 file.write('000000000000')
    #                 file.write(',')

    #                 file.write('                             ')
    #                 file.write(',')

    #                 file.write(str(self.bank_ids.sanitized_acc_number))
    #                 file.write(',')

    #                 amount=completar_cero(self.calcula_monto(det.employee_id.id,det.id),17)

    #                 file.write(str(amount))
    #                 file.write(',')

    #                 file.write('*' + "\n")

    #     self.write({'file_data': base64.encodestring(open(ruta, "rb").read()),
    #                 'file_name': "%s_%s.txt"%(self.payslip_run_id.name,formato_periodo2(self.date_from)),
    #                 })

    #     return self.show_view('Archivo Generado', self._name, 'hr_campos_parametrizacion.snc_wizard_mercantil_form_view', self.id)
        
    def action_generate_txt(self):
        if not self.payslip_run_id:
            raise UserError(_('Ingrese un lote de pago procesado'))
        cursor = self.env['hr.payslip'].search([('payslip_run_id', '=', self.payslip_run_id.id)])
        if not cursor:
            raise UserError(_('No hay registros para este lote'))

        output = io.StringIO()

        for det in cursor:
            tipo = "PAP"
            id1 = "0114" 
            numero_cuenta = det.contract_id.nr_cuenta 
            valor = self.calcula_monto(det.employee_id.id,det.id) 
            vat = rif_format(det.employee_id.address_home_id.vat,det.employee_id.address_home_id.doc_type) #"V13005699" 
            empleado = det.employee_id.name  

            estructura = f"{tipo}///{id1}/{numero_cuenta}/CTE//{valor}/{vat}/{empleado}/////"
            output.write(estructura + "\n")

        output.seek(0)
        encoded_content = base64.b64encode(output.getvalue().encode('utf-8'))
        output.close()

        # Almacenar el contenido codificado y el nombre del archivo en los campos del modelo
        self.file_data = encoded_content.decode('utf-8')
        self.file_name = f"{self.payslip_run_id.name}_{fields.Date.today()}.txt"
        return self.show_view('Archivo Generado', self._name, 'hr_campos_parametrizacion.snc_wizard_mercantil_form_view', self.id)
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': self._name,
            'res_id': self.id,
            'view_id': self.env.ref('hr_campos_parametrizacion.snc_wizard_mercantil_form_view').id,
            'target': 'new',
            'name': 'Archivo Generado'
        }