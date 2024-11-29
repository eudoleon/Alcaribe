###############################################################################
# Author: Jesus Pozzo
# Copyleft: 2023-Present.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
#
#
###############################################################################

import xlwt  # libreria para xlxs
import xlsxwriter
import base64
import calendar
from io import StringIO
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError, Warning
from datetime import datetime
from PIL import Image  # Librería para manipular imágenes

import logging


_logger = logging.getLogger(__name__)


style_number = xlwt.XFStyle()
style_number.num_format_str = '$#,##0.000'

style_number2 = xlwt.XFStyle()
style_number2.num_format_str = '_ Bs.S#,##0.000'


class AccountReportCXP(models.TransientModel):
    _name = 'account.invoice.report.cxp'
    _description = 'Reporte de Cuentas por PAGAR'

    start_date = fields.Date(
        string='Fecha Inicio', required=True, default=datetime.today().replace(day=1))

    end_date = fields.Date(string="Fecha Fin", required=True, default=datetime.now().replace(
        day=calendar.monthrange(datetime.now().year, datetime.now().month)[1]))

    invoice_data = fields.Char(string='Name')

    file_name = fields.Binary('Descargar', readonly=True)

    state = fields.Selection(
        [('choose', 'choose'), ('get', 'get')], default='choose')
    consolidado = fields.Boolean(default=False, string="Consolidado?")

    def action_invoices_report(self):
        current_company_id = self.env.company

        # Guardar el logo temporalmente en formato BMP
        logo_path = '/tmp/logo.bmp'
        if current_company_id.logo:
            logo_data = base64.b64decode(current_company_id.logo)
            with open('/tmp/logo.png', 'wb') as logo_file:
                logo_file.write(logo_data)
            # Convertir PNG a BMP
            with Image.open('/tmp/logo.png') as img:
                img.convert("RGB").save(logo_path, "BMP")

        query = """
        SELECT 
            m.id, 
            m.name, 
            m.date,
            m.tax_day, 
            m.amount_total, 
            m.amount_residual, 
            m.debit_origin_id, 
            m.amount_residual_bs, 
            m.tax_day, 
            m.amount_total_bs, 
            m.partner_id,
            p.name as partner_name,
            p.vat as partner_vat,
            m.ticket_fiscal,
            m.ticket_fiscal_pos
        FROM 
            account_move m
        JOIN res_partner p ON m.partner_id = p.id
        WHERE 
            m.move_type = 'in_invoice' 
            AND m.amount_residual != 0
            AND m.date BETWEEN %s AND %s
            AND m.state = 'posted'
            AND m.company_id = %s;
        """
        self.env.cr.execute(query, (self.start_date, self.end_date, current_company_id.id))
        result = self.env.cr.dictfetchall()

        if result:
            filename = '/tmp/cuentas_por_pagar.xls'
            workbook = xlwt.Workbook()
            sheet = workbook.add_sheet("CUENTAS POR PAGAR")

            # Formatos
            title_style = xlwt.easyxf(
                'font: bold 1, height 480; align: vert center, horiz center; pattern: pattern solid, fore_colour gray25'
            )
            header_style = xlwt.easyxf(
                'font: bold 1; align: vert center, horiz center; borders: bottom medium, top medium; pattern: pattern solid, fore_colour gray25'
            )
            info_style = xlwt.easyxf('align: vert center, horiz left; borders: bottom medium')
            cell_style = xlwt.easyxf(
                'align: vert center, horiz center; borders: left thin, right thin, top thin, bottom thin'
            )
            # Estilo para montos con formato numérico local (coma para decimales y punto para miles, con dos decimales)
            decimal_style = xlwt.easyxf(
                'align: vert center, horiz right; borders: left thin, right thin, top thin, bottom thin'
            )
            decimal_style.num_format_str = '#.#0,0'  # Punto para miles, coma para decimales, exactamente 2 decimales

            # Agregar logo con menor tamaño
            if current_company_id.logo:
                sheet.insert_bitmap(logo_path, 0, 0, scale_x=0.3, scale_y=0.3)

            # Información de la empresa al lado del logo
            sheet.write_merge(0, 0, 3, 7, "CUENTAS POR PAGAR", title_style)
            sheet.write(1, 3, "Empresa:", header_style)
            sheet.write(1, 4, current_company_id.name, info_style)
            sheet.write(2, 3, "R.I.F.:", header_style)
            sheet.write(2, 4, current_company_id.vat or "No posee RIF asociado", info_style)
            sheet.write(3, 3, "Fecha desde:", header_style)
            sheet.write(3, 4, self.start_date.strftime('%d/%m/%Y'), info_style)
            sheet.write(3, 5, "Fecha hasta:", header_style)
            sheet.write(3, 6, self.end_date.strftime('%d/%m/%Y'), info_style)

            # Encabezado de la tabla
            sheet.write(6, 0, "Fecha", header_style)
            sheet.write(6, 1, "RIF", header_style)
            sheet.write(6, 2, "Nombre o Razon Social", header_style)
            sheet.write(6, 3, "N° de Documento", header_style)
            sheet.write(6, 4, "Tipo de Documento", header_style)
            sheet.write(6, 5, "Monto Total Bs.", header_style)
            sheet.write(6, 6, "Deuda (Bs.)", header_style)
            sheet.write(6, 7, "Tasa BCV", header_style)

            # Ajustar ancho de columnas
            sheet.col(0).width = 256 * 12  # Fecha
            sheet.col(1).width = 256 * 15  # RIF
            sheet.col(2).width = 256 * 70  # Nombre o Razon Social
            sheet.col(3).width = 256 * 20  # N° de Documento
            sheet.col(4).width = 256 * 20  # Tipo de Documento
            sheet.col(5).width = 256 * 15  # Monto Total Bs.
            sheet.col(6).width = 256 * 15  # Deuda
            sheet.col(7).width = 256 * 12  # Tasa BCV

            # Agregar datos de la tabla
            i = 7
            for inv in result:
                amount_residual_calc = round(inv.get('amount_residual', 0) * inv.get('tax_day', 1), 2)
                amount_total_bs = round(inv.get('amount_total_bs', 0), 2)
                sheet.write(i, 0, inv.get('date').strftime('%d/%m/%Y'), cell_style)
                sheet.write(i, 1, inv.get('partner_vat'), cell_style)
                sheet.write(i, 2, inv.get('partner_name').upper(), cell_style)
                sheet.write(i, 3, inv.get('name').upper(), cell_style)
                sheet.write(i, 4, "NOTA DE DEBITO" if inv.get('debit_origin_id') else "FACTURA", cell_style)
                sheet.write(i, 5, amount_total_bs, decimal_style)
                sheet.write(i, 6, amount_residual_calc, decimal_style)
                sheet.write(i, 7, inv.get('tax_day'), cell_style)
                i += 1

            # Guardar archivo
            workbook.save(filename)
            file = open(filename, "rb")
            file_data = file.read()
            out = base64.encodebytes(file_data)
            self.write({
                'state': 'get',
                'file_name': out,
                'invoice_data': 'cuentas_por_pagar.xls'
            })

            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.invoice.report.cxp',
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': self.id,
                'target': 'new',
            }
        else:
            raise ValidationError(
                "No hay facturas, ND, NC y retenciones para el rango de fecha especificado"
            )