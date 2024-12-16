# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class Productos(models.Model):
    _inherit = 'product.template'

    currency_id_dif = fields.Many2one('res.currency', string='Moneda Diferente', default=lambda self: self.env.company.currency_id_dif.id)

    list_price_usd = fields.Monetary(string="Precio de venta $", currency_field='currency_id_dif')
    standard_price_usd = fields.Float(string="Costo $", inverse='_set_standard_price_usd', compute='_compute_standard_price_usd', readonly=False, store=True, currency_field='currency_id_dif')
    costo_reposicion_usd = fields.Monetary(string="Costo Reposición $", currency_field='currency_id_dif')

    def _set_standard_price_usd(self):
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.product_variant_ids.standard_price_usd = template.standard_price_usd

    @api.depends_context('company')
    @api.depends('product_variant_ids', 'product_variant_ids.standard_price_usd')
    def _compute_standard_price_usd(self):
        # Depends on force_company context because standard_price is company_dependent
        # on the product_product
        for rec in self:
            if len(rec.product_variant_ids) == 1:
                rec.standard_price_usd = rec.product_variant_ids[0].standard_price_usd
            else:
                rec.standard_price_usd = 0.0

    @api.onchange('list_price_usd')
    def _onchange_list_price_usd(self):
        for rec in self:
            if rec.list_price_usd:
                if rec.list_price_usd >0:
                    tasa = self.env.company.currency_id_dif
                    if tasa:
                        rec.list_price = rec.list_price_usd * tasa.inverse_rate

    @api.onchange('standard_price_usd')
    def _onchange_standard_price_usd(self):
        for rec in self:
            if len(rec.product_variant_ids) == 1:
                rec.product_variant_ids[0].standard_price_usd = rec.standard_price_usd

            if rec.standard_price_usd and rec.categ_id.property_valuation == 'manual_periodic':
                if rec.standard_price_usd > 0:
                    tasa = self.env.company.currency_id_dif
                    if tasa:
                        rec.standard_price = rec.standard_price_usd * tasa.inverse_rate


