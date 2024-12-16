# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, Command


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    currency_id_dif_statement = fields.Many2one("res.currency",
                                                string="Divisa de Referencia",
                                                default=lambda self: self.env.company.currency_id_dif)

    tasa_referencia_statement = fields.Float(string="Tasa", store=True, default=lambda self: self._get_default_tasa())

    amount_usd_statement = fields.Monetary(currency_field='currency_id_dif_statement', string='Total Ref.', store=True,
                                           readonly=True, compute='_amount_usd',
                                           digits='Dual_Currency')

    @api.onchange('date')
    def _onchange_date(self):
        for rec in self:
            rec._get_default_tasa()

    def _get_default_tasa(self):
        for rec in self:
            tasa_referencia_statement = 0
            if rec.date:
                domain = [('name', '=', rec.date), ('currency_id', '=', rec.currency_id_dif_statement.id),
                          ('company_id', '=', self.env.company.id)]
                # #print(domain)
                tasa_fecha = self.env['res.currency.rate'].search(domain)
                if tasa_fecha:
                    tasa_referencia_statement = tasa_fecha.inverse_company_rate
                else:
                    tasa_referencia_statement = self.env.company.currency_id_dif.inverse_rate
            else:
                tasa_referencia_statement = self.env.company.currency_id_dif.inverse_rate
            #print(' obteniendo la tasa ', tasa_referencia_statement)
            rec.tasa_referencia_statement = tasa_referencia_statement
            return tasa_referencia_statement

    @api.depends('tasa_referencia_statement', 'amount', 'currency_id_dif_statement', 'statement_id.currency_id_journal')
    def _amount_usd(self):
        for rec in self:
            if rec.statement_id.currency_id_journal == rec.currency_id_dif_statement:
                rec.amount_usd_statement = rec.amount
            else:
                rec.amount_usd_statement = (
                        rec.amount / rec.tasa_referencia_statement) if rec.tasa_referencia_statement > 0 else 0

    @api.model_create_multi
    def create(self, vals_list):
        # OVERRIDE
        tasa = self._get_default_tasa()
        for vals in vals_list:
            if not tasa:
                if 'journal_id' in vals:
                    journal = self.env['account.journal'].browse(vals['journal_id'])
                    tasa = journal.company_id.currency_id_dif.inverse_rate
            if 'tasa_referencia_statement' not in vals:
                vals['tasa_referencia_statement'] = tasa
            if not vals['tasa_referencia_statement']:
                vals['tasa_referencia_statement'] = tasa
            vals['tax_today'] = vals['tasa_referencia_statement']
        st_lines = super(AccountBankStatementLine, self).create(vals_list)
        return st_lines

    def write(self, vals):
        # OVERRIDE
        if 'tasa_referencia_statement' in vals:
            vals['tax_today'] = vals['tasa_referencia_statement']
        res = super(AccountBankStatementLine, self).write(vals)
        self._synchronize_to_moves(set(vals.keys()))
        return res

    # def _synchronize_to_moves(self, changed_fields):
    #     # OVERRIDE
    #     #print('valores', changed_fields)
    #     if 'tasa_referencia_statement' in changed_fields:
    #         changed_fields.append('tax_today')
    #     super()._synchronize_to_moves(changed_fields)

    @api.model
    def _prepare_liquidity_move_line_vals(self):
        ''' Prepare values to create a new account.move.line record corresponding to the
        liquidity line (having the bank/cash account).
        :return:        The values to create a new account.move.line record.
        '''
        self.ensure_one()

        statement = self.statement_id
        journal = statement.journal_id
        company_currency = journal.company_id.currency_id
        journal_currency = journal.currency_id or company_currency

        if self.foreign_currency_id and journal_currency:
            currency_id = journal_currency.id
            if self.foreign_currency_id == company_currency:
                amount_currency = self.amount
                balance = self.amount_currency
            else:
                amount_currency = self.amount
                balance = amount_currency * self.tasa_referencia_statement  # journal_currency._convert(amount_currency, company_currency, journal.company_id, self.date)
        elif self.foreign_currency_id and not journal_currency:
            amount_currency = self.amount_currency
            balance = self.amount
            currency_id = self.foreign_currency_id.id
        elif not self.foreign_currency_id and journal_currency:
            currency_id = journal_currency.id
            amount_currency = self.amount
            if journal_currency != company_currency:
                balance = amount_currency * self.tasa_referencia_statement  # journal_currency._convert(amount_currency, journal.company_id.currency_id, journal.company_id,self.date)
            else:
                balance = journal_currency._convert(amount_currency, journal.company_id.currency_id, journal.company_id,
                                                    self.date)
        else:
            currency_id = company_currency.id
            amount_currency = self.amount
            balance = self.amount
        balance_usd = self.amount_usd_statement
        if balance_usd == 0:
            balance_usd = balance / (
                self.tasa_referencia_statement if self.tasa_referencia_statement else self._get_default_tasa())
        # self.move_id.tax_today = self.tasa_referencia_statement if self.tasa_referencia_statement == 0 else self._get_default_tasa()
        valores = {
            'name': self.payment_ref,
            'move_id': self.move_id.id,
            'partner_id': self.partner_id.id,
            'currency_id': currency_id,
            'account_id': journal.default_account_id.id,
            'debit': balance > 0 and balance or 0.0,
            'credit': balance < 0 and -balance or 0.0,
            'debit_usd': balance_usd if balance_usd > 0.0 else 0.0,
            'credit_usd': -balance_usd if balance_usd < 0.0 else 0.0,
            'amount_currency': amount_currency,
        }
        return valores

    @api.model
    def _prepare_counterpart_move_line_vals(self, counterpart_vals, move_line=None):
        ''' Prepare values to create a new account.move.line move_line.
        By default, without specified 'counterpart_vals' or 'move_line', the counterpart line is
        created using the suspense account. Otherwise, this method is also called during the
        reconciliation to prepare the statement line's journal entry. In that case,
        'counterpart_vals' will be used to create a custom account.move.line (from the reconciliation widget)
        and 'move_line' will be used to create the counterpart of an existing account.move.line to which
        the newly created journal item will be reconciled.
        :param counterpart_vals:    A python dictionary containing:
            'balance':                  Optional amount to consider during the reconciliation. If a foreign currency is set on the
                                        counterpart line in the same foreign currency as the statement line, then this amount is
                                        considered as the amount in foreign currency. If not specified, the full balance is took.
                                        This value must be provided if move_line is not.
            'amount_residual':          The residual amount to reconcile expressed in the company's currency.
                                        /!\ This value should be equivalent to move_line.amount_residual except we want
                                        to avoid browsing the record when the only thing we need in an overview of the
                                        reconciliation, for example in the reconciliation widget.
            'amount_residual_currency': The residual amount to reconcile expressed in the foreign's currency.
                                        Using this key doesn't make sense without passing 'currency_id' in vals.
                                        /!\ This value should be equivalent to move_line.amount_residual_currency except
                                        we want to avoid browsing the record when the only thing we need in an overview
                                        of the reconciliation, for example in the reconciliation widget.
            **kwargs:                   Additional values that need to land on the account.move.line to create.
        :param move_line:           An optional account.move.line move_line representing the counterpart line to reconcile.
        :return:                    The values to create a new account.move.line move_line.
        '''
        self.ensure_one()
        statement = self.statement_id
        journal = statement.journal_id
        company_currency = journal.company_id.currency_id
        journal_currency = journal.currency_id or company_currency
        foreign_currency = self.foreign_currency_id or journal_currency or company_currency
        statement_line_rate = (self.amount_currency / self.amount) if self.amount else 0.0

        balance_to_reconcile = counterpart_vals.pop('balance', None)
        amount_residual = -counterpart_vals.pop('amount_residual', move_line.amount_residual if move_line else 0.0) \
            if balance_to_reconcile is None else balance_to_reconcile
        amount_residual_currency = -counterpart_vals.pop('amount_residual_currency',
                                                         move_line.amount_residual_currency if move_line else 0.0) \
            if balance_to_reconcile is None else balance_to_reconcile
        amount_residual_usd = 0
        if company_currency != journal_currency:
            amount_residual_usd = amount_residual_currency
        else:
            amount_residual_usd = -counterpart_vals.pop('amount_residual_usd',
                                                        move_line.amount_residual_usd if move_line else 0.0)
        if 'currency_id' in counterpart_vals:
            currency_id = counterpart_vals['currency_id'] or company_currency.id
        elif move_line:
            currency_id = move_line.currency_id.id or company_currency.id
        else:
            currency_id = foreign_currency.id

        if currency_id not in (foreign_currency.id, journal_currency.id):
            currency_id = company_currency.id
            amount_residual_currency = 0.0

        amounts = {
            company_currency.id: 0.0,
            journal_currency.id: 0.0,
            foreign_currency.id: 0.0,
        }

        amounts[currency_id] = amount_residual_currency
        amounts[company_currency.id] = amount_residual

        if currency_id == journal_currency.id and journal_currency != company_currency:
            if foreign_currency != company_currency:
                amounts[company_currency.id] = journal_currency._convert(amounts[currency_id], company_currency,
                                                                         journal.company_id, self.date)
            if statement_line_rate:
                amounts[foreign_currency.id] = amounts[currency_id] * statement_line_rate
        elif currency_id == foreign_currency.id and self.foreign_currency_id:
            if statement_line_rate:
                amounts[journal_currency.id] = amounts[foreign_currency.id] / statement_line_rate
                if foreign_currency != company_currency:
                    amounts[company_currency.id] = journal_currency._convert(amounts[journal_currency.id],
                                                                             company_currency, journal.company_id,
                                                                             self.date)
        else:
            amounts[journal_currency.id] = company_currency._convert(amounts[company_currency.id], journal_currency,
                                                                     journal.company_id, self.date)
            if statement_line_rate:
                amounts[foreign_currency.id] = amounts[journal_currency.id] * statement_line_rate

        if foreign_currency == company_currency and journal_currency != company_currency and self.foreign_currency_id:
            balance = amounts[foreign_currency.id]
        else:
            balance = amounts[company_currency.id]
            if company_currency != journal_currency:
                balance = amount_residual_usd * self.tasa_referencia_statement

        if foreign_currency != company_currency and self.foreign_currency_id:
            amount_currency = amounts[foreign_currency.id]
            currency_id = foreign_currency.id
        elif journal_currency != company_currency and not self.foreign_currency_id:
            amount_currency = amounts[journal_currency.id]
            currency_id = journal_currency.id
        else:
            amount_currency = amounts[company_currency.id]
            currency_id = company_currency.id
        balance_usd = amount_residual_usd
        if balance_usd == 0:
            balance_usd = balance / (
                self.tasa_referencia_statement if self.tasa_referencia_statement else self._get_default_tasa())
        # self.move_id.tax_today = self.tasa_referencia_statement if self.tasa_referencia_statement == 0 else self._get_default_tasa()
        valores = {
            **counterpart_vals,
            'name': counterpart_vals.get('name', move_line.name if move_line else ''),
            'move_id': self.move_id.id,
            'partner_id': self.partner_id.id or (move_line.partner_id.id if move_line else False),
            'currency_id': currency_id,
            'account_id': counterpart_vals.get('account_id', move_line.account_id.id if move_line else False),
            'debit': balance if balance > 0.0 else 0.0,
            'credit': -balance if balance < 0.0 else 0.0,
            'debit_usd': balance_usd if balance_usd > 0.0 else 0.0,
            'credit_usd': -balance_usd if balance_usd < 0.0 else 0.0,
            'amount_currency': amount_currency,
        }

        return valores
