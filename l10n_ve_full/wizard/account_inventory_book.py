# coding: utf-8
from odoo import fields, models, api, _
import time
from datetime import datetime, date, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT

class AccountInventoryBookWizard(models.TransientModel):
    _name = "account.inventory.book.wizard"

    date_start = fields.Date("Fecha de Inicio", required=True, default=time.strftime('%Y-%m-%d'))
    date_end = fields.Date("Fecha Fin", required=True, default=time.strftime('%Y-%m-%d'))
    product_type_filter = fields.Selection([("all", _("Todos los productos")),
            ("category", _("Categoría")),
            ("product", _("Producto")),
        ], "Filtar por", required=True, default='all')

    category_ids = fields.Many2many(comodel_name='product.category', string='Categoría')
    product_ids = fields.Many2many(comodel_name='product.product', string='Producto', domain="[('detailed_type','=','product')]")
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)

    @api.onchange('product_type_filter')
    def _onchange_product_type_filter(self):
        for rec in self:
            if rec.product_type_filter == 'all':
                rec.product_ids = False
                rec.category_ids = False
            elif rec.product_type_filter == 'category':
                rec.product_ids = False
            elif rec.product_type_filter == 'product':
                rec.category_ids = False

    def imprimir_pdf(self):
        for rec in self:
            data = {
                'ids': 0,
                'form': {
                    'date_from': self.date_start,
                    'date_to': self.date_end,
                    'category_ids': self.category_ids.ids if self.category_ids else [],
                    'product_ids': self.product_ids.ids if self.product_ids else [],
                    'company': self.company_id.id
                }
            }
            return self.env.ref('l10n_ve_full.report_inventary_book').report_action(self, data=data)  # , config=False


    def imprimir_xlsx(self):
        for rec in self:
            pass

class AccountInventoryBookReport(models.AbstractModel):
    _name = 'report.l10n_ve_full.report_invantary_book_template'

    @api.model
    def _get_report_values(self, docids, data=None):
        format_new = "%d/%m/%Y"
        date_start = datetime.strptime(data['form']['date_from'], DATE_FORMAT)
        date_end = datetime.strptime(data['form']['date_to'], DATE_FORMAT)
        company_id = self.env['res.company'].search([('id','=',data['form']['company'])])
        datos = []
        dominio_productos = ['|',('company_id','=',company_id.id),('company_id','=',False),('detailed_type','=','product')]

        if data['form']['category_ids']:
            dominio_productos.append(('categ_id','in',data['form']['category_ids']))
        if data['form']['product_ids']:
            dominio_productos.append(('id', 'in', data['form']['product_ids']))

        productos_ids = self.env['product.product'].search(dominio_productos)
        for p in productos_ids:
            #buscar saldos iniciales del producto
            inciales_ids = self.env['stock.valuation.layer'].search([('product_id','=',p.id),('create_date','<',data['form']['date_from'])])
            existencia_inicial = 0
            precio_inicial = 0
            precio_total_inicial = 0
            if inciales_ids:
                existencia_inicial = sum(inciales_ids.mapped('quantity'))
                precio_inicial = sum(inciales_ids.mapped('value')) / existencia_inicial
                precio_total_inicial = sum(inciales_ids.mapped('value'))

            #inventario del mes
            inventario_mes_ids = self.env['stock.valuation.layer'].search(
                [('product_id', '=', p.id), ('create_date', '>=', data['form']['date_from']), ('create_date', '<=', data['form']['date_to'])])

            entradas_mes = 0
            entradas_mes_precio = 0
            entradas_mes_precio_total = 0
            salida_mes = 0
            salida_mes_precio = 0
            salida_mes_precio_total = 0
            if inventario_mes_ids:
                entadas_ids = inventario_mes_ids.filtered(lambda x: x.quantity > 0)
                salidas_ids = inventario_mes_ids.filtered(lambda x: x.quantity < 0)
                if entadas_ids:
                    entradas_mes = sum(entadas_ids.mapped('quantity'))
                    entradas_mes_precio = sum(entadas_ids.mapped('value')) / entradas_mes
                    entradas_mes_precio_total = sum(entadas_ids.mapped('value'))
                if salidas_ids:
                    salida_mes = abs(sum(salidas_ids.mapped('quantity')))
                    salida_mes_precio = abs(sum(salidas_ids.mapped('value')) / salida_mes)
                    salida_mes_precio_total = abs(sum(salidas_ids.mapped('value')))

            final = existencia_inicial + entradas_mes - salida_mes
            final_precio_total = precio_total_inicial + entradas_mes_precio_total - salida_mes_precio_total
            final_precio = (final_precio_total / final) if final > 0 else 0

            datos.append({
                'default_code': p.default_code or '',
                'name': p.name,
                'existencia_inicial':existencia_inicial,
                'precio_inicial':precio_inicial,
                'precio_total_inicial':precio_total_inicial,
                'entradas_mes':entradas_mes,
                'entradas_mes_precio':entradas_mes_precio,
                'entradas_mes_precio_total':entradas_mes_precio_total,
                'salida_mes':salida_mes,
                'salida_mes_precio':salida_mes_precio,
                'salida_mes_precio_total':salida_mes_precio_total,
                'final': final,
                'final_precio': final_precio,
                'final_precio_total': final_precio_total
            })

        return {
            'company': company_id,
            'currency': company_id.currency_id,
            'date_start': date_start,
            'date_end': date_end,
            'datos':datos,
        }
