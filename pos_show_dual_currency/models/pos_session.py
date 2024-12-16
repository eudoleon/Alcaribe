from collections import defaultdict
from datetime import timedelta
from itertools import groupby

from odoo import api, fields, models, _, Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import float_is_zero, float_compare
from odoo.osv.expression import AND, OR
from odoo.service.common import exp_version

class PosSession(models.Model):
    _inherit = "pos.session"

    tax_today = fields.Float(string="Tasa Sesión", store=True,
                             compute="_tax_today",
                             track_visibility='onchange', digits='Dual_Currency_rate')
    @api.depends('config_id')
    def _tax_today(self):
        for rec in self:
            #-----------------------------------------------------
            # CORRECCION: DIVIDE CERO
            #-----------------------------------------------------
            rec.tax_today = 0.04
            if rec.config_id.show_currency_rate != 0:
                rec.tax_today = 1 / rec.config_id.show_currency_rate

    def _loader_params_pos_payment_method(self):
        return {
            'search_params': {
                'domain': ['|', ('active', '=', False), ('active', '=', True)],
                'fields': ['name', 'is_cash_count', 'use_payment_terminal', 'split_transactions', 'type','currency_id'],
                'order': 'is_cash_count desc, id',
            },
        }

    def _create_cash_statement_lines_and_cash_move_lines(self, data):
        # Create the split and combine cash statement lines and account move lines.
        # `split_cash_statement_lines` maps `journal` -> split cash statement lines
        # `combine_cash_statement_lines` maps `journal` -> combine cash statement lines
        # `split_cash_receivable_lines` maps `journal` -> split cash receivable lines
        # `combine_cash_receivable_lines` maps `journal` -> combine cash receivable lines
        MoveLine = data.get('MoveLine')
        split_receivables_cash = data.get('split_receivables_cash')
        combine_receivables_cash = data.get('combine_receivables_cash')

        # handle split cash payments
        split_cash_statement_line_vals = []
        split_cash_receivable_vals = []
        for payment, amounts in split_receivables_cash.items():
            journal_id = payment.payment_method_id.journal_id.id
            split_cash_statement_line_vals.append(
                self._get_split_statement_line_vals(
                    journal_id,
                    amounts['amount'],
                    payment
                )
            )
            split_cash_receivable_vals.append(
                self._get_split_receivable_vals(
                    payment,
                    amounts['amount'],
                    amounts['amount_converted']
                )
            )
        # handle combine cash payments
        combine_cash_statement_line_vals = []
        combine_cash_receivable_vals = []
        for payment_method, amounts in combine_receivables_cash.items():
            if not float_is_zero(amounts['amount'], precision_rounding=self.currency_id.rounding):
                combine_cash_statement_line_vals.append(
                    self._get_combine_statement_line_vals(
                        payment_method.journal_id.id,
                        amounts['amount'] if payment_method.currency_id == self.currency_id else amounts['amount'] * self.config_id.show_currency_rate,
                        payment_method
                    )
                )
                combine_cash_receivable_vals.append(
                    self._get_combine_receivable_vals(
                        payment_method,
                        amounts['amount'] if payment_method.currency_id == self.currency_id else amounts['amount'] * self.config_id.show_currency_rate,
                        amounts['amount_converted']
                    )
                )

        # create the statement lines and account move lines
        BankStatementLine = self.env['account.bank.statement.line']
        split_cash_statement_lines = {}
        combine_cash_statement_lines = {}
        split_cash_receivable_lines = {}
        combine_cash_receivable_lines = {}
        split_cash_statement_lines = BankStatementLine.create(split_cash_statement_line_vals).mapped(
            'move_id.line_ids').filtered(lambda line: line.account_id.account_type == 'asset_receivable')

        combine_cash_statement_lines = BankStatementLine.create(combine_cash_statement_line_vals).mapped(
            'move_id.line_ids').filtered(lambda line: line.account_id.account_type == 'asset_receivable')
        split_cash_receivable_lines = MoveLine.create(split_cash_receivable_vals)
        combine_cash_receivable_lines = MoveLine.create(combine_cash_receivable_vals)

        data.update(
            {'split_cash_statement_lines': split_cash_statement_lines,
             'combine_cash_statement_lines': combine_cash_statement_lines,
             'split_cash_receivable_lines': split_cash_receivable_lines,
             'combine_cash_receivable_lines': combine_cash_receivable_lines
             })
        return data

