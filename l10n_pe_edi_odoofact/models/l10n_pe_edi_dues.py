# -*- coding: utf-8 -*-
###############################################################################
#
#    Copyright (C) 2019-TODAY OPeru.
#    Author      :  Grupo Odoo S.A.C. (<http://www.operu.pe>)
#
#    This program is copyright property of the author mentioned above.
#    You can`t redistribute it and/or modify it.
#
###############################################################################

from odoo import models, fields, api, _

class EdiDues(models.Model):
    _name = 'l10n_pe_edi.dues'
    _description = 'Dues'
    _order = 'dues_number'

    move_id = fields.Many2one("account.move", string="Move", required=True, readonly=True, ondelete="cascade")
    dues_number = fields.Integer(string="Dues Number")
    paid_date = fields.Date(string="Paid Date")
    amount = fields.Float(string="Amount", digits=(16, 2))
