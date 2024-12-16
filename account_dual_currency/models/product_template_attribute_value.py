# -*- coding: utf-8 -*-

from itertools import groupby
from odoo import api, fields, models, _
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.exceptions import AccessError, UserError, ValidationError

class ProductTemplateAttributeValue(models.Model):
    _inherit = 'product.template.attribute.value'

    currency_id_dif = fields.Many2one('res.currency', string='Currency USD', default=lambda self: self.env.user.company_id.currency_id_dif.id)

    price_extra_usd = fields.Monetary(string='Precio Extra $', currency_field='currency_id_dif', digits='Dual_Currency')

    @api.onchange('price_extra_usd')
    def _onchange_price_extra_usd(self):
        self.price_extra = self.price_extra_usd * self.currency_id_dif.inverse_rate