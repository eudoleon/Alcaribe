# -*- coding: utf-8 -*-

from odoo import models, fields, _


# --------------------------------------------------------------------
# This model adds new fields on stock.scrap to select reasons on Scrap
# --------------------------------------------------------------------

class StockScrap(models.Model):
    _inherit = "stock.scrap"

    reason_id = fields.Many2one(
        "stock.scrap.reason",
        context={'_order': 'sequence asc'}
    )
    note = fields.Text()
