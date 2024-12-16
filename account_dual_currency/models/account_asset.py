# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class AccountAsset(models.Model):
    _inherit = 'account.asset'

    currency_id_dif = fields.Many2one("res.currency",
                                      string="Moneda Ref.",
                                      related="company_id.currency_id_dif", store=True)

    tax_today = fields.Float(string='Tasa de Cambio', required=True, default=lambda self: self.env.company.currency_id_dif.inverse_rate, digits='Dual_Currency_rate')

    original_value_ref = fields.Monetary(currency_field='currency_id_dif', string='Valor original Ref.', required=True, default=0.0, compute='_compute_values_ref', store=True)

    value_residual_ref = fields.Monetary(currency_field='currency_id_dif', string='Valor depreciable Ref.', required=True, default=0.0, compute='_compute_values_ref', store=True)

    salvage_value_ref = fields.Monetary(currency_field='currency_id_dif', string='Valor no depreciable Ref.', required=True, default=0.0, compute='_compute_values_ref', store=True)

    book_value_ref = fields.Monetary(currency_field='currency_id_dif', string='Valor contable Ref.', required=True, default=0.0, compute='_compute_values_ref', store=True)

    already_depreciated_amount_import_ref = fields.Monetary(currency_field='currency_id_dif', string='Monto depreciado Ref.', required=True, default=0.0, compute='_compute_already_depreciated', store=True)

    total_depreciable_value_ref = fields.Monetary(currency_field='currency_id_dif', compute='_compute_total_depreciable_value_ref')

    @api.depends('salvage_value_ref', 'original_value_ref')
    def _compute_total_depreciable_value_ref(self):
        for asset in self:
            asset.total_depreciable_value_ref = asset.original_value_ref - asset.salvage_value_ref

    @api.depends('original_value', 'salvage_value', 'tax_today', 'currency_id')
    def _compute_values_ref(self):
        for asset in self:
            if asset.currency_id_dif != asset.currency_id:
                asset.original_value_ref = asset.original_value / asset.tax_today
                asset.value_residual_ref = asset.value_residual / asset.tax_today
                asset.salvage_value_ref = asset.salvage_value / asset.tax_today
                asset.book_value_ref = asset.book_value / asset.tax_today
                asset.already_depreciated_amount_import_ref = asset.already_depreciated_amount_import / asset.tax_today
            else:
                asset.original_value_ref = asset.original_value
                asset.value_residual_ref = asset.value_residual
                asset.salvage_value_ref = asset.salvage_value
                asset.book_value_ref = asset.book_value
                asset.already_depreciated_amount_import_ref = asset.already_depreciated_amount_import

    @api.depends('already_depreciated_amount_import', 'tax_today', 'currency_id')
    def _compute_already_depreciated(self):
        for asset in self:
            if asset.currency_id_dif != asset.currency_id:
                asset.already_depreciated_amount_import_ref = asset.already_depreciated_amount_import / asset.tax_today
            else:
                asset.already_depreciated_amount_import_ref = asset.already_depreciated_amount_import

