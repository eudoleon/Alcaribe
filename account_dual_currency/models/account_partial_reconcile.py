# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

from datetime import date


class AccountPartialReconcile(models.Model):
    _inherit = "account.partial.reconcile"

    company_currency_id_dif = fields.Many2one(
        comodel_name='res.currency',
        string="Company Currency",
        related='company_id.currency_id_dif')

    # ==== Amount fields ====
    amount_usd = fields.Monetary(
        currency_field='company_currency_id_dif',
        help="Always positive amount concerned by this matching expressed in the company currency.",default=0)
