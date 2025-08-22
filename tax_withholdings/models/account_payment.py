# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    temp_sequence_withholding_iva = fields.Char(
        string="Temporary IVA withholding sequence",
        copy=False,
        readonly=True,
    )
    temp_sequence_withholding_islr = fields.Char(
        string="Temporary ISLR withholding sequence",
        copy=False,
        readonly=True,
    )
