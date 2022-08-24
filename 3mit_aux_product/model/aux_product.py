# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import itertools
import logging

from odoo import api, fields, models, tools, _

_logger = logging.getLogger(__name__)


class ProductTemplateInherit(models.Model):
    _inherit = "product.template"

    aux_price = fields.Float('Precio Auxiliar')

class CurrencyRateNew(models.Model):
    _inherit = 'res.currency.rate'

    @api.onchange('rate')
    def onchange_tasa_precios(self):
        tasa = self.rate
        productos = self.env['product.template'].search([])
        for prod in productos:
            if prod.aux_price != 0:
                monto_aux = prod.aux_price
                prod.list_price = monto_aux * tasa
        return
