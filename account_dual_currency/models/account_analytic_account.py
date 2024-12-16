# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.osv import expression
from collections import defaultdict

class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    currency_id_dif = fields.Many2one("res.currency",
                                      string="Divisa de Referencia",
                                      related="company_id.currency_id_dif")

    balance_usd = fields.Monetary(currency_field='currency_id_dif', compute='_compute_debit_credit_balance', string='Balance $',
                              groups='account.group_account_readonly')
    debit_usd = fields.Monetary(currency_field='currency_id_dif',compute='_compute_debit_credit_balance', string='Debito $',
                            groups='account.group_account_readonly')
    credit_usd = fields.Monetary(currency_field='currency_id_dif',compute='_compute_debit_credit_balance', string='Credito $',
                             groups='account.group_account_readonly')

    @api.depends('line_ids.amount', 'line_ids.amount_usd')
    def _compute_debit_credit_balance(self):
        Curr = self.env['res.currency']
        analytic_line_obj = self.env['account.analytic.line']
        domain = [
            ('account_id', 'in', self.ids),
            ('company_id', 'in', [False] + self.env.companies.ids)
        ]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))
        if self._context.get('tag_ids'):
            tag_domain = expression.OR([[('tag_ids', 'in', [tag])] for tag in self._context['tag_ids']])
            domain = expression.AND([domain, tag_domain])

        user_currency = self.env.company.currency_id
        credit_groups = analytic_line_obj.read_group(
            domain=domain + [('amount', '>=', 0.0)],
            fields=['account_id', 'currency_id', 'amount', 'amount_usd'],
            groupby=['account_id', 'currency_id'],
            lazy=False,
        )
        data_credit = defaultdict(float)
        data_credit_usd = defaultdict(float)
        for l in credit_groups:
            data_credit[l['account_id'][0]] += Curr.browse(l['currency_id'][0])._convert(
                l['amount'], user_currency, self.env.company, fields.Date.today())
            data_credit_usd[l['account_id'][0]] += l['amount_usd']

        debit_groups = analytic_line_obj.read_group(
            domain=domain + [('amount', '<', 0.0)],
            fields=['account_id', 'currency_id', 'amount','amount_usd'],
            groupby=['account_id', 'currency_id'],
            lazy=False,
        )
        data_debit = defaultdict(float)
        data_debit_usd = defaultdict(float)
        for l in debit_groups:
            data_debit[l['account_id'][0]] += Curr.browse(l['currency_id'][0])._convert(
                l['amount'], user_currency, self.env.company, fields.Date.today())
            data_debit_usd[l['account_id'][0]] += l['amount_usd']

        for account in self:
            account.debit = abs(data_debit.get(account.id, 0.0))
            account.credit = data_credit.get(account.id, 0.0)
            account.balance = account.credit - account.debit

            account.debit_usd = abs(data_debit_usd.get(account.id, 0.0))
            account.credit_usd = data_credit_usd.get(account.id, 0.0)
            account.balance_usd = account.credit_usd - account.debit_usd