# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields
from odoo.tools.sql import create_index


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    followup_line_id = fields.Many2one('account_followup.followup.line', 'Follow-up Level', copy=False)
    last_followup_date = fields.Date('Latest Follow-up', index=True, copy=False)  # TODO remove in master
    next_action_date = fields.Date('Next Action Date',  # TODO remove in master
                                   help="Date where the next action should be taken for a receivable item. Usually, "
                                        "automatically set when sending reminders through the customer statement.")
    invoice_date = fields.Date(related='move_id.invoice_date')
    invoice_origin = fields.Char(related='move_id.invoice_origin')

    def init(self):
        super().init()
        create_index(self.env.cr, 'account_move_line__unreconciled_index', 'account_move_line', ['account_id', 'partner_id'], where="reconciled IS NOT TRUE AND parent_state = 'posted'")
