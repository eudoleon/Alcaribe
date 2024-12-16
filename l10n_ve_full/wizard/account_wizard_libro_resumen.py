from datetime import datetime, timedelta
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT

from odoo import models, fields, api, _, tools
import logging

import io
from io import BytesIO

import xlsxwriter
import shutil
import base64
import csv
import xlwt

_logger = logging.getLogger(__name__)

class LibroVentasModelo(models.Model):
    _name = "account.wizard.pdf.resumen" 

    name = fields.Date(string='Fecha')

    def formato_fecha2(self,date):
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

    def doc_cedula(self,aux):
        #nro_doc=self.partner_id.vat
        busca_partner = self.env['res.partner'].search([('id','=',aux)])
        for det in busca_partner:
            tipo_doc=busca_partner.nationality
            if busca_partner.rif:
                nro_doc=str(busca_partner.rif)
            else:
                nro_doc="00000000"
            tipo_doc=busca_partner.nationality
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
        resultado=str(tipo_doc)+str(nro_doc)
        return resultado
        #raise UserError(_('cedula: %s')%resultado)

class resumen_libros(models.TransientModel):
    _name = "account.wizard.libro.resumen" ## = nombre de la carpeta.nombre del archivo deparado con puntos

    date_from = fields.Date(string='Date From', default=lambda *a:datetime.now().strftime('%Y-%m-%d'))
    date_to = fields.Date('Date To', default=lambda *a:(datetime.now() + timedelta(days=(1))).strftime('%Y-%m-%d'))

    # fields for download xls
    state = fields.Selection([('choose', 'choose'), ('get', 'get')],default='choose') ##Genera los botones de exportar xls y pdf como tambien el de cancelar
    report = fields.Binary('Prepared file', filters='.xls', readonly=True)
    name = fields.Char('File Name', size=32)
    company_id = fields.Many2one('res.company','Company',default=lambda self: self.env.company)

    line  = fields.Many2many(comodel_name='account.wizard.pdf.resumen', string='Lineas')

    def conv_div_nac(self,valor,selff):
        selff.invoice_id.currency_id.id
        fecha_contable_doc=selff.invoice_id.date
        monto_factura=selff.invoice_id.amount_total
        valor_aux=0
        #raise UserError(_('moneda compañia: %s')%self.company_id.currency_id.id)
        if selff.invoice_id.currency_id.id!=self.company_id.currency_id.id:
            tasa= self.env['account.move'].search([('id','=',selff.invoice_id.id)],order="id asc")
            for det_tasa in tasa:
                monto_nativo=det_tasa.amount_untaxed_signed
                monto_extran=det_tasa.amount_untaxed
                if not det_tasa.amount_untaxed:
                    monto_extran=0.000000000000000000000000000000000000000000001
                valor_aux=abs(monto_nativo/monto_extran)
            rate=round(valor_aux,3)  # LANTA
            #rate=round(valor_aux,2)  # ODOO SH
            resultado=valor*rate
        else:
            resultado=valor
        return resultado
    
    
    def periodo(self,valor):
        fecha = str(valor)
        fecha_aux=fecha
        ano=fecha_aux[0:4]
        mes=fecha[5:7]
        dia=fecha[8:10]  
        resultado=mes+"-"+ano
        return resultado


    def doc_cedula2(self,aux):
        #nro_doc=self.partner_id.vat
        busca_partner = self.env['res.partner'].search([('id','=',aux)])
        for det in busca_partner:
            tipo_doc=busca_partner.nationality
            nro_doc=str(busca_partner.rif)
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
        resultado=str(tipo_doc)+str(nro_doc)
        return resultado

    def ret_iva(self): # calcula las retenciones que han hecho los clientes
        cursor_resumen = self.env['account.move.line.resumen'].search([
            ('fecha_comprobante','>=',self.date_from),
            ('fecha_comprobante','<=',self.date_to),
            #('fecha_fact','<',self.date_from),
            #('fecha_fact','>=',self.date_to),
            ('type','in',('out_invoice','out_refund','out_receipt'))
            ])
        total_ret_iva=0
        for det in cursor_resumen:
        	if det.vat_ret_id.state=="posted":
        		total_ret_iva=total_ret_iva+det.total_ret_iva
        return total_ret_iva

    def debitos_fiscales(self):
        cursor_resumen = self.env['account.move.line.resumen'].search([
            ('fecha_fact','>=',self.date_from),
            ('fecha_fact','<=',self.date_to),
            ('state','=','posted'),
            ('type','in',('out_invoice','out_refund','out_receipt'))
            ])
        total_exento=0
        total_base_general=0
        alicuota_general=0

        base_adicional=0
        alicuota_adicional=0

        base_reducida=0
        alicuota_reducida=0
        for det in cursor_resumen:
            total_exento=total_exento+self.conv_div_nac(det.total_exento,det)
            total_base_general=total_base_general+self.conv_div_nac(det.base_general,det)
            alicuota_general=alicuota_general+self.conv_div_nac(det.alicuota_general,det)
            base_adicional=base_adicional+self.conv_div_nac(det.base_adicional,det)
            alicuota_adicional=alicuota_adicional+self.conv_div_nac(det.alicuota_adicional,det)
            base_reducida=base_reducida+self.conv_div_nac(det.base_reducida,det)
            alicuota_reducida=alicuota_reducida+self.conv_div_nac(det.alicuota_reducida,det)
        values={
        'total_exento':total_exento,
        'total_base_general':total_base_general,
        'alicuota_general':alicuota_general,
        'base_adicional':base_adicional,
        'alicuota_adicional':alicuota_adicional,
        'base_reducida':base_reducida,
        'alicuota_reducida':alicuota_reducida,
        }
        return values

    def creditos_fiscales(self):
        cursor_resumen = self.env['account.move.line.resumen'].search([
            ('fecha_fact','>=',self.date_from),
            ('fecha_fact','<=',self.date_to),
            ('state','=','posted'),
            ('type','in',('in_invoice','in_refund','in_receipt'))
            ])
        total_exento=0
        total_base_general=0
        alicuota_general=0

        base_adicional=0
        alicuota_adicional=0

        base_reducida=0
        alicuota_reducida=0
        for det in cursor_resumen:
            total_exento=total_exento+self.conv_div_nac(det.total_exento,det)
            total_base_general=total_base_general+self.conv_div_nac(det.base_general,det)
            alicuota_general=alicuota_general+self.conv_div_nac(det.alicuota_general,det)
            base_adicional=base_adicional+self.conv_div_nac(det.base_adicional,det)
            alicuota_adicional=alicuota_adicional+self.conv_div_nac(det.alicuota_adicional,det)
            base_reducida=base_reducida+self.conv_div_nac(det.base_reducida,det)
            alicuota_reducida=alicuota_reducida+self.conv_div_nac(det.alicuota_reducida,det)
        values={
        'total_exento':total_exento,
        'total_base_general':total_base_general,
        'alicuota_general':alicuota_general,
        'base_adicional':base_adicional,
        'alicuota_adicional':alicuota_adicional,
        'base_reducida':base_reducida,
        'alicuota_reducida':alicuota_reducida,
        }
        return values

    def get_invoice(self,accion):
        t=self.env['account.wizard.pdf.resumen']
        d=t.search([])
        #d.unlink()
        if accion=="factura":
            cursor_resumen = self.env['account.move.line.resumen'].search([
                ('fecha_fact','>=',self.date_from),
                ('fecha_fact','<=',self.date_to),
                ('state','in',('posted','cancel' )),
                ('type','in',('out_invoice','out_refund','out_receipt'))
                ])
        if accion=="voucher":
            cursor_resumen = self.env['account.move.line.resumen'].search([
                ('fecha_comprobante','>=',self.date_from),
                ('fecha_comprobante','<=',self.date_to),
                ('fecha_fact','<',self.date_from),
                #('fecha_fact','>=',self.date_to),
                ('state_voucher_iva','=','posted'),
                ('type','in',('out_invoice','out_refund','out_receipt'))
                ])
        for det in cursor_resumen:
            alicuota_reducida=0
            alicuota_general=0
            alicuota_adicional=0
            base_adicional=0
            base_reducida=0
            base_general=0
            total_con_iva=0
            total_base=0
            total_exento=0
            if accion=="factura":
                alicuota_reducida=det.alicuota_reducida
                alicuota_general=det.alicuota_general
                alicuota_adicional=det.alicuota_adicional
                base_adicional=det.base_adicional
                base_reducida=det.base_reducida
                base_general=det.base_general
                total_con_iva=det.total_con_iva
                total_base=det.total_base
                total_exento=det.total_exento
            values={
            'name':det.fecha_fact,
            'document':det.invoice_id.name,
            'partner':det.invoice_id.partner_id.id,
            'invoice_number': det.invoice_id.invoice_number,#darrell
            'tipo_doc': det.tipo_doc,
            'invoice_ctrl_number': det.invoice_id.invoice_ctrl_number,
            'sale_total': self.conv_div_nac(det.total_con_iva,det),
            'base_imponible':self.conv_div_nac(det.total_base,det),
            'iva' : self.conv_div_nac(det.total_valor_iva,det),
            'iva_retenido': self.conv_div_nac(det.total_ret_iva,det),
            'retenido': det.vat_ret_id.name,
            'retenido_date':det.vat_ret_id.voucher_delivery_date,
            'state_retantion': det.vat_ret_id.state,
            'state': det.invoice_id.state,
            'currency_id':det.invoice_id.currency_id.id,
            'ref':det.invoice_id.ref,
            'total_exento':self.conv_div_nac(det.total_exento,det),
            'alicuota_reducida':self.conv_div_nac(det.alicuota_reducida,det),
            'alicuota_general':self.conv_div_nac(det.alicuota_general,det),
            'alicuota_adicional':self.conv_div_nac(det.alicuota_adicional,det),
            'base_adicional':self.conv_div_nac(det.base_adicional,det),
            'base_reducida':self.conv_div_nac(det.base_reducida,det),
            'base_general':self.conv_div_nac(det.base_general,det),
            'retenido_reducida':self.conv_div_nac(det.retenido_reducida,det),
            'retenido_adicional':self.conv_div_nac(det.retenido_adicional,det),
            'retenido_general':self.conv_div_nac(det.retenido_general,det),
            'vat_ret_id':det.vat_ret_id.id,
            'invoice_id':det.invoice_id.id,
            }
            pdf_id = t.create(values)
        #   temp = self.env['account.wizard.pdf.ventas'].search([])
        self.line = self.env['account.wizard.pdf.ventas'].search([])



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

# *******************  REPORTE EN EXCEL ****************************
    def generate_xls_report(self):
        self.env['account.wizard.pdf.resumen'].search([]).unlink()
        #self.get_invoice()

        wb1 = xlwt.Workbook(encoding='utf-8')
        ws1 = wb1.add_sheet('Resumen')
        fp = BytesIO()

        header_content_style = xlwt.easyxf("font: name Helvetica size 20 px, bold 1, height 170;")
        header_content_style_c = xlwt.easyxf("font: name Helvetica size 20 px, bold 1, height 170; align: horiz center")
        sub_header_style = xlwt.easyxf("font: name Helvetica size 10 px, bold 1, height 170; borders: left thin, right thin, top thin, bottom thin;")
        sub_header_style_c = xlwt.easyxf("font: name Helvetica size 10 px, bold 1, height 170; borders: left thin, right thin, top thin, bottom thin; align: horiz center")
        sub_header_style_r = xlwt.easyxf("font: name Helvetica size 10 px, bold 1, height 170; borders: left thin, right thin, top thin, bottom thin; align: horiz right")

        header_style = xlwt.easyxf("font: name Helvetica size 10 px, height 170; borders: left thin, right thin, top thin, bottom thin;")
        header_style_c = xlwt.easyxf("font: name Helvetica size 10 px, height 170; borders: left thin, right thin, top thin, bottom thin; align: horiz center")
        header_style_r = xlwt.easyxf("font: name Helvetica size 10 px, height 170; borders: left thin, right thin, top thin, bottom thin; align: horiz right")

        sub_header_content_style = xlwt.easyxf("font: name Helvetica size 10 px, height 170;")
        line_content_style = xlwt.easyxf("font: name Helvetica, height 170;")
        row = 0
        col = 0
        ws1.row(row).height = 500
        # ************ cuerpo del excel
        ws1.write_merge(row,row, 4, 9, "Razón Social:"+" "+str(self.company_id.name), sub_header_style)
        row=row+1
        ws1.write_merge(row, row, 4, 9,"Rif:"+" "+str(self.company_id.partner_id.rif), sub_header_style)
        row=row+1
        ws1.write_merge(row,row, 4, 9, "Resumen de IVA",sub_header_style_c)
        row=row+1
        ws1.write_merge(row,row, 4, 4, "Periodo",header_content_style)
        periodo=self.periodo(self.date_to)
        ws1.write_merge(row,row, 5, 5, periodo,header_content_style)
        ws1.write_merge(row,row, 6, 6, "Desde:",header_content_style_c)
        fec_desde = self.line.formato_fecha2(self.date_from)
        ws1.write_merge(row,row, 7, 7, fec_desde,header_content_style)
        ws1.write_merge(row,row, 8, 8, "Hasta:",header_content_style_c)
        fec_hasta = self.line.formato_fecha2(self.date_to)
        ws1.write_merge(row,row, 9, 9, fec_hasta,header_content_style)

        diccionario=self.debitos_fiscales()
        row=row+2
        ws1.write_merge(row,row, 4, 7, "DÉBITOS FISCALES",sub_header_style)
        ws1.write_merge(row,row, 8, 8, "BASE IMPONIBLE",sub_header_style)
        ws1.write_merge(row,row, 9, 9, "DÉBITO FISCAL",sub_header_style)
        row=row+1
        ws1.write_merge(row,row, 4, 4, (row-5),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Ventas Internas no Gravadas",header_style)
        ws1.write_merge(row,row, 8, 8, diccionario['total_exento'],header_style_r)
        ws1.write_merge(row,row, 9, 9, "0,00",header_style_r)
        row=row+1
        ws1.write_merge(row,row, 4, 4, (row-5),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Ventas de Exportación",header_style)
        ws1.write_merge(row,row, 8, 8, "0,00",header_style_r)
        ws1.write_merge(row,row, 9, 9, "0,00",header_style_r)
        row=row+1
        ws1.write_merge(row,row, 4, 4, (row-5),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Ventas Internas Gravadas por Alicuota General",header_style)
        ws1.write_merge(row,row, 8, 8, diccionario['total_base_general'],header_style_r)
        ws1.write_merge(row,row, 9, 9,diccionario['alicuota_general'],header_style_r)
        row=row+1
        ws1.write_merge(row,row, 4, 4, (row-5),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Ventas Internas Gravadas por Alicuota General más Adicional",header_style)
        ws1.write_merge(row,row, 8, 8, diccionario['base_adicional'],header_style_r)
        ws1.write_merge(row,row, 9, 9, diccionario['alicuota_adicional'],header_style_r)
        row=row+1
        ws1.write_merge(row,row, 4, 4, (row-5),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Ventas Internas Gravadas por Alicuota Reducida",header_style)
        ws1.write_merge(row,row, 8, 8, diccionario['base_reducida'],header_style_r)
        ws1.write_merge(row,row, 9, 9,diccionario['alicuota_reducida'],header_style_r)
        sub_total1=diccionario['total_exento']+diccionario['total_base_general']+diccionario['base_adicional']+diccionario['base_reducida']
        sub_total11=diccionario['alicuota_general']+diccionario['alicuota_adicional']+diccionario['alicuota_reducida']
        row=row+1
        ws1.write_merge(row,row, 4, 4, (row-5),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Total Ventas y Debitos Fiscales para Efectos de Determinación",header_style)
        ws1.write_merge(row,row, 8, 8,sub_total1,header_style_r)
        ws1.write_merge(row,row, 9, 9,sub_total11,header_style_r)
        row=row+1
        ws1.write_merge(row,row, 4, 4, (row-5),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Ajustes a los Débitos Fiscales de Periodos Anteriores.",header_style)
        ws1.write_merge(row,row, 8, 8, "---",header_style_r)
        ws1.write_merge(row,row, 9, 9, "0,00",header_style_r)
        row=row+1
        ws1.write_merge(row,row, 4, 4, (row-5),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Certificados de Débitos Fiscales Exonerados",header_style)
        ws1.write_merge(row,row, 8, 8, "---",header_style_r)
        ws1.write_merge(row,row, 9, 9, "0,00",header_style_r)
        row=row+1
        total11=sub_total11
        ws1.write_merge(row,row, 4, 4, (row-5),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Total Débitos Fiscales:",sub_header_style)
        ws1.write_merge(row,row, 8, 8, "---",sub_header_style_r)
        ws1.write_merge(row,row, 9, 9, total11,sub_header_style_r)

        diccionario2=self.creditos_fiscales()
        row=row+1
        ws1.write_merge(row,row, 4, 7, "CRÉDITO FISCALES",sub_header_style)
        ws1.write_merge(row,row, 8, 8, "BASE IMPONIBLE",sub_header_style)
        ws1.write_merge(row,row, 9, 9, "CRÉDITO FISCAL",sub_header_style)
        row=row+1
        ws1.write_merge(row,row, 4, 4, (row-6),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Compras no Gravadas y/o sin Derecho a Credito Fiscal",header_style)
        ws1.write_merge(row,row, 8, 8,diccionario2['total_exento'],header_style_r)
        ws1.write_merge(row,row, 9, 9, "0,00",header_style_r)
        row=row+1
        ws1.write_merge(row,row, 4, 4, (row-6),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Importaciones No Gravadas",header_style)
        ws1.write_merge(row,row, 8, 8,"0,00",header_style_r)
        ws1.write_merge(row,row, 9, 9, "0,00",header_style_r)
        row=row+1
        ws1.write_merge(row,row, 4, 4, (row-6),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Importaciones Gravadas por Alicuota General",header_style)
        ws1.write_merge(row,row, 8, 8, "0,00",header_style_r)
        ws1.write_merge(row,row, 9, 9, "0,00",header_style_r)
        row=row+1
        ws1.write_merge(row,row, 4, 4, (row-6),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Importaciones Gravadas por Alicuota General más Alicuota Adicional",header_style)
        ws1.write_merge(row,row, 8, 8, "0,00",header_style_r)
        ws1.write_merge(row,row, 9, 9, "0,00",header_style_r)
        row=row+1
        ws1.write_merge(row,row, 4, 4, (row-6),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Importaciones Gravadas por Alicuota Reducida",header_style)
        ws1.write_merge(row,row, 8, 8, "0,00",header_style_r)
        ws1.write_merge(row,row, 9, 9, "0,00",header_style_r)
        row=row+1
        ws1.write_merge(row,row, 4, 4, (row-6),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Compras Gravadas por Alicuota General",header_style)
        ws1.write_merge(row,row, 8, 8,diccionario2['total_base_general'],header_style_r)
        ws1.write_merge(row,row, 9, 9,diccionario2['alicuota_general'],header_style_r)
        row=row+1
        ws1.write_merge(row,row, 4, 4, (row-6),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Compras Gravadas por Alicuota General más Alicuota Adicional",header_style)
        ws1.write_merge(row,row, 8, 8,diccionario2['base_adicional'],header_style_r)
        ws1.write_merge(row,row, 9, 9,diccionario2['alicuota_adicional'],header_style_r)
        row=row+1
        ws1.write_merge(row,row, 4, 4, (row-6),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Compras Gravadas por Alicuota Reducida",header_style)
        ws1.write_merge(row,row, 8, 8,diccionario2['base_reducida'],header_style_r)
        ws1.write_merge(row,row, 9, 9,diccionario2['alicuota_reducida'],header_style_r)
        row=row+1
        sub_total2=diccionario2['total_exento']+diccionario2['total_base_general']+diccionario2['base_adicional']+diccionario2['base_reducida']
        sub_total22=diccionario2['alicuota_general']+diccionario2['alicuota_adicional']+diccionario2['alicuota_reducida']
        ws1.write_merge(row,row, 4, 4, (row-6),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Total Compras y Créditos Fiscales del Período",header_style)
        ws1.write_merge(row,row, 8, 8,sub_total2,header_style_r)
        ws1.write_merge(row,row, 9, 9,sub_total22,header_style_r)

        row=row+1
        ws1.write_merge(row,row, 4, 9, "CALCULO DEL CREDITO DEDUCIBLE",sub_header_style)
        #ws1.write_merge(row,row, 8, 8, "BASE IMPONIBLE",sub_header_style)
        #ws1.write_merge(row,row, 9, 9, "CRÉDITO FISCAL",sub_header_style)
        row=row+1
        ws1.write_merge(row,row, 4, 4, (row-6),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Creditos Fiscales Totalmente Deducibles ",header_style)
        ws1.write_merge(row,row, 8, 8, "0,00",header_style_r)
        ws1.write_merge(row,row, 9, 9,sub_total22,header_style_r)
        row=row+1
        ws1.write_merge(row,row, 4, 4, (row-6),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Créditos Fiscales Producto de la Aplicación del Porcentaje de la Prorrata",header_style)
        ws1.write_merge(row,row, 8, 8, "0,00",header_style_r)
        ws1.write_merge(row,row, 9, 9, "0,00",header_style_r)
        row=row+1
        ws1.write_merge(row,row, 4, 4, (row-6),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Total Créditos Fiscales Deducibles",header_style)
        ws1.write_merge(row,row, 8, 8, "0,00",header_style_r)
        ws1.write_merge(row,row, 9, 9, "0,00",header_style_r)
        row=row+1
        ws1.write_merge(row,row, 4, 4, (row-6),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Exedente Créditos Fiscales del Semana Anterior ",header_style)
        ws1.write_merge(row,row, 8, 8, "0,00",header_style_r)
        ws1.write_merge(row,row, 9, 9, "0,00",header_style_r)
        row=row+1
        ws1.write_merge(row,row, 4, 4, (row-6),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Reintegro Solicitado (sólo exportadores)",header_style)
        ws1.write_merge(row,row, 8, 8, "0,00",header_style_r)
        ws1.write_merge(row,row, 9, 9, "0,00",header_style_r)
        row=row+1
        ws1.write_merge(row,row, 4, 4, (row-6),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Reintegro (sólo quien suministre bienes o presten servicios a entes exonerados)",header_style)
        ws1.write_merge(row,row, 8, 8, "0,00",header_style_r)
        ws1.write_merge(row,row, 9, 9, "0,00",header_style_r)
        row=row+1
        ws1.write_merge(row,row, 4, 4, (row-6),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Ajustes a los Créditos Fiscales de Periodos Anteriores.",header_style)
        ws1.write_merge(row,row, 8, 8, "0,00",header_style_r)
        ws1.write_merge(row,row, 9, 9, "0,00",header_style_r)
        row=row+1
        ws1.write_merge(row,row, 4, 4, (row-6),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Certificados de Débitos Fiscales Exonerados (emitidos de entes exonerados) Registrados en el periodo",header_style)
        ws1.col(5).width = int(len('Certificados de Débitos Fiscales Exonerados (emitidos de entes exonerados) Registrados en el periodo')*128)
        ws1.write_merge(row,row, 8, 8, "0,00",header_style_r)
        ws1.write_merge(row,row, 9, 9, "0,00",header_style_r)
        row=row+1
        total22=sub_total22
        ws1.write_merge(row,row, 4, 4, (row-6),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Total Creditos Fiscales:",sub_header_style)
        ws1.write_merge(row,row, 8, 8, "0,00",sub_header_style_r)
        ws1.write_merge(row,row, 9, 9,total22,sub_header_style_r)
        
        row=row+1
        ws1.write_merge(row,row, 4, 9, "AUTOLIQUIDACIÓN",sub_header_style)
        #ws1.write_merge(row,row, 8, 8, "BASE IMPONIBLE",sub_header_style)
        #ws1.write_merge(row,row, 9, 9, "CRÉDITO FISCAL",sub_header_style)
        row=row+1
        resultado27=0
        resultado28=0
        if total11>total22:
            resultado27=total11-total22
        if total22>total11:
            resultado28=total22-total11
        ws1.write_merge(row,row, 4, 4, (row-7),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Total Cuota Tributaria del Período.",header_style)
        ws1.write_merge(row,row, 8, 8, "---",header_style_r)
        ws1.write_merge(row,row, 9, 9, resultado27,header_style_r)
        row=row+1
        ws1.write_merge(row,row, 4, 4, (row-7),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Exedente de Crédito Fiscal para el mes Siguiente.",header_style)
        ws1.write_merge(row,row, 8, 8, "---",header_style_r)
        ws1.write_merge(row,row, 9, 9,resultado28,header_style_r)
        row=row+1
        ws1.write_merge(row,row, 4, 4, (row-7),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Impuesto Pagado en Declaración(es) Sustituida(s)",header_style)
        ws1.write_merge(row,row, 8, 8, "0,00",header_style_r)
        ws1.write_merge(row,row, 9, 9, "0,00",header_style_r)
        row=row+1
        ws1.write_merge(row,row, 4, 4, (row-7),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Retenciones Descontadas en Declaración(es) Sustitutiva(s)",header_style)
        ws1.write_merge(row,row, 8, 8, "0,00",header_style_r)
        ws1.write_merge(row,row, 9, 9, "0,00",header_style_r)
        row=row+1
        ws1.write_merge(row,row, 4, 4, (row-7),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Percepciones Descontadas en Declaración(es) Sustitutiva(s)",header_style)
        ws1.write_merge(row,row, 8, 8, "0,00",header_style_r)
        ws1.write_merge(row,row, 9, 9, "0,00",header_style_r)
        row=row+1
        total32=resultado28+resultado27
        ws1.write_merge(row,row, 4, 4, (row-7),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Sub- Total Impuesto a Pagar:",sub_header_style)
        #ws1.write_merge(row,row, 8, 8, "0,00",sub_header_style_r)
        ws1.write_merge(row,row, 9, 9,total32,sub_header_style_r)
        
        row=row+1
        ws1.write_merge(row,row, 4, 9, "RETENCIONES IVA",sub_header_style)
        #ws1.write_merge(row,row, 8, 8, "BASE IMPONIBLE",sub_header_style)
        #ws1.write_merge(row,row, 9, 9, "CRÉDITO FISCAL",sub_header_style)
        row=row+1
        total_ret=self.ret_iva()
        total_ret_anterior=0
        ws1.write_merge(row,row, 4, 4, (row-8),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Retenciones IVA Acumuladas por Descontar",header_style)
        ws1.write_merge(row,row, 8, 8, total_ret_anterior,header_style_r)
        ws1.write_merge(row,row, 9, 9, "0,00",header_style_r)
        row=row+1
        ws1.write_merge(row,row, 4, 4, (row-8),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Retenciones del IVA del Periodo",header_style)
        ws1.write_merge(row,row, 8, 8,total_ret,header_style_r)
        ws1.write_merge(row,row, 9, 9, "0,00",header_style_r)
        row=row+1
        ws1.write_merge(row,row, 4, 4, (row-8),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Créditos del IVA Adquiridos por Cesiones de Retenciones",header_style)
        ws1.write_merge(row,row, 8, 8, "0,00",header_style_r)
        ws1.write_merge(row,row, 9, 9, "0,00",header_style_r)
        row=row+1
        ws1.write_merge(row,row, 4, 4, (row-8),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Recuperaciones del IVA Retenciones Solicitadas",header_style)
        ws1.write_merge(row,row, 8, 8, "0,00",header_style_r)
        ws1.write_merge(row,row, 9, 9, "0,00",header_style_r)
        row=row+1
        total_ret_iva2=total_ret+total_ret_anterior
        ws1.write_merge(row,row, 4, 4, (row-8),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Total Retenciones del IVA",header_style)
        ws1.write_merge(row,row, 8, 8, total_ret_iva2,header_style_r)
        ws1.write_merge(row,row, 9, 9, "0,00",header_style_r)
        row=row+1
        total_ret_desc=0
        if total32<total_ret_iva2:
            ret_iva_soportada=total32
        else:
            ret_iva_soportada=total_ret_iva2
        ws1.write_merge(row,row, 4, 4, (row-8),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Retenciones del IVA Soportadas y Descontadas",header_style)
        ws1.write_merge(row,row, 8, 8, total_ret_desc,header_style_r)
        ws1.write_merge(row,row, 9, 9,ret_iva_soportada,header_style_r)
        row=row+1
        solo_ret_iva=total_ret_iva2-total_ret_desc
        ws1.write_merge(row,row, 4, 4, (row-8),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Saldo Retenciones del IVA no Aplicado ",header_style)
        ws1.write_merge(row,row, 8, 8, solo_ret_iva,header_style_r)
        ws1.write_merge(row,row, 9, 9, "0,00",header_style_r)
        row=row+1
        ws1.write_merge(row,row, 4, 4, (row-8),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Sub- Total Impuesto a Pagar item 40:",sub_header_style)
        #ws1.write_merge(row,row, 8, 8, "0,00",sub_header_style_r)
        ws1.write_merge(row,row, 9, 9,total32-ret_iva_soportada,sub_header_style_r)

        row=row+1
        ws1.write_merge(row,row, 4, 9, "PERCEPCIÓN",sub_header_style)
        #ws1.write_merge(row,row, 8, 8, "BASE IMPONIBLE",sub_header_style)
        #ws1.write_merge(row,row, 9, 9, "CRÉDITO FISCAL",sub_header_style)
        row=row+1
        ws1.write_merge(row,row, 4, 4, (row-9),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Percepciones Acumuladas en Importaciones por Descontar",header_style)
        ws1.write_merge(row,row, 8, 8, "0,00",header_style_r)
        ws1.write_merge(row,row, 9, 9, "0,00",header_style_r)
        row=row+1
        ws1.write_merge(row,row, 4, 4, (row-9),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Percepciones del Periodo",header_style)
        ws1.write_merge(row,row, 8, 8, "0,00",header_style_r)
        ws1.write_merge(row,row, 9, 9, "0,00",header_style_r)
        row=row+1
        ws1.write_merge(row,row, 4, 4, (row-9),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Créditos Adquiridos por Cesiones de Percepciones",header_style)
        ws1.write_merge(row,row, 8, 8, "0,00",header_style_r)
        ws1.write_merge(row,row, 9, 9, "0,00",header_style_r)
        row=row+1
        ws1.write_merge(row,row, 4, 4, (row-9),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Recuperaciones Percepciones Solicitado",header_style)
        ws1.write_merge(row,row, 8, 8, "0,00",header_style_r)
        ws1.write_merge(row,row, 9, 9, "0,00",header_style_r)
        row=row+1
        ws1.write_merge(row,row, 4, 4, (row-9),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Total Percepciones",header_style)
        ws1.write_merge(row,row, 8, 8, "0,00",header_style_r)
        ws1.write_merge(row,row, 9, 9, "0,00",header_style_r)
        row=row+1
        ws1.write_merge(row,row, 4, 4, (row-9),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Percepciones en Aduanas Descontadas",header_style)
        ws1.write_merge(row,row, 8, 8, "0,00",header_style_r)
        ws1.write_merge(row,row, 9, 9, "0,00",header_style_r)
        row=row+1
        ws1.write_merge(row,row, 4, 4, (row-9),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Saldo de Percepciones en Aduanas no Aplicado",header_style)
        ws1.write_merge(row,row, 8, 8, "0,00",header_style_r)
        ws1.write_merge(row,row, 9, 9, "0,00",header_style_r)
        row=row+1
        ws1.write_merge(row,row, 4, 4, (row-9),header_style_c)
        ws1.write_merge(row,row, 5, 7,"Total a Pagar:",sub_header_style)
        #ws1.write_merge(row,row, 8, 8, "0,00",sub_header_style_r)
        ws1.write_merge(row,row, 9, 9, "0,00",sub_header_style_r)
        # ************ fin cuerpo excel
        wb1.save(fp)
        out = base64.b64encode(fp.getvalue())
        fecha  = datetime.now().strftime('%d/%m/%Y') 
        self.write({'state': 'get', 'report': out, 'name':'Resume_ventas_compras.xls'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.wizard.libro.resumen',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }