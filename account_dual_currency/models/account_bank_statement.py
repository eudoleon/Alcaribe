# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, Command

class AccountBankStatement(models.Model):
    _inherit = "account.bank.statement"

    currency_id_journal = fields.Many2one("res.currency",
                                      string="Divisa en Diario", related='journal_id.currency_id')
