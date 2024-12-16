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
    _name = 'snc.wizard.faov'
    _description = 'Generar archivo TXT del FAOV'

    delimiter = '\t'
    quotechar = "'"
    date_from = fields.Date(string='Periodo', default=lambda *a:datetime.now().strftime('%Y-%m-%d'))
    nro_cuenta = fields.Char()
    file_data = fields.Binary('Archivo TXT', filters=None, help="")
    file_name = fields.Char('txt_generacion.txt', size=256, required=False, help="",)
    company_id = fields.Many2one('res.company','Company',default=lambda self: self.env.company.id)

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

    

    def action_generate_txt(self):
        if not self.nro_cuenta:
            raise UserError(_('Ingrese un número de cuenta'))
        cursor=self.env['hr.employee'].search([('company_id','=',self.company_id.id)])
        if not cursor:
            raise UserError(_(' No hay registros de empleados para esta compañia'))

        self.file_name = 'txt_generacion_faov.txt'

        ruta="C:/Odoo 13.0e/server/odoo/rrhh_super/hr_campos_parametrizacion/wizard/txt_generacion_faov.txt" #ruta local
        #ruta="/home/odoo/src/txt_generacion_faov.txt" # ruta odoo sh

        with open(ruta, "w") as file:

            for det in cursor:
                if det.identification_id:
                    if det.tipo_contribuyente:
                        tipo_contribuyente=det.tipo_contribuyente
                    else:
                        tipo_contribuyente='?'
                    file.write(str(tipo_contribuyente))# cedula 1
                    file.write(',')

                    file.write(str(det.identification_id))# cedula 1
                    file.write(',')

                    file.write(delimitador_coma(str(det.name)))# cedula 1
                    file.write(',')

                    if det.salario:
                        salario=(completar_cero(det.salario,11)) # salario 9
                    else:
                        salario='00000000000'
                    file.write(salario)
                    file.write(',')

                    file.write(str(formato_periodo(self.date_from))+ "\n")# cedula 1
                    #file.write(',')


                    #file.write('0' + "\n")

        self.write({'file_data': base64.encodestring(open(ruta, "rb").read()),
                    'file_name': "N%s%s.txt"%(self.nro_cuenta,formato_periodo2(self.date_from)),
                    })

        return self.show_view('Archivo Generado', self._name, 'hr_campos_parametrizacion.snc_wizard_faov_form_view', self.id)

        