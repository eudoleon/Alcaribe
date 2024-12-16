from odoo import models, fields, api
import pandas as pd
import io
import xlsxwriter
import base64
import tempfile
from datetime import datetime

class SaleReportWizard(models.TransientModel):
    _name = 'sale.report.wizard'
    _description = 'Asistente de Reporte de Ventas'

    date_from = fields.Date(string='Desde')
    date_to = fields.Date(string='Hasta')
    report_type = fields.Selection([('pos', 'POS'), ('sale', 'Ventas'), ('both', 'Ambas')], string='Tipo', required=True)
    currency = fields.Selection([('local', 'Local'), ('usd', 'USD'), ('both', 'Ambas')], string='Moneda', required=True)
    group_by = fields.Selection([
        ('customer', 'Cliente'), 
        ('seller', 'Vendedor'), 
        ('product', 'Producto'), 
        ('category', 'Categoría'), 
        ('customer_product', 'Cliente y Producto'),
        ('category_product', 'Categoría y Producto'),
        ('seller_product', 'Vendedor y Producto'),
        ('none', 'Ninguna')
    ], string='Agrupar por', required=True)
    view_type = fields.Selection([('export', 'Excel'), ('pivot', 'Pivot')], string='Tipo de vista', required=True)

    def generate_report(self):
        pos_orders = self.env['pos.order'].search([
            ('date_order', '>=', self.date_from),
            ('date_order', '<=', self.date_to),
            ('state', 'not in', ['draft', 'cancel'])
        ]) if self.report_type in ['pos', 'both'] else []

        sale_orders = self.env['sale.order'].search([
            ('date_order', '>=', self.date_from),
            ('date_order', '<=', self.date_to),
            ('state', 'not in', ['draft', 'cancel'])
        ]) if self.report_type in ['sale', 'both'] else []

        data = []

        for order in pos_orders:
            for line in order.lines:
                data.append(self._prepare_order_data(order, line, 'pos'))

        for order in sale_orders:
            for line in order.order_line:
                data.append(self._prepare_order_data(order, line, 'sale'))

        df = pd.DataFrame(data)
        df_grouped = self._group_and_summarize(df)

        if self.view_type == 'export':
            excel_data = self._export_to_excel(df_grouped)
            filename = f'Reporte_Ventas_{fields.Date.today()}.xlsx'
            
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': base64.b64encode(excel_data.getvalue()),
                'res_model': self._name,
                'res_id': self.id,
            })
            
            url = f'/web/content/{attachment.id}?download=true'
            
            return {
                'type': 'ir.actions.act_url',
                'url': url,
                'target': 'self',
            }
        else:
            return self._show_pivot_view(df_grouped)

    def _prepare_order_data(self, order, line, order_type):
        company_currency = self.env.user.company_id.currency_id
        order_currency = order.pricelist_id.currency_id
        usd_currency = self.env.ref('base.USD')

        # Conversión a moneda local
        if order_currency != company_currency:
            subtotal_local = order_currency._convert(line.price_subtotal, company_currency, order.company_id, order.date_order)
            total_local = order_currency._convert(line.price_subtotal_incl, company_currency, order.company_id, order.date_order)
        else:
            subtotal_local = line.price_subtotal
            total_local = line.price_subtotal_incl

        # Conversión a USD
        if order_currency != usd_currency:
            subtotal_usd = order_currency._convert(line.price_subtotal, usd_currency, order.company_id, order.date_order)
            total_usd = order_currency._convert(line.price_subtotal_incl, usd_currency, order.company_id, order.date_order)
        else:
            subtotal_usd = line.price_subtotal
            total_usd = line.price_subtotal_incl

        return {
            'ID Pedido': order.id if order_type == 'sale' else None,
            'ID Pedido POS': order.id if order_type == 'pos' else None,
            'Nombre': order.name,
            'Fecha': order.date_order,
            'Cliente': order.partner_id.name,
            'Vendedor': order.user_id.name,
            'Moneda': order.pricelist_id.currency_id.name,
            'Subtotal': line.price_subtotal,
            'Total': line.price_subtotal_incl,
            'Subtotal Local': subtotal_local,
            'Total Local': total_local,
            'Subtotal USD': subtotal_usd,
            'Total USD': total_usd,
            'Categoría': line.product_id.categ_id.name,
            'Producto': line.product_id.name,
        }

    def _group_and_summarize(self, df):
        group_columns = {
            'customer': 'Cliente',
            'seller': 'Vendedor',
            'product': 'Producto',
            'category': 'Categoría',
            'customer_product': ['Cliente', 'Producto'],
            'category_product': ['Categoría', 'Producto'],
            'seller_product': ['Vendedor', 'Producto']
        }

        group_by_column = group_columns.get(self.group_by)
        if not group_by_column or self.group_by == 'none':
            return df

        if isinstance(group_by_column, list):
            df_grouped = df.groupby(group_by_column).agg({
                'Subtotal': 'sum',
                'Total': 'sum',
                'Subtotal Local': 'sum',
                'Total Local': 'sum',
                'Subtotal USD': 'sum',
                'Total USD': 'sum',
            }).reset_index()

            # Agregar filas de subtotal
            subtotal_dfs = []
            for first_group in df_grouped[group_by_column[0]].unique():
                subtotal_df = df_grouped[df_grouped[group_by_column[0]] == first_group].copy()
                subtotal_row = subtotal_df.sum(numeric_only=True).to_frame().T
                subtotal_row[group_by_column[0]] = first_group
                subtotal_row[group_by_column[1]] = 'Subtotal'
                subtotal_dfs.append(subtotal_df)
                subtotal_dfs.append(subtotal_row)
            
            df_grouped = pd.concat(subtotal_dfs).reset_index(drop=True)
        else:
            df_grouped = df.groupby(group_by_column).agg({
                'Subtotal': 'sum',
                'Total': 'sum',
                'Subtotal Local': 'sum',
                'Total Local': 'sum',
                'Subtotal USD': 'sum',
                'Total USD': 'sum',
            }).reset_index()

        return df_grouped

    def _export_to_excel(self, df):
        output = io.BytesIO()
        
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        base_name = 'Reporte de Ventas'
        worksheet_name = base_name
        sheet_index = 1

        while True:
            try:
                worksheet = workbook.add_worksheet(worksheet_name)
                break
            except xlsxwriter.exceptions.DuplicateWorksheetName:
                worksheet_name = f"{base_name} {sheet_index}"
                sheet_index += 1

        # Define formatos
        format_header = workbook.add_format({
            'bold': True,
            'bg_color': '#4F81BD',
            'color': 'white',
            'border': 1
        })
        format_data = workbook.add_format({
            'border': 1
        })
        format_totals = workbook.add_format({
            'bg_color': '#DCE6F1',
            'border': 1,
            'bold': True
        })

        # Agregar logo y datos de la empresa
        company = self.env.user.company_id
        worksheet.merge_range('A1:D1', company.name, workbook.add_format({'bold': True, 'font_size': 20}))
        worksheet.write('A2', 'Dirección:', workbook.add_format({'bold': True}))
        worksheet.write('B2', company.partner_id.street or '')
        worksheet.write('A3', 'Ciudad:', workbook.add_format({'bold': True}))
        worksheet.write('B3', company.partner_id.city or '')
        worksheet.write('A4', 'RIF:', workbook.add_format({'bold': True}))
        worksheet.write('B4', company.vat or '')

        if company.logo:
            logo_data = base64.b64decode(company.logo)
            image_stream = io.BytesIO(logo_data)
            worksheet.insert_image('E1', 'company_logo.png', {'image_data': image_stream, 'x_scale': 0.5, 'y_scale': 0.5})

        # Escribir datos del DataFrame en Excel
        for col_num, column in enumerate(df.columns):
            worksheet.write(4, col_num, column, format_header)

        for row_num, row in df.iterrows():
            for col_num, value in enumerate(row):
                worksheet.write(row_num + 5, col_num, value, format_data)

        # Aplicar formato a las filas de totales
        for col_num, column in enumerate(df.columns):
            if col_num > 3:  # Comenzando desde la columna Subtotal
                worksheet.write(len(df) + 5, col_num, df[column].sum(), format_totals)

        worksheet.set_column('A:Z', 18)

        workbook.close()
        output.seek(0)

        return output

    def _show_pivot_view(self, df):
        view_id = self.env.ref('sale_report_module.view_sale_report_pivot').id
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Reporte de Ventas Pivot',
            'view_mode': 'pivot',
            'res_model': 'sale.report.custom',
            'views': [(view_id, 'pivot')],
            'context': {'default_data': df.to_dict('records')}
        }
        return action

class SaleReport(models.Model):
    _name = 'sale.report.custom'
    _description = 'Reporte de Ventas'

    # Define los campos necesarios para el reporte
    order_id = fields.Many2one('sale.order', string='ID Pedido')
    pos_order_id = fields.Many2one('pos.order', string='ID Pedido POS')
    name = fields.Char(string='Nombre del Pedido')
    date = fields.Date(string='Fecha')
    customer = fields.Many2one('res.partner', string='Cliente')
    seller = fields.Many2one('res.users', string='Vendedor')
    currency = fields.Many2one('res.currency', string='Moneda')
    subtotal = fields.Float(string='Subtotal')
    tax = fields.Float(string='Tax')
    discount = fields.Float(string='Discount')
    total = fields.Float(string='Total')
    subtotal_local = fields.Float(string='Subtotal Local')
    tax_local = fields.Float(string='Tax Local')
    discount_local = fields.Float(string='Discount Local')
    total_local = fields.Float(string='Total Local')
    subtotal_usd = fields.Float(string='Subtotal USD')
    tax_usd = fields.Float(string='Tax USD')
    discount_usd = fields.Float(string='Discount USD')
    total_usd = fields.Float(string='Total USD')
    category = fields.Many2one('product.category', string='Categoría')
    product = fields.Many2one('product.product', string='Producto')