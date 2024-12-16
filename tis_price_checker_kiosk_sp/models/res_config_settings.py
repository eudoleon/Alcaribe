# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd.
# - © Technaureus Info Solutions Pvt. Ltd 2020. All rights reserved.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    kiosk_pricelist_id = fields.Many2one('product.pricelist', string='Kiosk Special Price List',
                                         help="Kiosk Special Price List.")
    is_tax_included_price = fields.Boolean(string='Show Tax Included Price')
    is_pricelist = fields.Boolean()
    show_uom = fields.Boolean(string='Show Unit Of Measure')

    @api.model
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        IrDefault = self.env['ir.default'].sudo()
        IrDefault.set(
            'res.config.settings', "kiosk_pricelist_id", self.kiosk_pricelist_id.id)
        IrDefault.set(
            'res.config.settings', "is_tax_included_price", self.is_tax_included_price)
        IrDefault.set(
            'res.config.settings', "is_pricelist", self.group_product_pricelist)
        IrDefault.set(
            'res.config.settings', "show_uom", self.show_uom)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IrDefault = self.env['ir.default'].sudo()
        kiosk_pricelist_id = IrDefault.get(
            'res.config.settings', "kiosk_pricelist_id")
        is_tax_included_price = IrDefault.get(
            'res.config.settings', "is_tax_included_price")
        is_pricelist = IrDefault.get(
            'res.config.settings', "is_pricelist")
        show_uom = IrDefault.get(
            'res.config.settings', "show_uom")
        res.update(
            kiosk_pricelist_id=kiosk_pricelist_id if kiosk_pricelist_id else False,
            is_tax_included_price=is_tax_included_price if is_tax_included_price else False,
            is_pricelist=is_pricelist if is_pricelist else False,
            show_uom=show_uom if show_uom else False,
        )
        return res
