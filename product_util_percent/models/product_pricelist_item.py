# -*- coding: utf-8 -*-
# Copyright© 2016 ICTSTUDIO <http://www.ictstudio.eu>
# License: LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl)

import logging

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

class ProductPricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    util_percentage = fields.Float(
        string='Porcentaje de Utilidad',
        help='Porcentaje para el calculo de utldad')

    def change_product(self):
        for rec in self:
            if rec.product_tmpl_id:
                rec.product_tmpl_id.write({})
            if rec.product_id:
                rec.product_id.write({})
        return True

    def unlink(self):
        self.change_product()
        return super(ProductPricelistItem, self).unlink()

    @api.onchange('util_percentage')
    def _onchange_util_percentage(self):
        new_utilidad = (100-self.util_percentage)/100
        new_price = self.product_tmpl_id.standard_price/new_utilidad
        self.fixed_price=new_price

    def write(self, vals):
        _logger.warning(['price_surcharge'])
        _logger.warning("Precio %s", self.product_tmpl_id.name)
        _logger.warning("Utilidad %f", self.util_percentage)
        _logger.warning("Costo %f", self.product_tmpl_id.standard_price)

        new_utilidad = (100-self.util_percentage)/100
        new_price = self.product_tmpl_id.standard_price/new_utilidad
        _logger.warning("Precio %f", new_price)
        _logger.warning("prc utilidad  %f", new_utilidad)
        #vals['price_surcharge']=new_price
        self.change_product()
        return super(ProductPricelistItem, self).write(vals)

    @api.model
    def create(self, vals):
        self.change_product()
        return super(ProductPricelistItem, self).create(vals)