# -*- coding: utf-8 -*-
from odoo import api, models, fields, _
from odoo.exceptions import UserError


class ResUsers(models.Model):
    _inherit = 'res.users'

    kiosk_pricelist_id = fields.Many2one('product.pricelist', string='Kiosk Special Price List',
                                         help="Kiosk Special Price List.")