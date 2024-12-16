# -*- coding: utf-8 -*-
# Copyright© 2016 ICTSTUDIO <http://www.ictstudio.eu>
# License: LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl)

import logging

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    fob_price = fields.Float(
        string='Costo FOB',
        help='Costo FOB del articulo')
    fob_percentage = fields.Float(
        string='Porcentaje de Gasto',
        help='Porcentaje de gasto para importacion')
    type_porc = fields.Selection(
        [
            ("porc", "Porcentaje"),
            ("fixed", "Fijo"),
        ],
        default="porc",

    )
    unidad = fields.Char(string="Unidad de medida app")

    @api.onchange('fob_percentage','fob_price','type_porc')
    def _onchange_fob_percentage(self):
        new_price = 0.0
        if self.type_porc == 'porc':
            new_price = self.fob_price+(self.fob_price*self.fob_percentage/100)
        else:
            new_price = self.fob_price+self.fob_percentage
        self.standard_price_usd=new_price
        self._onchange_standard_price_usd()
