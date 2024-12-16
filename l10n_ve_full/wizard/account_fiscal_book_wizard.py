# coding: utf-8
##############################################################################

###############################################################################
import time
import base64
import xlsxwriter
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
from datetime import datetime, date, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from io import BytesIO


class FiscalBookWizard(models.TransientModel):
    """
    Sales book wizard implemented using the osv_memory wizard system
    """
    _name = "account.fiscal.book.wizard"

    TYPE = [("sale", _("Venta")),
            ("purchase", _("Compra")),
            ]

    @api.model
    def default_get(self, field_list):

        fiscal_book_obj = self.env['account.fiscal.book']
        fiscal_book = fiscal_book_obj.browse(self._context['active_id'])
        res = super(FiscalBookWizard, self).default_get(field_list)
        local_period = fiscal_book_obj.get_time_period(fiscal_book.time_period, fiscal_book)
        res.update({'type': fiscal_book.type})
        res.update({'date_start': local_period.get('dt_from', '')})
        res.update({'date_end': local_period.get('dt_to', '')})
        if fiscal_book.fortnight == 'first':
            date_obj = local_period.get('dt_to', '').split('-')
            res.update({'date_end': "%0004d-%02d-15" % (int(date_obj[0]), int(date_obj[1]))})
        elif fiscal_book.fortnight == 'second':
            date_obj = local_period.get('dt_to', '').split('-')
            res.update({'date_start': "%0004d-%02d-16" % (int(date_obj[0]), int(date_obj[1]))})
        return res

    def check_report_xlsx(self):
        if self.type == 'purchase':
            file_name = 'Libro_Compra.xlsx'
            output = BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True, 'strings_to_numbers': False})
            sheet = workbook.add_worksheet('Libro Compra')
            formats = self.set_formats(workbook)
            datos_compras, datos_compras_ajustes = self.get_datas_compras()
            if not datos_compras:
                raise UserError('No hay datos disponibles')
            sheet.merge_range('B3:G3', datos_compras[0]['company_name'], formats['string_titulo'])
            sheet.merge_range('M3:T3', 'Libro de Compras', formats['string_titulo'])
            sheet.merge_range('B4:G4', datos_compras[0]['company_rif'], formats['string'])
            format_new = "%d/%m/%Y"
            date_start = datetime.strptime(str(self.date_start), DATE_FORMAT).date()
            date_end = datetime.strptime(str(self.date_end), DATE_FORMAT).date()

            sheet.merge_range('M4:N4', 'Desde', formats['string'])
            sheet.merge_range('O4:P4', '%s' % date_start.strftime(format_new), formats['date'])
            sheet.merge_range('Q4:R4', 'Hasta', formats['string'])
            sheet.merge_range('S4:T4', '%s' % date_end.strftime(format_new), formats['date'])

            sheet.set_row(5, 30)
            sheet.merge_range('N6:W6', 'Compras Internas', formats['title'])
            sheet.merge_range('X6:AB6', 'Compras de Importaciones', formats['title'])
            sheet.merge_range('AC6:AD6', 'Retención IVA Proveedores', formats['title'])

            row = 6
            col = 1
            titles = [(1, 'Nro. Op'), (2, 'Fecha Emisión Doc.'), (3, 'Nro. de RIF'), (4, 'Nombre ó Razón Social'),
                      (5, 'Tipo Prov.'),
                      (6, 'Nro. de Factura'), (7, 'Nro. de Control'), (8, 'Nro. Nota de Crédito'),
                      (9, 'Nro. Nota de Débito'),
                      (10, 'Tipo de Trans'), (11, 'Nro. Factura Afectada'), (12, 'Total Compras con IVA'),
                      (13, 'Compras sin Derecho a Crédito'),
                      (14, 'Base Imponible Alicuota General'),
                      (15, '% Alicuota General'), (16, 'Impuesto (I.V.A) Alicuota General'),
                      (17, 'Base Imponible Alicuota Reducida'),
                      (18, '% Alicuota Reducida'), (19, 'Impuesto (I.V.A) Alicuota Reducida'),
                      (20, 'Base Imponible Alicuota Adicional'),
                      (21, '% Alicuota Adicional'), (22, 'Impuesto (I.V.A) Alicuota Adicional'),
                      (23, 'Base Imponible Alicuota General'),
                      (24, '% Alicuota General'), (25, 'Impuesto (I.V.A) Alicuota General'),
                      (26, 'Nro. Planilla Importación'),
                      (27, 'Nro. Expediente Importación'),
                      (28, 'Nro. de Comprobante'), (29, 'IVA Ret (Vend.)')]

            # sheet.set_row(6, cell_format=formats['title'])
            for title in titles:
                sheet.write(row, col, title[1], formats['title'])
                col += 1
            row += 1
            col = 1

            contador_datos_compras = 1
            row_suma_ini = row
            for d in datos_compras:
                col = 1
                sheet.write(row, col, contador_datos_compras)
                col += 1
                sheet.write(row, col, d['emission_date'])
                col += 1
                sheet.write(row, col, d['partner_vat'])
                col += 1
                sheet.write(row, col, d['partner_name'])
                col += 1
                sheet.write(row, col, d['people_type'])
                col += 1
                sheet.write(row, col, d['invoice_number'] if d['invoice_number'] else '', formats['string'])
                col += 1
                sheet.write(row, col, d['ctrl_number'], formats['string'])
                col += 1
                sheet.write(row, col, d['credit_affected'] if d['doc_type'] == 'N/CR' else '', formats['string'])
                col += 1
                sheet.write(row, col, d['debit_affected'] if d['debit_affected'] else '', formats['string'])
                col += 1
                sheet.write(row, col, d['type'])
                col += 1
                sheet.write(row, col, d['affected_invoice'] if d['affected_invoice'] else '', formats['string'])
                col += 1
                sheet.write(row, col, d['total_with_iva'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_exempt'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_general_base'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_general_rate'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_general_tax'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_reduced_base'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_reduced_rate'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_reduced_tax'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_additional_base'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_additional_rate'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_additional_tax'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_general_base_importaciones'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_general_rate_importaciones'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_general_tax_importaciones'], formats['number'])
                col += 1
                sheet.write(row, col, d['nro_planilla'], formats['string'])
                col += 1
                sheet.write(row, col, d['nro_expediente'], formats['string'])
                col += 1
                sheet.write(row, col, str(d['wh_number']), formats['number_sd'])
                col += 1
                sheet.write(row, col, d['get_wh_vat'], formats['number'])

                row += 1
                contador_datos_compras += 1
            row_suma_fin = row
            # imprimir totales y resumen
            row += 1
            col = 11
            row_totales = row + 1
            sheet.write(row, col, 'TOTALES', formats['title'])
            col = 12
            sheet.write(row, col, '=SUM(M%s:M%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])
            col = 13
            sheet.write(row, col, '=SUM(N%s:N%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])
            col = 14
            sheet.write(row, col, '=SUM(O%s:O%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])
            col = 15
            sheet.write(row, col, '', formats['title_number'])
            col = 16
            sheet.write(row, col, '=SUM(Q%s:Q%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])
            col = 17
            sheet.write(row, col, '=SUM(R%s:R%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])
            col = 18
            sheet.write(row, col, '', formats['title_number'])
            col = 19
            sheet.write(row, col, '=SUM(T%s:T%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])
            col = 20
            sheet.write(row, col, '=SUM(U%s:U%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])
            col = 21
            sheet.write(row, col, '', formats['title_number'])
            col = 22
            sheet.write(row, col, '=SUM(W%s:W%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])
            col = 23
            sheet.write(row, col, '=SUM(X%s:X%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])
            col = 24
            sheet.write(row, col, '', formats['title_number'])
            col = 25
            sheet.write(row, col, '=SUM(Z%s:Z%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])
            col = 26
            sheet.write(row, col, '', formats['title_number'])
            col = 27
            sheet.write(row, col, '', formats['title_number'])
            col = 28
            sheet.write(row, col, '', formats['title_number'])
            col = 29
            sheet.write(row, col, '=SUM(AD%s:AD%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])

            # resumen
            row += 4
            sheet.set_row(row - 1, 25)
            sheet.merge_range('L%s:T%s' % (row, row), 'Resumen de Libro de Compras', formats['title'])
            sheet.merge_range('U%s:Y%s' % (row, row), 'Base Imponible', formats['title'])
            sheet.merge_range('Z%s:AC%s' % (row, row), 'Crédito Fiscal', formats['title'])
            row += 1
            sheet.merge_range('L%s:T%s' % (row, row), 'Compras Internas no Gravadas y/o Sin Derecho a Crédito Fiscal')
            sheet.merge_range('U%s:Y%s' % (row, row), '0.0', formats['number'])
            sheet.merge_range('Z%s:AC%s' % (row, row), '0.0', formats['number'])
            row += 1
            sheet.merge_range('L%s:T%s' % (row, row), 'Compras Internas gravadas por Alicuota General ')
            sheet.merge_range('U%s:Y%s' % (row, row), '=O%s' % row_totales, formats['number'])
            sheet.merge_range('Z%s:AC%s' % (row, row), '=Q%s' % row_totales, formats['number'])
            row += 1
            sheet.merge_range('L%s:T%s' % (row, row),
                              'Compras Internas gravadas por Alicuota General mas Alicuota Adicional ')
            sheet.merge_range('U%s:Y%s' % (row, row), '=U%s' % row_totales, formats['number'])
            sheet.merge_range('Z%s:AC%s' % (row, row), '=W%s' % row_totales, formats['number'])
            row += 1
            sheet.merge_range('L%s:T%s' % (row, row),
                              'Compras Internas gravadas por Alicuota Reducida')
            sheet.merge_range('U%s:Y%s' % (row, row), '=R%s' % row_totales, formats['number'])
            sheet.merge_range('Z%s:AC%s' % (row, row), '=T%s' % row_totales, formats['number'])
            row += 1
            sheet.merge_range('L%s:T%s' % (row, row),
                              'Importaciones gravadas Alícuota General ')
            sheet.merge_range('U%s:Y%s' % (row, row), '=X%s' % row_totales, formats['number'])
            sheet.merge_range('Z%s:AC%s' % (row, row), '=Z%s' % row_totales, formats['number'])
            row += 1
            sheet.merge_range('L%s:T%s' % (row, row),
                              'Importaciones gravadas por Alícuota General mas Adicional ')
            sheet.merge_range('U%s:Y%s' % (row, row), '0.0', formats['number'])
            sheet.merge_range('Z%s:AC%s' % (row, row), '0.0', formats['number'])
            row += 1
            sheet.merge_range('L%s:T%s' % (row, row),
                              'Importaciones gravadas por Alicuota Reducida')
            sheet.merge_range('U%s:Y%s' % (row, row), '0.0', formats['number'])
            sheet.merge_range('Z%s:AC%s' % (row, row), '0.0', formats['number'])
            row += 1
            sheet.merge_range('L%s:T%s' % (row, row),
                              'Total Compras y Créditos Fiscales ',
                              formats['title'])
            sheet.merge_range('U%s:Y%s' % (row, row), '=O%s' % row_totales, formats['title_number'])
            sheet.merge_range('Z%s:AC%s' % (row, row), '=Q%s' % row_totales, formats['title_number'])
            row += 1
            sheet.merge_range('L%s:T%s' % (row, row),
                              'Total IVA Retenido',
                              formats['title'])
            sheet.merge_range('U%s:Y%s' % (row, row), '', formats['title_number'])
            sheet.merge_range('Z%s:AC%s' % (row, row), '=AD%s' % row_totales, formats['title_number'])

            row += 3
            col = 1
            sheet.merge_range('B%s:G%s' % (row, row), 'AJUSTE A CREDITOS FISCALES PERIODOS ANTERIORES')
            row += 1
            if datos_compras_ajustes:
                for title in titles:
                    sheet.write(row, col, title[1], formats['title'])
                    col += 1
                row += 1
                col = 1

                contador_datos_compras_ajustes = 1
                row_suma_ini_ajustes = row
                for d in datos_compras_ajustes:
                    col = 1
                    sheet.write(row, col, contador_datos_compras_ajustes)
                    col += 1
                    sheet.write(row, col, d['emission_date'])
                    col += 1
                    sheet.write(row, col, d['partner_vat'])
                    col += 1
                    sheet.write(row, col, d['partner_name'])
                    col += 1
                    sheet.write(row, col, d['people_type'])
                    col += 1
                    sheet.write(row, col, d['invoice_number'] if d['invoice_number'] else '', formats['string'])
                    col += 1
                    sheet.write(row, col, d['ctrl_number'], formats['string'])
                    col += 1
                    sheet.write(row, col, d['credit_affected'] if d['doc_type'] == 'N/CR' else '', formats['string'])
                    col += 1
                    sheet.write(row, col, d['debit_affected'] if d['debit_affected'] else '', formats['string'])
                    col += 1
                    sheet.write(row, col, d['type'])
                    col += 1
                    sheet.write(row, col, d['affected_invoice'] if d['affected_invoice'] else '', formats['string'])
                    col += 1
                    sheet.write(row, col, d['total_with_iva'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_exempt'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_general_base'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_general_rate'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_general_tax'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_reduced_base'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_reduced_rate'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_reduced_tax'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_additional_base'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_additional_rate'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_additional_tax'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_general_base_importaciones'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_general_rate_importaciones'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_general_tax_importaciones'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['nro_planilla'], formats['string'])
                    col += 1
                    sheet.write(row, col, d['nro_expediente'], formats['string'])
                    col += 1
                    sheet.write(row, col, str(d['wh_number']), formats['number_sd'])
                    col += 1
                    sheet.write(row, col, d['get_wh_vat'], formats['number'])

                    row += 1
                    contador_datos_compras_ajustes += 1
                row_suma_fin_ajustes = row
                # imprimir totales y resumen en ajustes
                row += 1
                col = 11
                sheet.write(row, col, 'TOTALES', formats['title'])
                col = 12
                sheet.write(row, col, '=SUM(M%s:M%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes),
                            formats['title_number'])
                col = 13
                sheet.write(row, col, '=SUM(N%s:N%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes),
                            formats['title_number'])
                col = 14
                sheet.write(row, col, '=SUM(O%s:O%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes),
                            formats['title_number'])
                col = 15
                sheet.write(row, col, '', formats['title_number'])
                col = 16
                sheet.write(row, col, '=SUM(Q%s:Q%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes),
                            formats['title_number'])
                col = 17
                sheet.write(row, col, '=SUM(R%s:R%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes),
                            formats['title_number'])
                col = 18
                sheet.write(row, col, '', formats['title_number'])
                col = 19
                sheet.write(row, col, '=SUM(T%s:T%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes),
                            formats['title_number'])
                col = 20
                sheet.write(row, col, '=SUM(U%s:U%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes),
                            formats['title_number'])
                col = 21
                sheet.write(row, col, '', formats['title_number'])
                col = 22
                sheet.write(row, col, '=SUM(W%s:W%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes),
                            formats['title_number'])
                col = 23
                sheet.write(row, col, '=SUM(X%s:X%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes),
                            formats['title_number'])
                col = 24
                sheet.write(row, col, '', formats['title_number'])
                col = 25
                sheet.write(row, col, '=SUM(Z%s:Z%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes),
                            formats['title_number'])
                col = 26
                sheet.write(row, col, '', formats['title_number'])
                col = 27
                sheet.write(row, col, '', formats['title_number'])
                col = 28
                sheet.write(row, col, '', formats['title_number'])
                col = 29
                sheet.write(row, col, '=SUM(AD%s:AD%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes),
                            formats['title_number'])

            sheet.set_column('AC:AC', 15)

            workbook.close()
            # with open(file_name, "rb") as file:
            #     file_base64 = base64.b64encode(file.read())
            file_base64 = base64.b64encode(output.getvalue())

            file_name = 'Libro de Compra'
            attachment_id = self.env['ir.attachment'].sudo().create({
                'name': file_name,
                'datas': file_base64
            })
            action = {
                'type': 'ir.actions.act_url',
                'url': '/web/content/{}?download=true'.format(attachment_id.id, ),
                'target': 'current',
            }
            return action
        else:
            ##excel de ventas
            file_name = 'Libro_Venta.xlsx'
            output = BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True, 'strings_to_numbers': True})
            sheet = workbook.add_worksheet('Libro de Venta')
            formats = self.set_formats(workbook)
            datos_ventas, datos_ventas_ajustes = self.get_datas_ventas()
            if not datos_ventas:
                raise UserError('No hay datos disponibles')
            sheet.merge_range('B3:G3', datos_ventas[0]['company_name'], formats['string_titulo'])
            sheet.merge_range('M3:T3', 'Libro de Venta', formats['string_titulo'])
            sheet.merge_range('B4:G4', datos_ventas[0]['company_rif'], formats['string'])
            format_new = "%d/%m/%Y"
            date_start = datetime.strptime(str(self.date_start), DATE_FORMAT).date()
            date_end = datetime.strptime(str(self.date_end), DATE_FORMAT).date()

            sheet.merge_range('M4:N4', 'Desde', formats['string'])
            sheet.merge_range('O4:P4', '%s' % date_start.strftime(format_new), formats['date'])
            sheet.merge_range('Q4:R4', 'Hasta', formats['string'])
            sheet.merge_range('S4:T4', '%s' % date_end.strftime(format_new), formats['date'])

            sheet.merge_range('Q6:Y6', 'Ventas Internas ó Exportación Gravadas', formats['title'])

            row = 6
            col = 1
            titles = [(1, 'Nro. Op'), (2, 'Nro. Reporte Z'), (3, 'Fecha Documento'), (4, 'RIF'),
                      (5, 'Nombre ó Razón Social'),
                      (6, 'Tipo Prov.'), (7, 'Nro. Planilla de Exportación'), (8, 'Nro. De Factura'),
                      (9, 'Nro. De Control'),
                      (10, 'Nro. Ultima Factura'), (11, 'Nro. Factura Afectada'), (12, 'Nro. Nota de Débito'),
                      (13, 'Nro. Nota de Crédito'),
                      (14, 'Tipo de Trans.'),
                      (15, 'Ventas Incluyendo IVA'), (16, 'Ventas Internas ó Exportaciones No Gravadas'),
                      (17, 'Ventas Internas ó Exportaciones Exoneradas'),
                      (18, 'Base Imponible Alicuota General'), (19, '% Alícuota General'),
                      (20, 'Impuesto IVA Alicuota General'),
                      (21, 'Base Imponible Alicuota Reducida'), (22, '% Alícuota Reducida'),
                      (23, 'Impuesto IVA Alicuota Reducida'),
                      (24, 'Base Imponible Alicuota Adicional'), (25, '% Alícuota Adicional'),
                      (26, 'Impuesto IVA Alicuota Adicional'),
                      (27, 'IVA Retenido (Comprador)'),
                      (28, 'Nro. De Comprobante'), (29, 'Fecha Comp.')]

            # sheet.set_row(6, cell_format=formats['title'])
            for title in titles:
                sheet.write(row, col, title[1], formats['title'])
                col += 1
            row += 1
            col = 1
            contador_datos_ventas = 1
            row_suma_ini = row
            for d in datos_ventas:
                col = 1
                sheet.write(row, col, contador_datos_ventas)
                col += 1
                sheet.write(row, col, d['report_z'] if d['report_z'] else '')
                col += 1
                sheet.write(row, col, d['emission_date'])
                col += 1
                sheet.write(row, col, d['partner_vat'])
                col += 1
                sheet.write(row, col, d['partner_name'])
                col += 1
                sheet.write(row, col, d['people_type'])
                col += 1
                sheet.write(row, col, d['export_form'])
                col += 1
                sheet.write(row, col, d['invoice_number'] if d['invoice_number'] else '')
                col += 1
                sheet.write(row, col, d['ctrl_number'] if d['ctrl_number'] else '')
                col += 1
                sheet.write(row, col, d['n_ultima_factZ'] if d['n_ultima_factZ'] else '')
                col += 1
                sheet.write(row, col, d['affected_invoice'] if d['affected_invoice'] else '')
                col += 1
                sheet.write(row, col, d['debit_note'] if d['debit_note'] else '')
                col += 1
                sheet.write(row, col, d['credit_note'] if d['credit_note'] else '')
                col += 1
                sheet.write(row, col, d['type'])
                col += 1
                sheet.write(row, col, d['total_w_iva'], formats['number'])
                col += 1
                sheet.write(row, col, d['no_taxe_sale'], formats['number'])
                col += 1
                sheet.write(row, col, d['export_sale'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_general_base'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_general_rate'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_general_tax'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_reduced_base'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_reduced_rate'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_reduced_tax'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_additional_base'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_additional_rate'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_additional_tax'], formats['number'])
                col += 1
                sheet.write(row, col, d['get_wh_vat'], formats['number'])
                col += 1
                sheet.write(row, col, d['wh_number'] if d['wh_number'] else '')
                col += 1
                sheet.write(row, col, d['date_wh_number'] if d['date_wh_number'] else '')

                row += 1
                contador_datos_ventas += 1

            row_suma_fin = row
            # imprimir totales y resumen
            row += 1
            col = 14
            row_totales = row + 1
            sheet.write(row, col, 'TOTALES', formats['title'])
            col = 15
            sheet.write(row, col, '=SUM(P%s:P%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])
            col = 16
            sheet.write(row, col, '=SUM(Q%s:Q%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])
            col = 17
            sheet.write(row, col, '=SUM(R%s:R%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])
            col = 18
            sheet.write(row, col, '=SUM(S%s:S%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])
            col = 19
            sheet.write(row, col, '', formats['title_number'])
            col = 20
            sheet.write(row, col, '=SUM(U%s:U%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])
            col = 21
            sheet.write(row, col, '=SUM(V%s:V%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])
            col = 22
            sheet.write(row, col, '', formats['title_number'])
            col = 23
            sheet.write(row, col, '=SUM(X%s:X%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])
            col = 24
            sheet.write(row, col, '=SUM(Y%s:Y%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])
            col = 25
            sheet.write(row, col, '', formats['title_number'])
            col = 26
            sheet.write(row, col, '=SUM(AA%s:AA%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])
            col = 27
            sheet.write(row, col, '=SUM(AB%s:AB%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])
            col = 28
            sheet.write(row, col, '', formats['title_number'])
            col = 29
            sheet.write(row, col, '', formats['title_number'])

            # resumen
            row += 4

            sheet.merge_range('L%s:R%s' % (row, row), 'Resumen de Libro de Ventas', formats['title'])
            sheet.merge_range('S%s:U%s' % (row, row), 'Base Imponible', formats['title'])
            sheet.merge_range('V%s:X%s' % (row, row), 'Débito Fiscal', formats['title'])
            sheet.merge_range('Y%s:AA%s' % (row, row), 'IVA Retenido por el Comprador', formats['title'])
            row += 1
            row_resumen = row
            sheet.merge_range('L%s:R%s' % (row, row), 'Ventas Internas Exoneradas')
            sheet.merge_range('S%s:U%s' % (row, row), '=Q%s' % row_totales, formats['number'])
            sheet.merge_range('V%s:X%s' % (row, row), '0.0', formats['number'])
            sheet.merge_range('Y%s:AA%s' % (row, row), '0.0', formats['number'])
            row += 1
            sheet.merge_range('L%s:R%s' % (row, row), 'Ventas de Exportación')
            sheet.merge_range('S%s:U%s' % (row, row), '0.0', formats['number'])
            sheet.merge_range('V%s:X%s' % (row, row), '0.0', formats['number'])
            sheet.merge_range('Y%s:AA%s' % (row, row), '0.0', formats['number'])
            row += 1
            sheet.merge_range('L%s:R%s' % (row, row), 'Ventas Internas gravadas por Alicuota General')
            sheet.merge_range('S%s:U%s' % (row, row), '=S%s' % row_totales, formats['number'])
            sheet.merge_range('V%s:X%s' % (row, row), '=U%s' % row_totales, formats['number'])
            sheet.merge_range('Y%s:AA%s' % (row, row), '=AB%s' % row_totales, formats['number'])
            row += 1
            sheet.merge_range('L%s:R%s' % (row, row),
                              'Ventas Internas gravadas por Alicuota General mas Alicuota Adicional ')
            sheet.merge_range('S%s:U%s' % (row, row), '=Y%s' % row_totales, formats['number'])
            sheet.merge_range('V%s:X%s' % (row, row), '=AA%s' % row_totales, formats['number'])
            sheet.merge_range('Y%s:AA%s' % (row, row), '0.0', formats['number'])
            row += 1
            sheet.merge_range('L%s:R%s' % (row, row), 'Ventas Internas gravadas por Alicuota Reducida')
            sheet.merge_range('S%s:U%s' % (row, row), '=V%s' % row_totales, formats['number'])
            sheet.merge_range('V%s:X%s' % (row, row), '=X%s' % row_totales, formats['number'])
            sheet.merge_range('Y%s:AA%s' % (row, row), '0.0', formats['number'])
            row += 1
            sheet.merge_range('L%s:R%s' % (row, row), 'Total Ventas y Debitos Fiscales', formats['title'])
            sheet.merge_range('S%s:U%s' % (row, row), '=SUMA(S%s:U%s)' % (row_resumen, row - 1),
                              formats['title_number'])
            sheet.merge_range('V%s:X%s' % (row, row), '=SUMA(V%s:X%s)' % (row_resumen, row - 1),
                              formats['title_number'])
            sheet.merge_range('Y%s:AA%s' % (row, row), '=SUMA(Y%s:AA%s)' % (row_resumen, row - 1),
                              formats['title_number'])
            row += 1
            if datos_ventas_ajustes:
                row += 3
                col = 1
                sheet.merge_range('B%s:G%s' % (row, row), 'RETENCIONES DE PERIODOS ANTERIORES')
                row += 1
                for title in titles:
                    sheet.write(row, col, title[1], formats['title'])
                    col += 1
                row += 1
                col = 1
                contador_datos_ventas_ajustes = 1
                row_suma_ini_ajustes = row
                for d in datos_ventas_ajustes:
                    col = 1
                    sheet.write(row, col, contador_datos_ventas_ajustes)
                    col += 1
                    sheet.write(row, col, d['report_z'] if d['report_z'] else '')
                    col += 1
                    sheet.write(row, col, d['emission_date'])
                    col += 1
                    sheet.write(row, col, d['partner_vat'])
                    col += 1
                    sheet.write(row, col, d['partner_name'])
                    col += 1
                    sheet.write(row, col, d['people_type'])
                    col += 1
                    sheet.write(row, col, d['export_form'])
                    col += 1
                    sheet.write(row, col, d['invoice_number'] if d['invoice_number'] else '')
                    col += 1
                    sheet.write(row, col, d['ctrl_number'] if d['ctrl_number'] else '')
                    col += 1
                    sheet.write(row, col, d['n_ultima_factZ'] if d['n_ultima_factZ'] else '')
                    col += 1
                    sheet.write(row, col, d['affected_invoice'] if d['affected_invoice'] else '')
                    col += 1
                    sheet.write(row, col, d['debit_note'] if d['debit_note'] else '')
                    col += 1
                    sheet.write(row, col, d['credit_note'] if d['credit_note'] else '')
                    col += 1
                    sheet.write(row, col, d['type'])
                    col += 1
                    sheet.write(row, col, d['total_w_iva'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['no_taxe_sale'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['export_sale'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_general_base'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_general_rate'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_general_tax'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_reduced_base'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_reduced_rate'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_reduced_tax'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_additional_base'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_additional_rate'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_additional_tax'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['get_wh_vat'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['wh_number'] if d['wh_number'] else '')
                    col += 1
                    sheet.write(row, col, d['date_wh_number'] if d['date_wh_number'] else '')

                    row += 1
                    contador_datos_ventas_ajustes += 1

                row_suma_fin_ajustes = row
                # imprimir totales y resumen
                row += 1
                col = 14
                row_totales = row + 1
                sheet.write(row, col, 'TOTALES', formats['title'])
                col = 15
                sheet.write(row, col, '=SUM(P%s:P%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes), formats['title_number'])
                col = 16
                sheet.write(row, col, '=SUM(Q%s:Q%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes), formats['title_number'])
                col = 17
                sheet.write(row, col, '=SUM(R%s:R%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes), formats['title_number'])
                col = 18
                sheet.write(row, col, '=SUM(S%s:S%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes), formats['title_number'])
                col = 19
                sheet.write(row, col, '', formats['title_number'])
                col = 20
                sheet.write(row, col, '=SUM(U%s:U%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes), formats['title_number'])
                col = 21
                sheet.write(row, col, '=SUM(V%s:V%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes), formats['title_number'])
                col = 22
                sheet.write(row, col, '', formats['title_number'])
                col = 23
                sheet.write(row, col, '=SUM(X%s:X%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes), formats['title_number'])
                col = 24
                sheet.write(row, col, '=SUM(Y%s:Y%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes), formats['title_number'])
                col = 25
                sheet.write(row, col, '', formats['title_number'])
                col = 26
                sheet.write(row, col, '=SUM(AA%s:AA%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes), formats['title_number'])
                col = 27
                sheet.write(row, col, '=SUM(AB%s:AB%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes), formats['title_number'])
                col = 28
                sheet.write(row, col, '', formats['title_number'])
                col = 29
                sheet.write(row, col, '', formats['title_number'])


            workbook.close()
            # with open(file_name, "rb") as file:
            #     file_base64 = base64.b64encode(file.read())
            file_base64 = base64.b64encode(output.getvalue())
            file_name = 'Libro de Venta'
            attachment_id = self.env['ir.attachment'].sudo().create({
                'name': file_name,
                'datas': file_base64
            })
            action = {
                'type': 'ir.actions.act_url',
                'url': '/web/content/{}?download=true'.format(attachment_id.id, ),
                'target': 'current',
            }
            return action

    def check_report(self):
        if self.type == 'purchase':
            if self.date_start and self.date_end:
                fecha_inicio = self.date_start
                fecha_fin = self.date_end
                book_id = self.env.context['active_id']
                purchase_book_obj = self.env['account.move']
                purchase_book_ids = purchase_book_obj.search(
                    [('invoice_date', '>=', fecha_inicio), ('invoice_date', '<=', fecha_fin),
                     ('state', 'in', ['posted'])])
                if purchase_book_ids:
                    ids = []
                    for id in purchase_book_ids:
                        ids.append(id.id)
                    data = {
                        'ids': ids,
                        'model': 'report.fiscal_book.report_fiscal_purchase_book',
                        'form': {
                            'date_from': self.date_start,
                            'date_to': self.date_end,
                            'book_id': book_id,
                        },
                    }
                    return self.env.ref('l10n_ve_full.report_purchase_book').report_action(self,
                                                                                           data=data)  # , config=False
                else:
                    raise ValidationError('Advertencia! No existen facturas entre las fechas seleccionadas')
        else:
            if self.date_start and self.date_end:
                fecha_inicio = self.date_start
                fecha_fin = self.date_end
                book_id = self.env.context['active_id']
                # tabla_report_z = self.env['datos.zeta.diario']
                # domain = ['|',
                #           ('fecha_ultimo_reporte_z', '>=', fecha_inicio),
                #           ('fecha_ultimo_reporte_z', '<=', fecha_fin),
                #           ('numero_ultimo_reporte_z', '>', '0')
                #           ]
                #
                # report_z_ids = tabla_report_z.search(domain, order='fecha_ultimo_reporte_z asc')
                #
                # if report_z_ids:
                #     ids = []
                #     for id in report_z_ids:
                #         ids.append(id.id)
                # purchase_book_obj = self.env['account.move']
                # purchase_book_ids = purchase_book_obj.search(
                #     [('invoice_date', '>=', fecha_inicio), ('invoice_date', '<=', fecha_fin),
                #      ('state', 'in', ['posted'])])
                #if purchase_book_ids:
                ids = [book_id]
                data = {
                        'ids': ids,
                        'model': 'report.fiscal_book.report_fiscal_sale_book',
                        'form': {
                            'date_from': self.date_start,
                            'date_to': self.date_end,
                            'book_id': book_id,
                        },
                }
                return self.env.ref('l10n_ve_full.report_sale_book').report_action(self, data=data, config=False)


    date_start = fields.Date("Fecha de Inicio", required=True, default=time.strftime('%Y-%m-%d'))
    date_end = fields.Date("Fecha Fin", required=True, default=time.strftime('%Y-%m-%d'))
    control_start = fields.Integer("Control Start")
    control_end = fields.Integer("Control End")
    type = fields.Selection(TYPE, "Tipo", required=True)

    def set_formats(self, workbook):
        merge_format_string = workbook.add_format({
            'border': 0,
            'align': 'center',
            'valign': 'vcenter',
        })
        merge_format_string_titulo = workbook.add_format({
            'border': 0,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 20,
        })
        merge_format_date = workbook.add_format({
            'border': 0,
            'align': 'center',
            'valign': 'vcenter',
            'num_format': 'dd-mm-yyyy'
        })
        merge_format_number = workbook.add_format({
            'bold': 0,
            'valign': 'vcenter',
            'num_format': '#,##0.00'
        })
        merge_format_number_sd = workbook.add_format({
            'bold': 0,
            'valign': 'vcenter',
            'num_format': '###0'
        })
        merge_format_number_peso = workbook.add_format({
            'bold': 0,
            'valign': 'vcenter',
            'num_format': '$ #,##0.00'
        })
        merge_format_number_usd = workbook.add_format({
            'bold': 0,
            'valign': 'vcenter',
            'num_format': '[$USD-409] #,##0.00'
        })
        merge_format_number_euro = workbook.add_format({
            'bold': 0,
            'valign': 'vcenter',
            'num_format': '€ #,##0.00'
        })
        merge_format_title = workbook.add_format({
            'bold': 1,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#fff5af',
            'text_wrap': True,
            'font_size': 10,
            'border': 1
        })
        merge_format_title_number = workbook.add_format({
            'bold': 1,
            'valign': 'vcenter',
            'bg_color': '#fff5af',
            'num_format': '#,##0.00',
            'text_wrap': True,
            'border': 1
        })
        merge_format_red_status = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#c30f0f',
            'font_color': 'white',
        })
        merge_format_yellow_status = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#ffeb9c',
            'font_color': 'black',
        })
        merge_format_light_green_status = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#c6efce',
            'font_color': '#50612e',
        })
        merge_format_green_status = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#87c842',
            'font_color': 'black',
        })
        merge_format_pink_status = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#ffc7ce',
            'font_color': '#9c0031',
        })
        return {
            'string': merge_format_string,
            'string_titulo': merge_format_string_titulo,
            'date': merge_format_date,
            'number': merge_format_number,
            'number_sd': merge_format_number_sd,
            'number_peso': merge_format_number_peso,
            'number_usd': merge_format_number_usd,
            'number_euro': merge_format_number_euro,
            'title': merge_format_title,
            'title_number': merge_format_title_number,
            'red_status': merge_format_red_status,
            'yellow_status': merge_format_yellow_status,
            'green_status': merge_format_green_status,
            'light_green_status': merge_format_light_green_status,
            'pink_status': merge_format_pink_status
        }

    def get_datas_compras(self):
        datos_compras = []
        datos_compras_ajustes = []
        for rec in self:
            format_new = "%d/%m/%Y"
            date_start = datetime.strptime(str(self.date_start), DATE_FORMAT)
            date_end = datetime.strptime(str(self.date_end), DATE_FORMAT)

            purchasebook_ids = self.env['account.fiscal.book.line'].search(
                [('fb_id', '=', self.env.context['active_id']),
                 ('accounting_date', '>=', date_start.strftime(DATETIME_FORMAT)),
                 ('accounting_date', '<=', date_end.strftime(DATETIME_FORMAT))], order='rank asc')

            emission_date = ' '
            sum_compras_credit = 0
            sum_total_with_iva = 0
            sum_vat_general_base = 0
            sum_vat_general_tax = 0
            sum_vat_reduced_base = 0
            sum_vat_reduced_tax = 0
            sum_vat_additional_base = 0
            sum_vat_additional_tax = 0
            sum_get_wh_vat = 0
            suma_vat_exempt = 0

            sum_compras_credit_ajustes = 0
            sum_total_with_iva_ajustes = 0
            sum_vat_general_base_ajustes = 0
            sum_vat_general_tax_ajustes = 0
            sum_vat_reduced_base_ajustes = 0
            sum_vat_reduced_tax_ajustes = 0
            sum_vat_additional_base_ajustes = 0
            sum_vat_additional_tax_ajustes = 0
            sum_get_wh_vat_ajustes = 0
            suma_vat_exempt_ajustes = 0

            vat_reduced_base = 0
            vat_reduced_rate = 0
            vat_reduced_tax = 0
            vat_additional_base = 0
            vat_additional_rate = 0
            vat_additional_tax = 0

            ''' COMPRAS DE IMPORTACIONES'''

            sum_total_with_iva_importaciones = 0
            sum_vat_general_base_importaciones = 0
            suma_base_general_importaciones = 0
            sum_base_general_tax_importaciones = 0
            sum_vat_general_tax_importaciones = 0
            sum_vat_reduced_base_importaciones = 0
            sum_vat_reduced_tax_importaciones = 0
            sum_vat_additional_base_importaciones = 0
            sum_vat_additional_tax_importaciones = 0

            hola = 0
            #######################################
            compras_credit = 0
            origin = 0
            number = 0

            for h in purchasebook_ids:
                h_vat_general_base = 0.0
                h_vat_general_rate = 0.0
                h_vat_general_tax = 0.0
                vat_general_base_importaciones = 0
                vat_general_rate_importaciones = 0
                vat_general_general_rate_importaciones = 0
                vat_general_tax_importaciones = 0
                vat_reduced_base_importaciones = 0
                vat_reduced_rate_importaciones = 0
                vat_reduced_tax_importaciones = 0
                vat_additional_tax_importaciones = 0
                vat_additional_rate_importaciones = 0
                vat_additional_base_importaciones = 0
                vat_reduced_base = 0
                vat_reduced_rate = 0
                vat_reduced_tax = 0
                vat_additional_base = 0
                vat_additional_rate = 0
                vat_additional_tax = 0
                get_wh_vat = 0

                if h.type == 'ntp':
                    compras_credit = h.invoice_id.amount_untaxed

                if h.doc_type == 'N/DB':
                    origin = h.affected_invoice
                    if h.invoice_id:
                        if h.invoice_id.nro_ctrl:
                            busq1 = self.env['account.move'].search([('nro_ctrl', '=', h.invoice_id.nro_ctrl)])
                            if busq1:
                                for busq2 in busq1:
                                    if busq2.type == 'in_invoice':
                                        number = busq2.name or ''

                sum_compras_credit += compras_credit
                suma_vat_exempt += h.vat_exempt
                planilla = ''
                expediente = ''
                total = 0
                partner = self.env['res.partner'].search([('rif', '=', h.partner_vat)])
                if partner and len(partner) == 1:
                    partner_1 = partner
                else:
                    partner = self.env['res.partner'].search([('name', '=', h.partner_vat)])
                    partner_1 = partner
                if h.invoice_id:
                    partner = h.invoice_id.partner_id
                    partner_1 = partner
                if (partner_1.company_type == 'company' or partner_1.company_type == 'person') and (
                        partner_1.people_type_company or partner_1.people_type_individual) and (
                        partner_1.people_type_company == 'pjdo' or partner_1.people_type_individual == 'pnre' or partner_1.people_type_individual == 'pnnr'):
                    '####################### NO ES PROVEDOR INTERNACIONAL########################################################3'

                    if h.invoice_id:
                        print('tiene factura')
                        tasa = 1
                        if h.invoice_id.currency_id.name == "USD":
                            tasa = self.obtener_tasa(h.invoice_id)
                        if h.doc_type == 'N/CR':
                            total = (h.invoice_id.amount_total) * -1 * tasa
                        else:
                            total = (h.invoice_id.amount_total) * tasa
                        sum_vat_reduced_base += h.vat_reduced_base  # Base Imponible de alicuota Reducida
                        sum_vat_reduced_tax += h.vat_reduced_tax  # Impuesto de IVA alicuota reducida
                        sum_vat_additional_base += h.vat_additional_base  # BASE IMPONIBLE ALICUOTA ADICIONAL

                        sum_vat_additional_tax += h.vat_additional_tax  # IMPUESTO DE IVA ALICUOTA ADICIONAL

                        sum_total_with_iva = (
                                h.fb_id.base_amount + h.fb_id.tax_amount) if h.emission_date >= date_start.date() else 0  # Total monto con IVA
                        sum_total_with_iva_ajustes = (
                                h.fb_id.base_amount + h.fb_id.tax_amount) if h.emission_date < date_start.date() else 0
                        # Total monto con IVA
                        sum_vat_general_base += h.vat_general_base  # Base Imponible Alicuota general
                        sum_vat_general_tax += h.vat_general_tax  # Impuesto de IVA
                        h_vat_general_base = h.vat_general_base
                        h_vat_general_rate = (
                                h.vat_general_base and h.vat_general_tax * 100 / h.vat_general_base) if h.vat_general_base else 0.0
                        h_vat_general_rate = round(h_vat_general_rate, 0)
                        h_vat_general_tax = h.vat_general_tax if h.vat_general_tax else 0.0
                        vat_reduced_base = h.vat_reduced_base
                        vat_reduced_rate = int(h.vat_reduced_base and h.vat_reduced_tax * 100 / h.vat_reduced_base)
                        vat_reduced_tax = h.vat_reduced_tax
                        vat_additional_base = h.vat_additional_base
                        vat_additional_rate = int(
                            h.vat_additional_base and h.vat_additional_tax * 100 / h.vat_additional_base)
                        vat_additional_tax = h.vat_additional_tax
                        get_wh_vat = h.get_wh_vat

                        emission_date = datetime.strftime(
                            datetime.strptime(str(h.emission_date), DEFAULT_SERVER_DATE_FORMAT),
                            format_new)
                    if h.iwdl_id.invoice_id:
                        print('tiene retencion y factura')
                        tasa = 1
                        if h.iwdl_id.invoice_id.currency_id.name == "USD":
                            tasa = self.obtener_tasa(h.iwdl_id.invoice_id)
                        if h.doc_type == 'N/CR':
                            total = (h.iwdl_id.invoice_id.amount_total) * -1 * tasa
                        else:
                            total = (h.iwdl_id.invoice_id.amount_total) * tasa
                        sum_vat_reduced_base += h.vat_reduced_base  # Base Imponible de alicuota Reducida
                        sum_vat_reduced_tax += h.vat_reduced_tax
                        # Impuesto de IVA alicuota reducida

                        sum_vat_additional_base += h.vat_additional_base  # BASE IMPONIBLE ALICUOTA ADICIONAL

                        sum_vat_additional_tax += h.vat_additional_tax  # IMPUESTO DE IVA ALICUOTA ADICIONAL

                        sum_total_with_iva = (
                                h.fb_id.base_amount + h.fb_id.tax_amount) if h.emission_date >= date_start.date() else 0  # Total monto con IVA
                        sum_total_with_iva_ajustes = (
                                h.fb_id.base_amount + h.fb_id.tax_amount) if h.emission_date < date_start.date() else 0
                        sum_vat_general_base += h.vat_general_base  # Base Imponible Alicuota general
                        sum_vat_general_tax += h.vat_general_tax  # Impuesto de IVA
                        h_vat_general_base = h.vat_general_base
                        h_vat_general_rate = (
                                h.vat_general_base and h.vat_general_tax * 100 / h.vat_general_base) if h.vat_general_base else 0.0
                        h_vat_general_rate = round(h_vat_general_rate, 0)
                        h_vat_general_tax = h.vat_general_tax if h.vat_general_tax else 0.0
                        vat_reduced_base = h.vat_reduced_base
                        vat_reduced_rate = int(h.vat_reduced_base and h.vat_reduced_tax * 100 / h.vat_reduced_base)
                        vat_reduced_tax = h.vat_reduced_tax
                        vat_additional_base = h.vat_additional_base
                        vat_additional_rate = int(
                            h.vat_additional_base and h.vat_additional_tax * 100 / h.vat_additional_base)
                        vat_additional_tax = h.vat_additional_tax
                        get_wh_vat = h.get_wh_vat

                        emission_date = datetime.strftime(
                            datetime.strptime(str(h.emission_date), DEFAULT_SERVER_DATE_FORMAT),
                            format_new)

                if (partner_1.company_type == 'company' or partner_1.company_type == 'person') and (
                        partner_1.people_type_company or partner_1.people_type_individual) and partner_1.people_type_company == 'pjnd':
                    '############## ES UN PROVEEDOR INTERNACIONAL ##############################################'

                    if h.invoice_id:
                        tasa = 1
                        if h.invoice_id.currency_id.name == "USD":
                            tasa = self.obtener_tasa(h.invoice_id)
                        if h.invoice_id.fecha_importacion:
                            date_impor = h.invoice_id.fecha_importacion
                            emission_date = datetime.strftime(
                                datetime.strptime(str(date_impor), DEFAULT_SERVER_DATE_FORMAT),
                                format_new)
                            total = h.invoice_id.amount_total * tasa
                        else:
                            date_impor = h.invoice_id.invoice_date
                            emission_date = datetime.strftime(
                                datetime.strptime(str(date_impor), DEFAULT_SERVER_DATE_FORMAT),
                                format_new)

                        planilla = h.invoice_id.nro_planilla_impor
                        expediente = h.invoice_id.nro_expediente_impor




                    else:
                        date_impor = h.iwdl_id.invoice_id.fecha_importacion
                        emission_date = datetime.strftime(
                            datetime.strptime(str(date_impor), DEFAULT_SERVER_DATE_FORMAT),
                            format_new)
                        planilla = h.iwdl_id.invoice_id.nro_planilla_impor
                        expediente = h.iwdl_id.invoice_id.nro_expediente_impor
                        tasa = 1
                        if h.iwdl_id.invoice_id.currency_id.name == "USD":
                            tasa = self.obtener_tasa(h.iwdl_id.invoice_id)
                        total = h.iwdl_id.invoice_id.amount_total * tasa
                    get_wh_vat = 0.0
                    vat_reduced_base = 0
                    vat_reduced_rate = 0
                    vat_reduced_tax = 0
                    vat_additional_base = 0
                    vat_additional_rate = 0
                    vat_additional_tax = 0
                    'ALICUOTA GENERAL IMPORTACIONES'
                    vat_general_base_importaciones = h.vat_general_base
                    vat_general_rate_importaciones = (
                            h.vat_general_base and h.vat_general_tax * 100 / h.vat_general_base)
                    vat_general_rate_importaciones = round(vat_general_rate_importaciones, 0)
                    vat_general_tax_importaciones = h.vat_general_tax
                    'ALICUOTA REDUCIDA IMPORTACIONES'
                    vat_reduced_base_importaciones = h.vat_reduced_base
                    vat_reduced_rate_importaciones = int(
                        h.vat_reduced_base and h.vat_reduced_tax * 100 / h.vat_reduced_base)
                    vat_reduced_tax_importaciones = h.vat_reduced_tax
                    'ALICUOTA ADICIONAL IMPORTACIONES'
                    vat_additional_base_importaciones = h.vat_additional_base
                    vat_additional_rate_importaciones = int(
                        h.vat_additional_base and h.vat_additional_tax * 100 / h.vat_additional_base)
                    vat_additional_tax_importaciones = h.vat_additional_tax
                    'Suma total compras con IVA'
                    sum_total_with_iva = (
                            h.fb_id.base_amount + h.fb_id.tax_amount) if h.emission_date >= date_start.date() else 0
                    sum_total_with_iva_ajustes = (
                            h.fb_id.base_amount + h.fb_id.tax_amount) if h.emission_date < date_start.date() else 0
                    # Total monto con IVA
                    'SUMA TOTAL DE TODAS LAS ALICUOTAS PARA LAS IMPORTACIONES'
                    sum_vat_general_base_importaciones += h.vat_general_base + h.vat_reduced_base + h.vat_additional_base  # Base Imponible Alicuota general
                    sum_vat_general_tax_importaciones += h.vat_general_tax + h.vat_additional_tax + h.vat_reduced_tax  # Impuesto de IVA

                    'Suma total de Alicuota General'
                    suma_base_general_importaciones += h.vat_general_base
                    sum_base_general_tax_importaciones += h.vat_general_tax

                    ' Suma total de Alicuota Reducida'
                    sum_vat_reduced_base_importaciones += h.vat_reduced_base  # Base Imponible de alicuota Reducida
                    sum_vat_reduced_tax_importaciones += h.vat_reduced_tax  # Impuesto de IVA alicuota reducida
                    'Suma total de Alicuota Adicional'
                    sum_vat_additional_base_importaciones += h.vat_additional_base  # BASE IMPONIBLE ALICUOTA ADICIONAL
                    sum_vat_additional_tax_importaciones += h.vat_additional_tax  # IMPUESTO DE IVA ALICUOTA ADICIONAL

                    get_wh_vat = h.get_wh_vat
                sum_get_wh_vat += h.get_wh_vat  # IVA RETENIDO

                if h_vat_general_base != 0:
                    valor_base_imponible = h.vat_general_base
                    valor_alic_general = h_vat_general_rate
                    valor_iva = h_vat_general_tax
                else:

                    valor_base_imponible = 0
                    valor_alic_general = 0
                    valor_iva = 0

                if get_wh_vat != 0:
                    hola = get_wh_vat
                else:
                    hola = 0

                if h.vat_exempt != 0:
                    vat_exempt = h.vat_exempt

                else:
                    vat_exempt = 0

                'Para las diferentes alicuotas que pueda tener el proveedor  internacional'
                'todas son mayor a 0'
                if vat_general_rate_importaciones > 0 and vat_reduced_rate_importaciones > 0 and vat_additional_rate_importaciones > 0:
                    vat_general_general_rate_importaciones = str(vat_general_rate_importaciones) + ',' + ' ' + str(
                        vat_reduced_rate_importaciones) + ',' + ' ' + str(vat_additional_rate_importaciones) + ' '
                'todas son cero'
                if vat_general_rate_importaciones == 0 and vat_reduced_rate_importaciones == 0 and vat_additional_rate_importaciones == 0:
                    vat_general_general_rate_importaciones = 0
                'Existe reducida y adicional'
                if vat_general_rate_importaciones == 0 and vat_reduced_rate_importaciones > 0 and vat_additional_rate_importaciones > 0:
                    vat_general_general_rate_importaciones = str(vat_reduced_rate_importaciones) + ',' + ' ' + str(
                        vat_additional_rate_importaciones) + ' '
                'Existe general y adicional'
                if vat_general_rate_importaciones > 0 and vat_reduced_rate_importaciones == 0 and vat_additional_rate_importaciones > 0:
                    vat_general_general_rate_importaciones = str(vat_general_rate_importaciones) + ',' + ' ' + str(
                        vat_additional_rate_importaciones) + ' '
                'Existe general y reducida'
                if vat_general_rate_importaciones > 0 and vat_reduced_rate_importaciones > 0 and vat_additional_rate_importaciones == 0:
                    vat_general_general_rate_importaciones = str(vat_general_rate_importaciones) + ',' + ' ' + str(
                        vat_reduced_rate_importaciones) + ' '
                'Existe solo la general'
                if vat_general_rate_importaciones > 0 and vat_reduced_rate_importaciones == 0 and vat_additional_rate_importaciones == 0:
                    vat_general_general_rate_importaciones = str(vat_general_rate_importaciones)
                'Existe solo la reducida'
                if vat_general_rate_importaciones == 0 and vat_reduced_rate_importaciones > 0 and vat_additional_rate_importaciones == 0:
                    vat_general_general_rate_importaciones = str(vat_reduced_rate_importaciones)
                'Existe solo la adicional'
                if vat_general_rate_importaciones == 0 and vat_reduced_rate_importaciones == 0 and vat_additional_rate_importaciones > 0:
                    vat_general_general_rate_importaciones = str(vat_additional_rate_importaciones)
                if h.emission_date >= date_start.date():
                    datos_compras.append({

                        'emission_date': datetime.strftime(
                            datetime.strptime(str(h.emission_date), DEFAULT_SERVER_DATE_FORMAT),
                            format_new) if h.emission_date else ' ',
                        'partner_vat': h.partner_vat if h.partner_vat else ' ',
                        'partner_name': h.partner_name,
                        'people_type': h.people_type,
                        'wh_number': h.wh_number if h.wh_number else ' ',
                        'invoice_number': h.invoice_number,
                        'affected_invoice': h.affected_invoice,
                        'ctrl_number': h.ctrl_number,
                        'debit_affected': h.numero_debit_credit if h.doc_type == 'N/DB' else False,
                        'credit_affected': h.numero_debit_credit if h.doc_type == 'N/CR' else False,
                        # h.credit_affected,
                        'type': h.void_form,
                        'doc_type': h.doc_type,
                        'origin': origin,
                        'number': number,
                        'total_with_iva': h.total_with_iva,
                        'vat_exempt': vat_exempt,
                        'compras_credit': compras_credit,
                        'vat_general_base': valor_base_imponible,
                        'vat_general_rate': valor_alic_general,
                        'vat_general_tax': valor_iva,
                        'vat_reduced_base': vat_reduced_base,
                        'vat_reduced_rate': vat_reduced_rate,
                        'vat_reduced_tax': vat_reduced_tax,
                        'vat_additional_base': vat_additional_base,
                        'vat_additional_rate': vat_additional_rate,
                        'vat_additional_tax': vat_additional_tax,
                        'get_wh_vat': hola,
                        'vat_general_base_importaciones': vat_general_base_importaciones + vat_additional_base_importaciones + vat_reduced_base_importaciones,
                        'vat_general_rate_importaciones': vat_general_general_rate_importaciones,
                        'vat_general_tax_importaciones': vat_general_tax_importaciones + vat_reduced_tax_importaciones + vat_additional_tax_importaciones,
                        'nro_planilla': planilla,
                        'nro_expediente': expediente,
                        'company_name': h.fb_id.company_id.name,
                        'company_rif': h.fb_id.company_id.rif
                    })
                else:
                    datos_compras_ajustes.append({

                        'emission_date': datetime.strftime(
                            datetime.strptime(str(h.emission_date), DEFAULT_SERVER_DATE_FORMAT),
                            format_new) if h.emission_date else ' ',
                        'partner_vat': h.partner_vat if h.partner_vat else ' ',
                        'partner_name': h.partner_name,
                        'people_type': h.people_type,
                        'wh_number': h.wh_number if h.wh_number else ' ',
                        'invoice_number': h.invoice_number,
                        'affected_invoice': h.affected_invoice,
                        'ctrl_number': h.ctrl_number,
                        'debit_affected': h.numero_debit_credit if h.doc_type == 'N/DB' else False,
                        'credit_affected': h.numero_debit_credit if h.doc_type == 'N/CR' else False,
                        # h.credit_affected,
                        'type': h.void_form,
                        'doc_type': h.doc_type,
                        'origin': origin,
                        'number': number,
                        'total_with_iva': h.total_with_iva,
                        'vat_exempt': vat_exempt,
                        'compras_credit': compras_credit,
                        'vat_general_base': valor_base_imponible,
                        'vat_general_rate': valor_alic_general,
                        'vat_general_tax': valor_iva,
                        'vat_reduced_base': vat_reduced_base,
                        'vat_reduced_rate': vat_reduced_rate,
                        'vat_reduced_tax': vat_reduced_tax,
                        'vat_additional_base': vat_additional_base,
                        'vat_additional_rate': vat_additional_rate,
                        'vat_additional_tax': vat_additional_tax,
                        'get_wh_vat': hola,
                        'vat_general_base_importaciones': vat_general_base_importaciones + vat_additional_base_importaciones + vat_reduced_base_importaciones,
                        'vat_general_rate_importaciones': vat_general_general_rate_importaciones,
                        'vat_general_tax_importaciones': vat_general_tax_importaciones + vat_reduced_tax_importaciones + vat_additional_tax_importaciones,
                        'nro_planilla': planilla,
                        'nro_expediente': expediente,
                        'company_name': h.fb_id.company_id.name,
                        'company_rif': h.fb_id.company_id.rif
                    })

        return datos_compras, datos_compras_ajustes

    def get_datas_ventas(self):
        datos_ventas = []
        datos_ventas_ajustes = []
        for rec in self:
            format_new = "%d/%m/%Y"

            # date_start =(data['form']['date_from'])
            # date_end =(data['form']['date_to'])

            fb_id = self.env.context['active_id']
            busq = self.env['account.fiscal.book'].search([('id', '=', fb_id)])
            date_start = datetime.strptime(str(self.date_start), DATE_FORMAT)
            date_end = datetime.strptime(str(self.date_end), DATE_FORMAT)
            # date_start = busq.period_start
            # date_end = busq.period_end
            fbl_obj = self.env['account.fiscal.book.line'].search(
                [('fb_id', '=', busq.id), ('accounting_date', '>=', date_start)
                 ], order='rank asc')

            suma_total_w_iva = 0
            suma_no_taxe_sale = 0
            suma_vat_general_base = 0
            suma_total_vat_general_base = 0
            suma_total_vat_general_tax = 0
            suma_total_vat_reduced_base = 0
            suma_total_vat_reduced_tax = 0
            suma_total_vat_additional_base = 0
            suma_total_vat_additional_tax = 0
            suma_vat_general_tax = 0
            suma_vat_reduced_base = 0
            suma_vat_reduced_tax = 0
            suma_vat_additional_base = 0
            suma_vat_additional_tax = 0
            suma_get_wh_vat = 0
            suma_ali_gene_addi = 0
            suma_ali_gene_addi_debit = 0
            total_ventas_base_imponible = 0
            total_ventas_debit_fiscal = 0

            suma_amount_tax = 0

            for line in fbl_obj:
                if line.vat_general_base != 0 or line.vat_reduced_base != 0 or line.vat_additional_base != 0 or line.vat_exempt != 0 or (
                        line.void_form == '03-ANU' and line.invoice_number):
                    vat_general_base = 0
                    vat_general_rate = 0
                    vat_general_tax = 0
                    vat_reduced_base = 0
                    vat_additional_base = 0
                    vat_additional_rate = 0
                    vat_additional_tax = 0
                    vat_reduced_rate = 0
                    vat_reduced_tax = 0

                    if line.type == 'ntp':
                        no_taxe_sale = line.vat_general_base
                    else:
                        no_taxe_sale = 0.0

                    if line.vat_reduced_base and line.vat_reduced_base != 0:
                        vat_reduced_base = line.vat_reduced_base
                        vat_reduced_rate = (
                                line.vat_reduced_base and line.vat_reduced_tax * 100 / line.vat_reduced_base)
                        vat_reduced_rate = int(round(vat_reduced_rate, 0))
                        vat_reduced_tax = line.vat_reduced_tax
                        suma_vat_reduced_base += line.vat_reduced_base
                        suma_vat_reduced_tax += line.vat_reduced_tax

                    if line.vat_additional_base and line.vat_additional_base != 0:
                        vat_additional_base = line.vat_additional_base
                        vat_additional_rate = (
                                line.vat_additional_base and line.vat_additional_tax * 100 / line.vat_additional_base)
                        vat_additional_rate = int(round(vat_additional_rate, 0))
                        vat_additional_tax = line.vat_additional_tax
                        suma_vat_additional_base += line.vat_additional_base
                        suma_vat_additional_tax += line.vat_additional_tax

                    if line.vat_general_base and line.vat_general_base != 0:
                        vat_general_base = line.vat_general_base
                        vat_general_rate = (line.vat_general_tax * 100 / line.vat_general_base)
                        vat_general_rate = int(round(vat_general_rate, 0))
                        vat_general_tax = line.vat_general_tax
                        suma_vat_general_base += line.vat_general_base
                        suma_vat_general_tax += line.vat_general_tax

                    if line.get_wh_vat:
                        suma_get_wh_vat += line.get_wh_vat
                    if vat_reduced_rate == 0:
                        vat_reduced_rate = ''
                    else:
                        vat_reduced_rate = str(vat_reduced_rate)
                    if vat_additional_rate == 0:
                        vat_additional_rate = ''
                    else:
                        vat_additional_rate = str(vat_additional_rate)
                    if vat_general_rate == 0:
                        vat_general_rate = ''

                    if vat_general_rate == '' and vat_reduced_rate == '' and vat_additional_rate == '':
                        vat_general_rate = 0

                    # if  line.void_form == '03-ANU' and line.invoice_number:
                    #     vat_general_base = 0
                    #     vat_general_rate = 0
                    #     vat_general_tax = 0
                    #     vat_reduced_base = 0
                    #     vat_additional_base = 0
                    #     vat_additional_rate = 0
                    #     vat_additional_tax = 0
                    #     vat_reduced_rate = 0
                    #     vat_reduced_tax = 0
                    if line.emission_date >= date_start.date():
                        datos_ventas.append({
                            'rannk': line.rank,
                            'emission_date': datetime.strftime(
                                datetime.strptime(str(line.emission_date), DEFAULT_SERVER_DATE_FORMAT), format_new),
                            'partner_vat': line.partner_vat if line.partner_vat else ' ',
                            'partner_name': line.partner_name,
                            'people_type': line.people_type if line.people_type else ' ',
                            'report_z': line.z_report,
                            'export_form': '',
                            'wh_number': line.wh_number,
                            'date_wh_number': line.iwdl_id.retention_id.date_ret if line.wh_number != '' else '',
                            'invoice_number': line.invoice_number,
                            'n_ultima_factZ': line.n_ultima_factZ,
                            'ctrl_number': line.ctrl_number,
                            'debit_note': line.numero_debit_credit if line.doc_type == 'N/DB' else False,
                            'credit_note': line.numero_debit_credit if line.doc_type == 'N/CR' else False,
                            'type': line.void_form,
                            'affected_invoice': line.affected_invoice if line.affected_invoice else ' ',
                            'total_w_iva': line.total_with_iva if line.total_with_iva else 0,
                            'no_taxe_sale': line.vat_exempt,
                            'export_sale': '',
                            'vat_general_base': vat_general_base,  # + vat_reduced_base + vat_additional_base,
                            'vat_general_rate': str(vat_general_rate),
                            # + '  ' + str(vat_reduced_rate) + ' ' + str(vat_additional_rate) + '  ',
                            'vat_general_tax': vat_general_tax,  # + vat_reduced_tax + vat_additional_tax,
                            'vat_reduced_base': line.vat_reduced_base,
                            'vat_reduced_rate': str(vat_reduced_rate),
                            'vat_reduced_tax': vat_reduced_tax,
                            'vat_additional_base': vat_additional_base,
                            'vat_additional_rate': str(vat_additional_rate),
                            'vat_additional_tax': vat_additional_tax,
                            'get_wh_vat': line.get_wh_vat,
                            'company_name': line.fb_id.company_id.name,
                            'company_rif': line.fb_id.company_id.rif
                        })
                    else:
                        datos_ventas_ajustes.append({
                            'rannk': line.rank,
                            'emission_date': datetime.strftime(
                                datetime.strptime(str(line.emission_date), DEFAULT_SERVER_DATE_FORMAT), format_new),
                            'partner_vat': line.partner_vat if line.partner_vat else ' ',
                            'partner_name': line.partner_name,
                            'people_type': line.people_type if line.people_type else ' ',
                            'report_z': line.z_report,
                            'export_form': '',
                            'wh_number': line.wh_number,
                            'date_wh_number': line.iwdl_id.retention_id.date_ret if line.wh_number != '' else '',
                            'invoice_number': line.invoice_number,
                            'n_ultima_factZ': line.n_ultima_factZ,
                            'ctrl_number': line.ctrl_number,
                            'debit_note': line.numero_debit_credit if line.doc_type == 'N/DB' else False,
                            'credit_note': line.numero_debit_credit if line.doc_type == 'N/CR' else False,
                            'type': line.void_form,
                            'affected_invoice': line.affected_invoice if line.affected_invoice else ' ',
                            'total_w_iva': line.total_with_iva if line.total_with_iva else 0,
                            'no_taxe_sale': line.vat_exempt,
                            'export_sale': '',
                            'vat_general_base': vat_general_base,  # + vat_reduced_base + vat_additional_base,
                            'vat_general_rate': str(vat_general_rate),
                            # + '  ' + str(vat_reduced_rate) + ' ' + str(vat_additional_rate) + '  ',
                            'vat_general_tax': vat_general_tax,  # + vat_reduced_tax + vat_additional_tax,
                            'vat_reduced_base': line.vat_reduced_base,
                            'vat_reduced_rate': str(vat_reduced_rate),
                            'vat_reduced_tax': vat_reduced_tax,
                            'vat_additional_base': vat_additional_base,
                            'vat_additional_rate': str(vat_additional_rate),
                            'vat_additional_tax': vat_additional_tax,
                            'get_wh_vat': line.get_wh_vat,
                            'company_name': line.fb_id.company_id.name,
                            'company_rif': line.fb_id.company_id.rif
                        })
                    suma_total_w_iva += line.total_with_iva
                    suma_no_taxe_sale += line.vat_exempt
                    suma_total_vat_general_base += line.vat_general_base
                    suma_total_vat_general_tax += line.vat_general_tax
                    suma_total_vat_reduced_base += line.vat_reduced_base
                    suma_total_vat_reduced_tax += line.vat_reduced_tax
                    suma_total_vat_additional_base += line.vat_additional_base
                    suma_total_vat_additional_tax += line.vat_additional_tax

                    # RESUMEN LIBRO DE VENTAS

                    # suma_ali_gene_addi =  suma_vat_additional_base if line.vat_additional_base else 0.0
                    # suma_ali_gene_addi_debit = suma_vat_additional_tax if line.vat_additional_tax else 0.0
                    total_ventas_base_imponible = suma_vat_general_base + suma_vat_additional_base + suma_vat_reduced_base + suma_no_taxe_sale
                    total_ventas_debit_fiscal = suma_vat_general_tax + suma_vat_additional_tax + suma_vat_reduced_tax

            if fbl_obj.env.company and fbl_obj.env.company.street:
                street = str(fbl_obj.env.company.street) + ','
            else:
                street = ' '

        return datos_ventas, datos_ventas_ajustes

    def obtener_tasa(self, invoice):
        fecha = invoice.date
        tasa_id = invoice.currency_id
        tasa = self.env['res.currency.rate'].search([('currency_id', '=', tasa_id.id), ('name', '<=', fecha)],
                                                    order='id desc', limit=1)
        if not tasa:
            raise UserError(
                "Advertencia! \n No hay referencia de tasas registradas para moneda USD en la fecha igual o inferior de la factura %s" % (
                    invoice.name))
        return tasa.rate


class PurchaseBook(models.AbstractModel):
    _name = 'report.l10n_ve_full.report_fiscal_purchase_book'

    @api.model
    def _get_report_values(self, docids, data=None):
        format_new = "%d/%m/%Y"
        date_start = datetime.strptime(data['form']['date_from'], DATE_FORMAT)
        date_end = datetime.strptime(data['form']['date_to'], DATE_FORMAT)
        datos_compras = []
        datos_compras_ajustes = []
        purchasebook_ids = self.env['account.fiscal.book.line'].search(
            [('fb_id', '=', data['form']['book_id']), ('accounting_date', '>=', date_start.strftime(DATETIME_FORMAT)),
             ('accounting_date', '<=', date_end.strftime(DATETIME_FORMAT))], order='rank asc')
        emission_date = ' '
        sum_compras_credit = 0
        sum_total_with_iva = 0
        sum_vat_general_base = 0
        sum_vat_general_tax = 0
        sum_vat_reduced_base = 0
        sum_vat_reduced_tax = 0
        sum_vat_additional_base = 0
        sum_vat_additional_tax = 0
        sum_get_wh_vat = 0
        suma_vat_exempt = 0

        sum_compras_credit_ajustes = 0
        sum_total_with_iva_ajustes = 0
        sum_vat_general_base_ajustes = 0
        sum_vat_general_tax_ajustes = 0
        sum_vat_reduced_base_ajustes = 0
        sum_vat_reduced_tax_ajustes = 0
        sum_vat_additional_base_ajustes = 0
        sum_vat_additional_tax_ajustes = 0
        sum_get_wh_vat_ajustes = 0
        suma_vat_exempt_ajustes = 0

        vat_reduced_base = 0
        vat_reduced_rate = 0
        vat_reduced_tax = 0
        vat_additional_base = 0
        vat_additional_rate = 0
        vat_additional_tax = 0

        ''' COMPRAS DE IMPORTACIONES'''

        sum_total_with_iva_importaciones = 0
        sum_vat_general_base_importaciones = 0
        suma_base_general_importaciones = 0
        sum_base_general_tax_importaciones = 0
        sum_vat_general_tax_importaciones = 0
        sum_vat_reduced_base_importaciones = 0
        sum_vat_reduced_tax_importaciones = 0
        sum_vat_additional_base_importaciones = 0
        sum_vat_additional_tax_importaciones = 0

        hola = 0
        #######################################
        compras_credit = 0
        origin = 0
        number = 0

        for h in purchasebook_ids:
            h_vat_general_base = 0.0
            h_vat_general_rate = 0.0
            h_vat_general_tax = 0.0
            vat_general_base_importaciones = 0
            vat_general_rate_importaciones = 0
            vat_general_general_rate_importaciones = 0
            vat_general_tax_importaciones = 0
            vat_reduced_base_importaciones = 0
            vat_reduced_rate_importaciones = 0
            vat_reduced_tax_importaciones = 0
            vat_additional_tax_importaciones = 0
            vat_additional_rate_importaciones = 0
            vat_additional_base_importaciones = 0
            vat_reduced_base = 0
            vat_reduced_rate = 0
            vat_reduced_tax = 0
            vat_additional_base = 0
            vat_additional_rate = 0
            vat_additional_tax = 0
            get_wh_vat = 0

            if h.type == 'ntp':
                compras_credit = h.invoice_id.amount_untaxed

            if h.doc_type == 'N/DB':
                origin = h.affected_invoice
                if h.invoice_id:
                    if h.invoice_id.nro_ctrl:
                        busq1 = self.env['account.move'].search([('nro_ctrl', '=', h.invoice_id.nro_ctrl)])
                        if busq1:
                            for busq2 in busq1:
                                if busq2.type == 'in_invoice':
                                    number = busq2.name or ''

            sum_compras_credit += compras_credit
            suma_vat_exempt += h.vat_exempt
            planilla = ''
            expediente = ''
            total = 0
            partner = self.env['res.partner'].search([('rif', '=', h.partner_vat)])
            if partner and len(partner) == 1:
                partner_1 = partner
            else:
                partner = self.env['res.partner'].search([('name', '=', h.partner_vat)])
                partner_1 = partner

            if h.invoice_id:
                partner = h.invoice_id.partner_id
                partner_1 = partner

            if (partner_1.company_type == 'company' or partner_1.company_type == 'person') and (
                    partner_1.people_type_company or partner_1.people_type_individual) and (
                    partner_1.people_type_company == 'pjdo' or partner_1.people_type_individual == 'pnre' or partner_1.people_type_individual == 'pnnr'):
                '####################### NO ES PROVEDOR INTERNACIONAL########################################################3'
                if h.invoice_id:
                    tasa = 1
                    if h.invoice_id.currency_id.name == "USD":
                        tasa = self.obtener_tasa(h.invoice_id)
                    if h.doc_type == 'N/CR':
                        total = (h.invoice_id.amount_total) * -1 * tasa
                    else:
                        total = (h.invoice_id.amount_total) * tasa
                    sum_vat_reduced_base += h.vat_reduced_base  # Base Imponible de alicuota Reducida
                    sum_vat_reduced_tax += h.vat_reduced_tax  # Impuesto de IVA alicuota reducida
                    sum_vat_additional_base += h.vat_additional_base  # BASE IMPONIBLE ALICUOTA ADICIONAL

                    sum_vat_additional_tax += h.vat_additional_tax  # IMPUESTO DE IVA ALICUOTA ADICIONAL

                    sum_total_with_iva = (
                                h.fb_id.base_amount + h.fb_id.tax_amount) if h.emission_date >= date_start.date() else 0  # Total monto con IVA
                    sum_total_with_iva_ajustes = (
                                h.fb_id.base_amount + h.fb_id.tax_amount) if h.emission_date < date_start.date() else 0
                    # Total monto con IVA
                    sum_vat_general_base += h.vat_general_base  # Base Imponible Alicuota general
                    sum_vat_general_tax += h.vat_general_tax  # Impuesto de IVA
                    h_vat_general_base = h.vat_general_base
                    h_vat_general_rate = (
                                h.vat_general_base and h.vat_general_tax * 100 / h.vat_general_base) if h.vat_general_base else 0.0
                    h_vat_general_rate = round(h_vat_general_rate, 0)
                    h_vat_general_tax = h.vat_general_tax if h.vat_general_tax else 0.0
                    vat_reduced_base = h.vat_reduced_base
                    vat_reduced_rate = int(h.vat_reduced_base and h.vat_reduced_tax * 100 / h.vat_reduced_base)
                    vat_reduced_tax = h.vat_reduced_tax
                    vat_additional_base = h.vat_additional_base
                    vat_additional_rate = int(
                        h.vat_additional_base and h.vat_additional_tax * 100 / h.vat_additional_base)
                    vat_additional_tax = h.vat_additional_tax
                    get_wh_vat = h.get_wh_vat

                    emission_date = datetime.strftime(
                        datetime.strptime(str(h.emission_date), DEFAULT_SERVER_DATE_FORMAT),
                        format_new)
                if h.iwdl_id.invoice_id:
                    tasa = 1
                    if h.iwdl_id.invoice_id.currency_id.name == "USD":
                        tasa = self.obtener_tasa(h.iwdl_id.invoice_id)
                    if h.doc_type == 'N/CR':
                        total = (h.iwdl_id.invoice_id.amount_total) * -1 * tasa
                    else:
                        total = (h.iwdl_id.invoice_id.amount_total) * tasa
                    sum_vat_reduced_base += h.vat_reduced_base  # Base Imponible de alicuota Reducida
                    sum_vat_reduced_tax += h.vat_reduced_tax
                    # Impuesto de IVA alicuota reducida

                    sum_vat_additional_base += h.vat_additional_base  # BASE IMPONIBLE ALICUOTA ADICIONAL

                    sum_vat_additional_tax += h.vat_additional_tax  # IMPUESTO DE IVA ALICUOTA ADICIONAL

                    sum_total_with_iva = (
                                h.fb_id.base_amount + h.fb_id.tax_amount) if h.emission_date >= date_start.date() else 0  # Total monto con IVA
                    sum_total_with_iva_ajustes = (
                                h.fb_id.base_amount + h.fb_id.tax_amount) if h.emission_date < date_start.date() else 0
                    sum_vat_general_base += h.vat_general_base  # Base Imponible Alicuota general
                    sum_vat_general_tax += h.vat_general_tax  # Impuesto de IVA
                    h_vat_general_base = h.vat_general_base
                    h_vat_general_rate = (
                                h.vat_general_base and h.vat_general_tax * 100 / h.vat_general_base) if h.vat_general_base else 0.0
                    h_vat_general_rate = round(h_vat_general_rate, 0)
                    h_vat_general_tax = h.vat_general_tax if h.vat_general_tax else 0.0
                    vat_reduced_base = h.vat_reduced_base
                    vat_reduced_rate = int(h.vat_reduced_base and h.vat_reduced_tax * 100 / h.vat_reduced_base)
                    vat_reduced_tax = h.vat_reduced_tax
                    vat_additional_base = h.vat_additional_base
                    vat_additional_rate = int(
                        h.vat_additional_base and h.vat_additional_tax * 100 / h.vat_additional_base)
                    vat_additional_tax = h.vat_additional_tax
                    get_wh_vat = h.get_wh_vat

                    emission_date = datetime.strftime(
                        datetime.strptime(str(h.emission_date), DEFAULT_SERVER_DATE_FORMAT),
                        format_new)

            if (partner_1.company_type == 'company' or partner_1.company_type == 'person') and (
                    partner_1.people_type_company or partner_1.people_type_individual) and partner_1.people_type_company == 'pjnd':
                '############## ES UN PROVEEDOR INTERNACIONAL ##############################################'

                if h.invoice_id:
                    tasa = 1
                    if h.invoice_id.currency_id.name == "USD":
                        tasa = self.obtener_tasa(h.invoice_id)
                    if h.invoice_id.fecha_importacion:
                        date_impor = h.invoice_id.fecha_importacion
                        emission_date = datetime.strftime(
                            datetime.strptime(str(date_impor), DEFAULT_SERVER_DATE_FORMAT),
                            format_new)
                        total = h.invoice_id.amount_total * tasa
                    else:
                        date_impor = h.invoice_id.invoice_date
                        emission_date = datetime.strftime(
                            datetime.strptime(str(date_impor), DEFAULT_SERVER_DATE_FORMAT),
                            format_new)

                    planilla = h.invoice_id.nro_planilla_impor
                    expediente = h.invoice_id.nro_expediente_impor




                else:
                    date_impor = h.iwdl_id.invoice_id.fecha_importacion
                    emission_date = datetime.strftime(datetime.strptime(str(date_impor), DEFAULT_SERVER_DATE_FORMAT),
                                                      format_new)
                    planilla = h.iwdl_id.invoice_id.nro_planilla_impor
                    expediente = h.iwdl_id.invoice_id.nro_expediente_impor
                    tasa = 1
                    if h.iwdl_id.invoice_id.currency_id.name == "USD":
                        tasa = self.obtener_tasa(h.iwdl_id.invoice_id)
                    total = h.iwdl_id.invoice_id.amount_total * tasa
                get_wh_vat = 0.0
                vat_reduced_base = 0
                vat_reduced_rate = 0
                vat_reduced_tax = 0
                vat_additional_base = 0
                vat_additional_rate = 0
                vat_additional_tax = 0
                'ALICUOTA GENERAL IMPORTACIONES'
                vat_general_base_importaciones = h.vat_general_base
                vat_general_rate_importaciones = (h.vat_general_base and h.vat_general_tax * 100 / h.vat_general_base)
                vat_general_rate_importaciones = round(vat_general_rate_importaciones, 0)
                vat_general_tax_importaciones = h.vat_general_tax
                'ALICUOTA REDUCIDA IMPORTACIONES'
                vat_reduced_base_importaciones = h.vat_reduced_base
                vat_reduced_rate_importaciones = int(
                    h.vat_reduced_base and h.vat_reduced_tax * 100 / h.vat_reduced_base)
                vat_reduced_tax_importaciones = h.vat_reduced_tax
                'ALICUOTA ADICIONAL IMPORTACIONES'
                vat_additional_base_importaciones = h.vat_additional_base
                vat_additional_rate_importaciones = int(
                    h.vat_additional_base and h.vat_additional_tax * 100 / h.vat_additional_base)
                vat_additional_tax_importaciones = h.vat_additional_tax
                'Suma total compras con IVA'
                sum_total_with_iva = (
                            h.fb_id.base_amount + h.fb_id.tax_amount) if h.emission_date >= date_start.date() else 0
                sum_total_with_iva_ajustes = (
                            h.fb_id.base_amount + h.fb_id.tax_amount) if h.emission_date < date_start.date() else 0
                # Total monto con IVA
                'SUMA TOTAL DE TODAS LAS ALICUOTAS PARA LAS IMPORTACIONES'
                sum_vat_general_base_importaciones += h.vat_general_base + h.vat_reduced_base + h.vat_additional_base  # Base Imponible Alicuota general
                sum_vat_general_tax_importaciones += h.vat_general_tax + h.vat_additional_tax + h.vat_reduced_tax  # Impuesto de IVA

                'Suma total de Alicuota General'
                suma_base_general_importaciones += h.vat_general_base
                sum_base_general_tax_importaciones += h.vat_general_tax

                ' Suma total de Alicuota Reducida'
                sum_vat_reduced_base_importaciones += h.vat_reduced_base  # Base Imponible de alicuota Reducida
                sum_vat_reduced_tax_importaciones += h.vat_reduced_tax  # Impuesto de IVA alicuota reducida
                'Suma total de Alicuota Adicional'
                sum_vat_additional_base_importaciones += h.vat_additional_base  # BASE IMPONIBLE ALICUOTA ADICIONAL
                sum_vat_additional_tax_importaciones += h.vat_additional_tax  # IMPUESTO DE IVA ALICUOTA ADICIONAL

                get_wh_vat = h.get_wh_vat
            sum_get_wh_vat += h.get_wh_vat  # IVA RETENIDO

            if h_vat_general_base != 0:
                valor_base_imponible = h.vat_general_base
                valor_alic_general = h_vat_general_rate
                valor_iva = h_vat_general_tax
            else:
                valor_base_imponible = 0
                valor_alic_general = 0
                valor_iva = 0

            if get_wh_vat != 0:
                hola = get_wh_vat
            else:
                hola = 0

            if h.vat_exempt != 0:
                vat_exempt = h.vat_exempt

            else:
                vat_exempt = 0

            'Para las diferentes alicuotas que pueda tener el proveedor  internacional'
            'todas son mayor a 0'
            if vat_general_rate_importaciones > 0 and vat_reduced_rate_importaciones > 0 and vat_additional_rate_importaciones > 0:
                vat_general_general_rate_importaciones = str(vat_general_rate_importaciones) + ',' + ' ' + str(
                    vat_reduced_rate_importaciones) + ',' + ' ' + str(vat_additional_rate_importaciones) + ' '
            'todas son cero'
            if vat_general_rate_importaciones == 0 and vat_reduced_rate_importaciones == 0 and vat_additional_rate_importaciones == 0:
                vat_general_general_rate_importaciones = 0
            'Existe reducida y adicional'
            if vat_general_rate_importaciones == 0 and vat_reduced_rate_importaciones > 0 and vat_additional_rate_importaciones > 0:
                vat_general_general_rate_importaciones = str(vat_reduced_rate_importaciones) + ',' + ' ' + str(
                    vat_additional_rate_importaciones) + ' '
            'Existe general y adicional'
            if vat_general_rate_importaciones > 0 and vat_reduced_rate_importaciones == 0 and vat_additional_rate_importaciones > 0:
                vat_general_general_rate_importaciones = str(vat_general_rate_importaciones) + ',' + ' ' + str(
                    vat_additional_rate_importaciones) + ' '
            'Existe general y reducida'
            if vat_general_rate_importaciones > 0 and vat_reduced_rate_importaciones > 0 and vat_additional_rate_importaciones == 0:
                vat_general_general_rate_importaciones = str(vat_general_rate_importaciones) + ',' + ' ' + str(
                    vat_reduced_rate_importaciones) + ' '
            'Existe solo la general'
            if vat_general_rate_importaciones > 0 and vat_reduced_rate_importaciones == 0 and vat_additional_rate_importaciones == 0:
                vat_general_general_rate_importaciones = str(vat_general_rate_importaciones)
            'Existe solo la reducida'
            if vat_general_rate_importaciones == 0 and vat_reduced_rate_importaciones > 0 and vat_additional_rate_importaciones == 0:
                vat_general_general_rate_importaciones = str(vat_reduced_rate_importaciones)
            'Existe solo la adicional'
            if vat_general_rate_importaciones == 0 and vat_reduced_rate_importaciones == 0 and vat_additional_rate_importaciones > 0:
                vat_general_general_rate_importaciones = str(vat_additional_rate_importaciones)
            if h.emission_date >= date_start.date():
                datos_compras.append({

                    'emission_date': datetime.strftime(
                        datetime.strptime(str(h.emission_date), DEFAULT_SERVER_DATE_FORMAT),
                        format_new) if h.emission_date else ' ',
                    'partner_vat': h.partner_vat if h.partner_vat else ' ',
                    'partner_name': h.partner_name,
                    'people_type': h.people_type,
                    'wh_number': h.wh_number if h.wh_number else ' ',
                    'invoice_number': h.invoice_number,
                    'affected_invoice': h.affected_invoice,
                    'ctrl_number': h.ctrl_number,
                    'debit_affected': h.numero_debit_credit if h.doc_type == 'N/DB' else False,
                    'credit_affected': h.numero_debit_credit if h.doc_type == 'N/CR' else False,  # h.credit_affected,
                    'type': h.void_form,
                    'doc_type': h.doc_type,
                    'origin': origin,
                    'number': number,
                    'total_with_iva': h.total_with_iva,
                    'vat_exempt': vat_exempt,
                    'compras_credit': compras_credit,
                    'vat_general_base': valor_base_imponible,
                    'vat_general_rate': valor_alic_general,
                    'vat_general_tax': valor_iva,
                    'vat_reduced_base': vat_reduced_base,
                    'vat_reduced_rate': vat_reduced_rate,
                    'vat_reduced_tax': vat_reduced_tax,
                    'vat_additional_base': vat_additional_base,
                    'vat_additional_rate': vat_additional_rate,
                    'vat_additional_tax': vat_additional_tax,
                    'get_wh_vat': hola,
                    'vat_general_base_importaciones': vat_general_base_importaciones + vat_additional_base_importaciones + vat_reduced_base_importaciones,
                    'vat_general_rate_importaciones': vat_general_general_rate_importaciones,
                    'vat_general_tax_importaciones': vat_general_tax_importaciones + vat_reduced_tax_importaciones + vat_additional_tax_importaciones,
                    'nro_planilla': planilla,
                    'nro_expediente': expediente,
                })
            else:
                datos_compras_ajustes.append({

                    'emission_date': datetime.strftime(
                        datetime.strptime(str(h.emission_date), DEFAULT_SERVER_DATE_FORMAT),
                        format_new) if h.emission_date else ' ',
                    'partner_vat': h.partner_vat if h.partner_vat else ' ',
                    'partner_name': h.partner_name,
                    'people_type': h.people_type,
                    'wh_number': h.wh_number if h.wh_number else ' ',
                    'invoice_number': h.invoice_number,
                    'affected_invoice': h.affected_invoice,
                    'ctrl_number': h.ctrl_number,
                    'debit_affected': h.numero_debit_credit if h.doc_type == 'N/DB' else False,
                    'credit_affected': h.numero_debit_credit if h.doc_type == 'N/CR' else False,  # h.credit_affected,
                    'type': h.void_form,
                    'doc_type': h.doc_type,
                    'origin': origin,
                    'number': number,
                    'total_with_iva': h.total_with_iva,
                    'vat_exempt': vat_exempt,
                    'compras_credit': compras_credit,
                    'vat_general_base': valor_base_imponible,
                    'vat_general_rate': valor_alic_general,
                    'vat_general_tax': valor_iva,
                    'vat_reduced_base': vat_reduced_base,
                    'vat_reduced_rate': vat_reduced_rate,
                    'vat_reduced_tax': vat_reduced_tax,
                    'vat_additional_base': vat_additional_base,
                    'vat_additional_rate': vat_additional_rate,
                    'vat_additional_tax': vat_additional_tax,
                    'get_wh_vat': hola,
                    'vat_general_base_importaciones': vat_general_base_importaciones + vat_additional_base_importaciones + vat_reduced_base_importaciones,
                    'vat_general_rate_importaciones': vat_general_general_rate_importaciones,
                    'vat_general_tax_importaciones': vat_general_tax_importaciones + vat_reduced_tax_importaciones + vat_additional_tax_importaciones,
                    'nro_planilla': planilla,
                    'nro_expediente': expediente,
                })
        'SUMA TOTAL DE ALICUOTA ADICIONAL BASE'
        if sum_vat_additional_base != 0 and sum_vat_additional_base_importaciones > 0:
            sum_ali_gene_addi = sum_vat_additional_base
            sum_vat_additional_base = sum_vat_additional_base
        else:
            sum_ali_gene_addi = sum_vat_additional_base
        'SUMA TOTAL DE ALICUOTA ADICIONAL TAX'
        if sum_vat_additional_tax != 0 and sum_vat_additional_tax_importaciones > 0:
            sum_ali_gene_addi_credit = sum_vat_additional_tax
            sum_vat_additional_tax = sum_vat_additional_tax
        else:
            sum_ali_gene_addi_credit = sum_vat_additional_tax
        'SUMA TOTAL DE ALICUOTA GENERAL BASE'
        if sum_vat_general_base != 0 and suma_base_general_importaciones > 0:
            sum_vat_general_base = sum_vat_general_base
            sum_vat_general_tax = sum_vat_general_tax
        'SUMA TOTAL DE ALICUOTA REDUCIDA BASE'
        if sum_vat_reduced_base != 0 and sum_vat_reduced_base_importaciones > 0:
            sum_vat_reduced_base = sum_vat_reduced_base
            sum_vat_reduced_tax = sum_vat_reduced_tax

        ' IMPORTACIONES ALICUOTA GENERAL + ALICUOTA ADICIONAL'
        if sum_vat_additional_base_importaciones != 0:
            sum_ali_gene_addi_importaciones = sum_vat_additional_base_importaciones
        else:
            sum_ali_gene_addi_importaciones = sum_vat_additional_base_importaciones

        if sum_vat_additional_tax_importaciones != 0:
            sum_ali_gene_addi_credit_importaciones = sum_vat_additional_tax_importaciones
        else:
            sum_ali_gene_addi_credit_importaciones = sum_vat_additional_tax_importaciones

        total_compras_base_imponible = sum_vat_general_base + sum_ali_gene_addi + sum_vat_reduced_base + suma_base_general_importaciones + sum_ali_gene_addi_importaciones + sum_vat_reduced_base_importaciones + suma_vat_exempt
        total_compras_credit_fiscal = sum_vat_general_tax + sum_ali_gene_addi_credit + sum_vat_reduced_tax + sum_base_general_tax_importaciones + sum_ali_gene_addi_credit_importaciones + sum_vat_reduced_tax_importaciones

        date_start = datetime.strftime(datetime.strptime(data['form']['date_from'], DEFAULT_SERVER_DATE_FORMAT),
                                       format_new)
        date_end = datetime.strftime(datetime.strptime(data['form']['date_to'], DEFAULT_SERVER_DATE_FORMAT), format_new)

        if purchasebook_ids.env.company and purchasebook_ids.env.company.street:
            street = str(purchasebook_ids.env.company.street) + ','
        else:
            street = ' '
        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'date_start': date_start,
            'date_end': date_end,
            'a': 0.00,
            'street': street,
            'company': purchasebook_ids.env.company,
            'datos_compras': datos_compras,
            'datos_compras_ajustes': datos_compras_ajustes,
            'sum_compras_credit': sum_compras_credit,
            'sum_total_with_iva': sum_total_with_iva,
            'suma_vat_exempt': suma_vat_exempt,
            'sum_vat_general_base': sum_vat_general_base,
            'sum_vat_general_tax': sum_vat_general_tax,
            'sum_vat_reduced_base': sum_vat_reduced_base,
            'sum_vat_reduced_tax': sum_vat_reduced_tax,
            'sum_vat_additional_base': sum_vat_additional_base,
            'sum_vat_additional_tax': sum_vat_additional_tax,
            'sum_get_wh_vat': sum_get_wh_vat,
            'sum_ali_gene_addi': sum_ali_gene_addi,
            'sum_ali_gene_addi_credit': sum_ali_gene_addi_credit,
            'suma_base_general_importaciones': suma_base_general_importaciones,
            'sum_base_general_tax_importaciones': sum_base_general_tax_importaciones,
            'sum_vat_general_base_importaciones': sum_vat_general_base_importaciones,
            'sum_vat_general_tax_importaciones': sum_vat_general_tax_importaciones,
            'sum_ali_gene_addi_importaciones': sum_ali_gene_addi_importaciones,
            'sum_ali_gene_addi_credit_importaciones': sum_ali_gene_addi_credit_importaciones,
            'sum_vat_reduced_base_importaciones': sum_vat_reduced_base_importaciones,
            'sum_vat_reduced_tax_importaciones': sum_vat_reduced_tax_importaciones,
            'total_compras_base_imponible': total_compras_base_imponible,
            'total_compras_credit_fiscal': total_compras_credit_fiscal,

        }

    def obtener_tasa(self, invoice):
        fecha = invoice.date
        tasa_id = invoice.currency_id
        tasa = self.env['res.currency.rate'].search([('currency_id', '=', tasa_id.id), ('name', '<=', fecha)],
                                                    order='id desc', limit=1)
        if not tasa:
            raise UserError(
                "Advertencia! \n No hay referencia de tasas registradas para moneda USD en la fecha igual o inferior de la factura %s" % (
                    invoice.name))
        return tasa.rate


#
class FiscalBookSaleReport(models.AbstractModel):
    _name = 'report.l10n_ve_full.report_fiscal_sale_book'

    @api.model
    def _get_report_values(self, docids, data=None):
        format_new = "%d/%m/%Y"

        # date_start =(data['form']['date_from'])
        # date_end =(data['form']['date_to'])

        fb_id = data['form']['book_id']
        busq = self.env['account.fiscal.book'].search([('id', '=', fb_id)])
        date_start = datetime.strptime(data['form']['date_from'], DATE_FORMAT).date()
        date_end = datetime.strptime(data['form']['date_to'], DATE_FORMAT).date()
        # date_start = busq.period_start
        # date_end = busq.period_end
        fbl_obj = self.env['account.fiscal.book.line'].search(
            [('fb_id', '=', busq.id), ('accounting_date', '>=', date_start)
             ], order='rank asc')

        docs = []
        docs_ajustes = []
        suma_total_w_iva = 0
        suma_no_taxe_sale = 0
        suma_vat_general_base = 0
        suma_total_vat_general_base = 0
        suma_total_vat_general_tax = 0
        suma_total_vat_reduced_base = 0
        suma_total_vat_reduced_tax = 0
        suma_total_vat_additional_base = 0
        suma_total_vat_additional_tax = 0
        suma_vat_general_tax = 0
        suma_vat_reduced_base = 0
        suma_vat_reduced_tax = 0
        suma_vat_additional_base = 0
        suma_vat_additional_tax = 0
        suma_get_wh_vat = 0
        suma_ali_gene_addi = 0
        suma_ali_gene_addi_debit = 0
        total_ventas_base_imponible = 0
        total_ventas_debit_fiscal = 0

        suma_amount_tax = 0

        for line in fbl_obj:
            if line.vat_general_base != 0 or line.vat_reduced_base != 0 or line.vat_additional_base != 0 or line.vat_exempt != 0 or (
                    line.void_form == '03-ANU' and line.invoice_number):
                vat_general_base = 0
                vat_general_rate = 0
                vat_general_tax = 0
                vat_reduced_base = 0
                vat_additional_base = 0
                vat_additional_rate = 0
                vat_additional_tax = 0
                vat_reduced_rate = 0
                vat_reduced_tax = 0

                if line.type == 'ntp':
                    no_taxe_sale = line.vat_general_base
                else:
                    no_taxe_sale = 0.0

                if line.vat_reduced_base and line.vat_reduced_base != 0:
                    vat_reduced_base = line.vat_reduced_base
                    vat_reduced_rate = (line.vat_reduced_base and line.vat_reduced_tax * 100 / line.vat_reduced_base)
                    vat_reduced_rate = int(round(vat_reduced_rate, 0))
                    vat_reduced_tax = line.vat_reduced_tax
                    if line.emission_date >= date_start:
                        suma_vat_reduced_base += line.vat_reduced_base
                        suma_vat_reduced_tax += line.vat_reduced_tax

                if line.vat_additional_base and line.vat_additional_base != 0:
                    vat_additional_base = line.vat_additional_base
                    vat_additional_rate = (
                                line.vat_additional_base and line.vat_additional_tax * 100 / line.vat_additional_base)
                    vat_additional_rate = int(round(vat_additional_rate, 0))
                    vat_additional_tax = line.vat_additional_tax
                    if line.emission_date >= date_start:
                        suma_vat_additional_base += line.vat_additional_base
                        suma_vat_additional_tax += line.vat_additional_tax

                if line.vat_general_base and line.vat_general_base != 0:
                    vat_general_base = line.vat_general_base
                    vat_general_rate = (line.vat_general_tax * 100 / line.vat_general_base)
                    vat_general_rate = int(round(vat_general_rate, 0))
                    vat_general_tax = line.vat_general_tax
                    if line.emission_date >= date_start:
                        suma_vat_general_base += line.vat_general_base
                        suma_vat_general_tax += line.vat_general_tax

                if line.get_wh_vat and line.emission_date >= date_start:
                    suma_get_wh_vat += line.get_wh_vat
                if vat_reduced_rate == 0:
                    vat_reduced_rate = ''
                else:
                    vat_reduced_rate = str(vat_reduced_rate)
                if vat_additional_rate == 0:
                    vat_additional_rate = ''
                else:
                    vat_additional_rate = str(vat_additional_rate)
                if vat_general_rate == 0:
                    vat_general_rate = ''

                if vat_general_rate == '' and vat_reduced_rate == '' and vat_additional_rate == '':
                    vat_general_rate = 0

                # if  line.void_form == '03-ANU' and line.invoice_number:
                #     vat_general_base = 0
                #     vat_general_rate = 0
                #     vat_general_tax = 0
                #     vat_reduced_base = 0
                #     vat_additional_base = 0
                #     vat_additional_rate = 0
                #     vat_additional_tax = 0
                #     vat_reduced_rate = 0
                #     vat_reduced_tax = 0
                if line.emission_date >= date_start:
                    docs.append({
                        'rannk': line.rank,
                        'emission_date': datetime.strftime(
                            datetime.strptime(str(line.emission_date), DEFAULT_SERVER_DATE_FORMAT), format_new),
                        'partner_vat': line.partner_vat if line.partner_vat else ' ',
                        'partner_name': line.partner_name,
                        'people_type': line.people_type if line.people_type else ' ',
                        'report_z': line.z_report if line.z_report else '',
                        'export_form': '',
                        'wh_number': line.wh_number,
                        'date_wh_number': line.iwdl_id.retention_id.date_ret if line.wh_number != '' else '',
                        'invoice_number': line.invoice_number,
                        'n_ultima_factZ': line.n_ultima_factZ,
                        'ctrl_number': line.ctrl_number,
                        'debit_note': line.numero_debit_credit if line.doc_type == 'N/DB' else False,
                        'credit_note': line.numero_debit_credit if line.doc_type == 'N/CR' else False,
                        'type': line.void_form,
                        'affected_invoice': line.affected_invoice if line.affected_invoice else ' ',
                        'total_w_iva': line.total_with_iva if line.total_with_iva else 0,
                        'no_taxe_sale': line.vat_exempt,
                        'export_sale': '',
                        'vat_general_base': vat_general_base,  # + vat_reduced_base + vat_additional_base,
                        'vat_general_rate': str(vat_general_rate),
                        # + '  ' + str(vat_reduced_rate) + ' ' + str(vat_additional_rate) + '  ',
                        'vat_general_tax': vat_general_tax,  # + vat_reduced_tax + vat_additional_tax,
                        'vat_reduced_base': line.vat_reduced_base,
                        'vat_reduced_rate': str(vat_reduced_rate),
                        'vat_reduced_tax': vat_reduced_tax,
                        'vat_additional_base': vat_additional_base,
                        'vat_additional_rate': str(vat_additional_rate),
                        'vat_additional_tax': vat_additional_tax,
                        'get_wh_vat': line.get_wh_vat,
                    })

                    suma_total_w_iva += line.total_with_iva
                    suma_no_taxe_sale += line.vat_exempt
                    suma_total_vat_general_base += line.vat_general_base
                    suma_total_vat_general_tax += line.vat_general_tax
                    suma_total_vat_reduced_base += line.vat_reduced_base
                    suma_total_vat_reduced_tax += line.vat_reduced_tax
                    suma_total_vat_additional_base += line.vat_additional_base
                    suma_total_vat_additional_tax += line.vat_additional_tax

                    # RESUMEN LIBRO DE VENTAS

                    # suma_ali_gene_addi =  suma_vat_additional_base if line.vat_additional_base else 0.0
                    # suma_ali_gene_addi_debit = suma_vat_additional_tax if line.vat_additional_tax else 0.0
                    total_ventas_base_imponible = suma_vat_general_base + suma_vat_additional_base + suma_vat_reduced_base + suma_no_taxe_sale
                    total_ventas_debit_fiscal = suma_vat_general_tax + suma_vat_additional_tax + suma_vat_reduced_tax
                else:
                    docs_ajustes.append({
                        'rannk': line.rank,
                        'emission_date': datetime.strftime(
                            datetime.strptime(str(line.emission_date), DEFAULT_SERVER_DATE_FORMAT), format_new),
                        'partner_vat': line.partner_vat if line.partner_vat else ' ',
                        'partner_name': line.partner_name,
                        'people_type': line.people_type if line.people_type else ' ',
                        'report_z': line.z_report if line.z_report else ' ',
                        'export_form': '',
                        'wh_number': line.wh_number,
                        'date_wh_number': line.iwdl_id.retention_id.date_ret if line.wh_number != '' else '',
                        'invoice_number': line.invoice_number,
                        'n_ultima_factZ': line.n_ultima_factZ,
                        'ctrl_number': line.ctrl_number,
                        'debit_note': line.numero_debit_credit if line.doc_type == 'N/DB' else False,
                        'credit_note': line.numero_debit_credit if line.doc_type == 'N/CR' else False,
                        'type': line.void_form,
                        'affected_invoice': line.affected_invoice if line.affected_invoice else ' ',
                        'total_w_iva': line.total_with_iva if line.total_with_iva else 0,
                        'no_taxe_sale': line.vat_exempt,
                        'export_sale': '',
                        'vat_general_base': vat_general_base,  # + vat_reduced_base + vat_additional_base,
                        'vat_general_rate': str(vat_general_rate),
                        # + '  ' + str(vat_reduced_rate) + ' ' + str(vat_additional_rate) + '  ',
                        'vat_general_tax': vat_general_tax,  # + vat_reduced_tax + vat_additional_tax,
                        'vat_reduced_base': line.vat_reduced_base,
                        'vat_reduced_rate': str(vat_reduced_rate),
                        'vat_reduced_tax': vat_reduced_tax,
                        'vat_additional_base': vat_additional_base,
                        'vat_additional_rate': str(vat_additional_rate),
                        'vat_additional_tax': vat_additional_tax,
                        'get_wh_vat': line.get_wh_vat,
                    })



        date_start = datetime.strftime(datetime.strptime(data['form']['date_from'], DEFAULT_SERVER_DATE_FORMAT),
                                       format_new)
        date_end = datetime.strftime(datetime.strptime(data['form']['date_to'], DEFAULT_SERVER_DATE_FORMAT), format_new)

        if fbl_obj.fb_id.company_id and fbl_obj.fb_id.company_id.street:
            street = str(fbl_obj.env.company.street) + ','
        else:
            street = ' '

        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'date_start': date_start,
            'date_end': date_end,
            'docs': docs,
            'docs_ajustes': docs_ajustes,
            'a': 0.00,
            'street': street,
            'company': fbl_obj.fb_id.company_id,
            'suma_total_w_iva': suma_total_w_iva,
            'suma_no_taxe_sale': suma_no_taxe_sale,
            'suma_total_vat_general_base': suma_total_vat_general_base,
            'suma_total_vat_general_tax': suma_total_vat_general_tax,
            'suma_vat_general_base': suma_vat_general_base,
            'suma_vat_general_tax': suma_vat_general_tax,
            'suma_total_vat_reduced_base': suma_total_vat_reduced_base,
            'suma_total_vat_reduced_tax': suma_total_vat_reduced_tax,
            'suma_total_vat_additional_base': suma_total_vat_additional_base,
            'suma_total_vat_additional_tax': suma_total_vat_additional_tax,
            'suma_vat_reduced_base': suma_vat_reduced_base,
            'suma_vat_reduced_tax': suma_vat_reduced_tax,
            'suma_vat_additional_base': suma_vat_additional_base,
            'suma_vat_additional_tax': suma_vat_additional_tax,
            'suma_get_wh_vat': suma_get_wh_vat,
            'suma_ali_gene_addi': suma_vat_additional_base,
            'suma_ali_gene_addi_debit': suma_vat_additional_tax,
            'total_ventas_base_imponible': total_ventas_base_imponible,
            'total_ventas_debit_fiscal': total_ventas_debit_fiscal,
        }
#
#
# FiscalBookWizard()
