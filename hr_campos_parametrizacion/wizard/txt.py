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

class BsoftContratoReport2(models.TransientModel):
    _name = 'snc.wizard.mintra'
    _description = 'Generar archivo TXT de MINTRA'

    delimiter = '\t'
    quotechar = "'"
    date_from = fields.Date(string='Fecha de Llegada', default=lambda *a:datetime.now().strftime('%Y-%m-%d'))
    date_to = fields.Date(string='Fecha de Salida', default=lambda *a:(datetime.now() + timedelta(days=(1))).strftime('%Y-%m-%d'))
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
        cursor=self.env['hr.employee'].search([('company_id','=',self.company_id.id)])
        if not cursor:
            raise UserError(_(' No hay registros de empleados para esta compañia'))

        self.file_name = 'txt_generacion.txt'

        #ruta="C:/Odoo 13.0e/server/odoo/rrhh_super/hr_campos_parametrizacion/wizard/txt_generacion.txt" #ruta local
        ruta="/home/odoo/src/txt_generacion.txt" # ruta odoo sh

        cabecera="Cedula;Tipo Trabajador;Tipo Contrato;Fecha Ingreso;Cargo;"
        cabecera=cabecera+"Ocupacion;Especializacion;Subproceso;Salario;Jornada;"
        cabecera=cabecera+"Esta Sindicalizado;Labora dia domingo?;Pomedio horas laboradas mes;Promedio hora extras mes;Promedio horas nocturnas mes;"
        caabecera=cabecera+"Carga Familiar;Posee familia con discapacidad?;Hijos beneficios Guarderia;"
        cabecera=cabecera+"Monto beneficio guarderia;Es una mujer Embarazada?"
        with open(ruta, "w") as file:

            file.write(cabecera+ "\n")

            for det in cursor:
                if det.identification_id:
                    file.write(str(det.identification_id))# cedula 1
                    file.write(';')

                    if det.tipo_trabajador:
                        tipo_trabajador=str(det.tipo_trabajador)
                    else:
                        tipo_trabajador=''
                    file.write(tipo_trabajador)# tipo_trabajador 2
                    file.write(';')

                    if det.tipo_contrato:
                        tipo_contrato=str(det.tipo_contrato) # tipo_contrato 3
                    else:
                        tipo_contrato=''
                    file.write(tipo_contrato)
                    file.write(';')

                    if det.fecha_ingreso:
                        fecha_ingreso=str(formato_periodo(det.fecha_ingreso)) # fecha_ingreso 4
                    else:
                        fecha_ingreso=''
                    file.write(fecha_ingreso)
                    file.write(';')

                    if det.job_id:
                        cargo=str(det.job_id.name) # cargo 5
                    else:
                        cargo=''
                    file.write(cargo)
                    file.write(';')

                    if det.ocupacion:
                        ocupacion=str(det.ocupacion) # ocupacion 6
                    else:
                        ocupacion=''
                    file.write(ocupacion)
                    file.write(';')

                    if det.profesion:
                        especializacion=str(det.profesion.name) # especializacion 7
                    else:
                        especializacion=''
                    file.write(especializacion)
                    file.write(';')

                    if det.subproceso:
                        subproceso=str(det.subproceso) # subproceso 8
                    else:
                        subproceso=''
                    file.write(subproceso)
                    file.write(';')

                    if det.salario:
                        salario=delimitador_coma(str(det.salario)) # salario 9
                    else:
                        salario=''
                    file.write(salario)
                    file.write(';')

                    if det.jornada:
                        jornada=str(det.jornada) # jornada 10
                    else:
                        jornada=''
                    file.write(jornada)
                    file.write(';')

                    if det.sindicalizado:
                        sindicalizado=str(det.sindicalizado) # sindicalizado 11
                    else:
                        sindicalizado=''
                    file.write(sindicalizado)
                    file.write(';')

                    if det.lab_domingo:
                        lab_domingo=str(det.lab_domingo) # lab_domingo 12
                    else:
                        lab_domingo=''
                    file.write(lab_domingo)
                    file.write(';')

                    if det.prom_hora_lab:
                        prom_hora_lab=str(int(det.prom_hora_lab)) # prom_hora_lab 13
                    else:
                        prom_hora_lab=''
                    file.write(prom_hora_lab)
                    file.write(';')

                    if det.prom_hora_extras:
                        prom_hora_extras=str(int(det.prom_hora_extras)) # prom_hora_extras 14
                    else:
                        prom_hora_extras=''
                    file.write(prom_hora_extras)
                    file.write(';')

                    if det.prom_hora_noc:
                        prom_hora_noc=str(int(det.prom_hora_noc)) # prom_hora_noc 15
                    else:
                        prom_hora_noc=''
                    file.write(prom_hora_noc)
                    file.write(';')

                    if det.carga_familiar:
                        carga_familiar=str(det.carga_familiar) # carga_familiar 16
                    else:
                        carga_familiar=''
                    file.write(carga_familiar)
                    file.write(';')

                    if det.fam_discap:
                        fam_discap=str(det.fam_discap) # fam_discap 17
                    else:
                        fam_discap=''
                    file.write(fam_discap)
                    file.write(';')

                    if det.hijo_benf_guard:
                        hijo_benf_guard=str(det.hijo_benf_guard) # hijo_benf_guard 18
                    else:
                        hijo_benf_guard=''
                    file.write(hijo_benf_guard)
                    file.write(';')

                    if det.monto_bene_guar:
                        monto_bene_guar=delimitador_coma(str(det.monto_bene_guar)) # monto_bene_guar 19
                    else:
                        monto_bene_guar=''
                    file.write(monto_bene_guar)
                    file.write(';')

                    if det.mujer_embarazad:
                        mujer_embarazad=str(det.mujer_embarazad) # mujer_embarazad 20
                    else:
                        mujer_embarazad=''
                    file.write(mujer_embarazad+ "\n")
                    #file.write(';')

                    #file.write('0' + "\n") #16

        self.write({'file_data': base64.encodestring(open(ruta, "rb").read()),
                    'file_name': "mintra desde %s hasta %s.txt"%(self.date_from,self.date_to),
                    })

        return self.show_view('Archivo Generado', self._name, 'hr_campos_parametrizacion.snc_wizard_mintra_form_view', self.id)