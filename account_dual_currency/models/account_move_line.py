# -*- coding: utf-8 -*-
from collections import defaultdict
from contextlib import contextmanager
from datetime import date, timedelta
from functools import lru_cache

from odoo import api, fields, models, Command, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import frozendict, formatLang, format_date, float_compare, Query


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    debit_usd = fields.Monetary(currency_field='currency_id_dif', string='Débito $', store=True, compute="_debit_usd",
                                 readonly=False, )
    credit_usd = fields.Monetary(currency_field='currency_id_dif', string='Crédito $', store=True,
                                 compute="_credit_usd", readonly=False)
    tax_today = fields.Float(related="move_id.tax_today", store=True, digits='Dual_Currency_rate')
    currency_id_dif = fields.Many2one("res.currency", related="move_id.currency_id_dif", store=True)
    price_unit_usd = fields.Monetary(currency_field='currency_id_dif', string='Precio $', store=True,
                                     compute='_price_unit_usd', readonly=False)
    price_subtotal_usd = fields.Monetary(currency_field='currency_id_dif', string='SubTotal $', store=True,
                                         compute="_price_subtotal_usd", digits='Dual_Currency')
    amount_residual_usd = fields.Monetary(string='Residual Amount USD', computed='_compute_amount_residual_usd', store=True,
                                       help="The residual amount on a journal item expressed in the company currency.")
    balance_usd = fields.Monetary(string='Balance Ref.',
                                  currency_field='currency_id_dif', store=True, readonly=False,
                                  compute='_compute_balance_usd',
                                  default=lambda self: self._compute_balance_usd(),
                                  help="Technical field holding the debit_usd - credit_usd in order to open meaningful graph views from reports")

    @api.depends('currency_id', 'company_id', 'move_id.date','move_id.tax_today')
    def _compute_currency_rate(self):

        @lru_cache()
        def get_rate(from_currency, to_currency, company, date):
            rate = self.env['res.currency']._get_conversion_rate(
                from_currency=from_currency,
                to_currency=to_currency,
                company=company,
                date=date,
            )
            #print('pasando por get_rate', rate)
            return rate

        for line in self:
            #print('pasando por _compute_currency_rate')
            self.env.context = dict(self.env.context, tasa_factura=line.move_id.tax_today, calcular_dual_currency=True)
            # line.currency_rate = get_rate(
            #     from_currency=line.company_currency_id,
            #     to_currency=line.currency_id,
            #     company=line.company_id,
            #     date=line.move_id.invoice_date or line.move_id.date or fields.Date.context_today(line),
            # )
            line.currency_rate = 1 / line.move_id.tax_today if line.move_id.tax_today > 0 else 1
            #print('line.currency_rate', line.currency_rate)
        self.env.context = dict(self.env.context, tasa_factura=None, calcular_dual_currency=False)

    @api.onchange('amount_currency')
    def _onchange_amount_currency(self):
        self._debit_usd()
        self._credit_usd()

    @api.onchange('price_unit_usd')
    def _onchange_price_unit_usd(self):
        for rec in self:
            if rec.move_id.currency_id != rec.company_id.currency_id:
                rec.price_unit = rec.price_unit_usd
            else:
                rec.price_unit = rec.price_unit_usd * rec.tax_today


    @api.onchange('product_id')
    def _onchange_product_id(self):
        #super()._onchange_product_id()
        self._price_unit_usd()

    @api.depends('debit_usd', 'credit_usd')
    def _compute_balance_usd(self):
        for line in self:
            line.balance_usd = line.debit_usd - line.credit_usd


    @api.depends('price_unit', 'product_id')
    def _price_unit_usd(self):
        for rec in self:
            if rec.price_unit > 0:
                if rec.move_id.currency_id == self.env.company.currency_id:
                    rec.price_unit_usd = (rec.price_unit / rec.tax_today) if rec.tax_today > 0 else 0
                else:
                    rec.price_unit_usd = rec.price_unit
            else:
                rec.price_unit_usd = 0

            # if rec.price_unit_usd > 0:
            #     if rec.move_id.currency_id == self.env.company.currency_id:
            #         rec.price_unit = rec.price_unit_usd * rec.tax_today
            #     else:
            #         rec.price_unit = rec.price_unit_usd
            # else:
            #     rec.price_unit = 0

    @api.depends('price_subtotal')
    def _price_subtotal_usd(self):
        for rec in self:
            if rec.price_subtotal > 0:
                if rec.move_id.currency_id == self.env.company.currency_id:
                    rec.price_subtotal_usd = (rec.price_subtotal / rec.tax_today) if rec.tax_today > 0 else 0
                else:
                    rec.price_subtotal_usd = rec.price_subtotal
            else:
                rec.price_subtotal_usd = 0

            # if rec.price_subtotal_usd > 0:
            #     if rec.move_id.currency_id == self.env.company.currency_id:
            #         rec.price_subtotal = rec.price_subtotal_usd * rec.tax_today
            #     else:
            #         rec.price_subtotal = rec.price_subtotal_usd
            # else:
            #     rec.price_subtotal = 0

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if 'tax_today' not in fields:
            return super(AccountMoveLine, self).read_group(domain, fields, groupby, offset=offset, limit=limit,
                                                           orderby=orderby, lazy=lazy)
        res = super(AccountMoveLine, self).read_group(domain, fields, groupby, offset=offset, limit=limit,
                                                      orderby=orderby, lazy=lazy)
        for group in res:
            if group.get('__domain'):
                records = self.search(group['__domain'])
                group['tax_today'] = 0
        return res

    @api.depends('amount_currency', 'tax_today','debit')
    def _debit_usd(self):
        for rec in self:
            if not rec.debit == 0:
                if rec.move_id.currency_id == self.env.company.currency_id:
                    amount_currency = (rec.amount_currency if rec.amount_currency > 0 else (rec.amount_currency * -1))
                    rec.debit_usd = (amount_currency / rec.tax_today) if rec.tax_today > 0 else 0
                    #rec.debit = amount_currency
                else:
                    rec.debit_usd = (rec.amount_currency if rec.amount_currency > 0 else (rec.amount_currency * -1))

                    # if not 'calcular_dual_currency' in self.env.context:
                    #     if not rec.move_id.stock_move_id:
                    #         module_dual_currency = self.env['ir.module.module'].sudo().search(
                    #             [('name', '=', 'account_dual_currency'), ('state', '=', 'installed')])
                    #         if module_dual_currency:
                    #             # rec.debit = ((rec.amount_currency * rec.tax_today) if rec.amount_currency > 0 else (
                    #             #         (rec.amount_currency * -1) * rec.tax_today))
                    #             rec.with_context(check_move_validity=False).debit = (rec.debit_usd * rec.tax_today)

            else:
                rec.debit_usd = 0

    @api.depends('amount_currency', 'tax_today','credit')
    def _credit_usd(self):
        for rec in self:
            # tmp = rec.credit_usd if rec.credit_usd > 0 else 0
            if not rec.credit == 0:
                if rec.move_id.currency_id == self.env.company.currency_id:
                    amount_currency = (rec.amount_currency if rec.amount_currency > 0 else (rec.amount_currency * -1))
                    rec.credit_usd = (amount_currency / rec.tax_today) if rec.tax_today > 0 else 0
                    #rec.credit = amount_currency
                else:
                    rec.credit_usd = (rec.amount_currency if rec.amount_currency > 0 else (rec.amount_currency * -1))
                    model = self.env.context.get('active_model')
                    #print('contexto--->', self._context)
                    #print('contexto', self.env.context)
                    # if not 'calcular_dual_currency' in self.env.context:
                    #     if not rec.move_id.stock_move_id:
                    #         module_dual_currency = self.env['ir.module.module'].sudo().search(
                    #             [('name', '=', 'account_dual_currency'), ('state', '=', 'installed')])
                    #         if module_dual_currency:
                    #             #rec.credit = ((rec.amount_currency * rec.tax_today) if rec.amount_currency > 0 else (
                    #             #        (rec.amount_currency * -1) * rec.tax_today))
                    #             rec.with_context(check_move_validity=False).credit = rec.credit_usd * rec.tax_today

            else:
                rec.credit_usd = 0

    @api.depends('debit','credit','debit_usd', 'credit_usd', 'amount_currency', 'account_id', 'currency_id', 'move_id.state',
                 'company_id',
                 'matched_debit_ids', 'matched_credit_ids')
    def _compute_amount_residual_usd(self):
        """ Computes the residual amount of a move line from a reconcilable account in the company currency and the line's currency.
            This amount will be 0 for fully reconciled lines or lines from a non-reconcilable account, the original line amount
            for unreconciled lines, and something in-between for partially reconciled lines.
        """
        for line in self:
            if line.id and (line.account_id.reconcile or line.account_id.account_type in ('asset_cash', 'liability_credit_card')):
                reconciled_balance = sum(line.matched_credit_ids.mapped('amount_usd')) \
                                     - sum(line.matched_debit_ids.mapped('amount_usd'))

                line.amount_residual_usd = (line.debit_usd - line.credit_usd) - reconciled_balance

                line.reconciled = (line.amount_residual_usd == 0)
            else:
                # Must not have any reconciliation since the line is not eligible for that.
                line.amount_residual_usd = 0.0
                line.reconciled = False

    def reconcile(self):
        ''' Reconcile the current move lines all together.
        :return: A dictionary representing a summary of what has been done during the reconciliation:
                * partials:             A recorset of all account.partial.reconcile created during the reconciliation.
                * exchange_partials:    A recorset of all account.partial.reconcile created during the reconciliation
                                        with the exchange difference journal entries.
                * full_reconcile:       An account.full.reconcile record created when there is nothing left to reconcile
                                        in the involved lines.
                * tax_cash_basis_moves: An account.move recordset representing the tax cash basis journal entries.
        '''
        self = self.with_context(no_exchange_difference=True)
        results = {'exchange_partials': self.env['account.partial.reconcile']}

        if not self:
            return results

        not_paid_invoices = self.move_id.filtered(lambda move:
            move.is_invoice(include_receipts=True)
            and move.payment_state not in ('paid', 'in_payment')
        )

        # ==== Check the lines can be reconciled together ====
        company = None
        account = None
        for line in self:
            #if line.reconciled:
            #    raise UserError(_("You are trying to reconcile some entries that are already reconciled."))
            if not line.account_id.reconcile and line.account_id.account_type not in ('asset_cash', 'liability_credit_card'):
                raise UserError(_("Account %s does not allow reconciliation. First change the configuration of this account to allow it.")
                                % line.account_id.display_name)
            if line.move_id.state != 'posted':
                raise UserError(_('You can only reconcile posted entries.'))
            if company is None:
                company = line.company_id
            elif line.company_id != company:
                raise UserError(_("Entries doesn't belong to the same company: %s != %s")
                                % (company.display_name, line.company_id.display_name))
            if account is None:
                account = line.account_id
            elif line.account_id != account:
                raise UserError(_("Entries are not from the same account: %s != %s")
                                % (account.display_name, line.account_id.display_name))

        sorted_lines = self.sorted(key=lambda line: (line.date_maturity or line.date, line.currency_id, line.amount_currency))

        # ==== Collect all involved lines through the existing reconciliation ====

        involved_lines = sorted_lines._all_reconciled_lines()
        involved_partials = involved_lines.matched_credit_ids | involved_lines.matched_debit_ids

        # ==== Create partials ====

        partial_no_exch_diff = bool(self.env['ir.config_parameter'].sudo().get_param('account.disable_partial_exchange_diff'))
        sorted_lines_ctx = sorted_lines.with_context(no_exchange_difference=self._context.get('no_exchange_difference') or partial_no_exch_diff)
        partials = sorted_lines_ctx._create_reconciliation_partials()
        results['partials'] = partials
        involved_partials += partials
        exchange_move_lines = partials.exchange_move_id.line_ids.filtered(lambda line: line.account_id == account)
        involved_lines += exchange_move_lines
        exchange_diff_partials = exchange_move_lines.matched_debit_ids + exchange_move_lines.matched_credit_ids
        involved_partials += exchange_diff_partials
        results['exchange_partials'] += exchange_diff_partials

        # ==== Create entries for cash basis taxes ====

        is_cash_basis_needed = account.company_id.tax_exigibility and account.account_type in ('asset_receivable', 'liability_payable')
        if is_cash_basis_needed and not self._context.get('move_reverse_cancel'):
            tax_cash_basis_moves = partials._create_tax_cash_basis_moves()
            results['tax_cash_basis_moves'] = tax_cash_basis_moves

        # ==== Check if a full reconcile is needed ====

        def is_line_reconciled(line, has_multiple_currencies):
            # Check if the journal item passed as parameter is now fully reconciled.
            return line.reconciled \
                   or (line.company_currency_id.is_zero(line.amount_residual)
                       if has_multiple_currencies
                       else line.currency_id.is_zero(line.amount_residual_currency)
                   )

        has_multiple_currencies = len(involved_lines.currency_id) > 1
        if all(is_line_reconciled(line, has_multiple_currencies) for line in involved_lines):
            # ==== Create the exchange difference move ====
            # This part could be bypassed using the 'no_exchange_difference' key inside the context. This is useful
            # when importing a full accounting including the reconciliation like Winbooks.

            exchange_move = self.env['account.move']
            caba_lines_to_reconcile = None
            if not self._context.get('no_exchange_difference'):
                # In normal cases, the exchange differences are already generated by the partial at this point meaning
                # there is no journal item left with a zero amount residual in one currency but not in the other.
                # However, after a migration coming from an older version with an older partial reconciliation or due to
                # some rounding issues (when dealing with different decimal places for example), we could need an extra
                # exchange difference journal entry to handle them.
                exchange_lines_to_fix = self.env['account.move.line']
                amounts_list = []
                exchange_max_date = date.min
                for line in involved_lines:
                    if not line.company_currency_id.is_zero(line.amount_residual):
                        exchange_lines_to_fix += line
                        amounts_list.append({'amount_residual': line.amount_residual})
                    elif not line.currency_id.is_zero(line.amount_residual_currency):
                        exchange_lines_to_fix += line
                        amounts_list.append({'amount_residual_currency': line.amount_residual_currency})
                    exchange_max_date = max(exchange_max_date, line.date)
                exchange_diff_vals = exchange_lines_to_fix._prepare_exchange_difference_move_vals(
                    amounts_list,
                    company=involved_lines[0].company_id,
                    exchange_date=exchange_max_date,
                )

                # Exchange difference for cash basis entries.
                if is_cash_basis_needed:
                    caba_lines_to_reconcile = involved_lines._add_exchange_difference_cash_basis_vals(exchange_diff_vals)

                # Create the exchange difference.
                if exchange_diff_vals['move_vals']['line_ids']:
                    exchange_move = involved_lines._create_exchange_difference_move(exchange_diff_vals)
                    if exchange_move:
                        exchange_move_lines = exchange_move.line_ids.filtered(lambda line: line.account_id == account)

                        # Track newly created lines.
                        involved_lines += exchange_move_lines

                        # Track newly created partials.
                        exchange_diff_partials = exchange_move_lines.matched_debit_ids \
                                                 + exchange_move_lines.matched_credit_ids
                        involved_partials += exchange_diff_partials
                        results['exchange_partials'] += exchange_diff_partials

            # ==== Create the full reconcile ====
            results['full_reconcile'] = self.env['account.full.reconcile'] \
                .with_context(
                    skip_invoice_sync=True,
                    skip_invoice_line_sync=True,
                    skip_account_move_synchronization=True,
                    check_move_validity=False,
                ) \
                .create({
                    'exchange_move_id': exchange_move and exchange_move.id,
                    'partial_reconcile_ids': [Command.set(involved_partials.ids)],
                    'reconciled_line_ids': [Command.set(involved_lines.ids)],
                })

            # === Cash basis rounding autoreconciliation ===
            # In case a cash basis rounding difference line got created for the transition account, we reconcile it with the corresponding lines
            # on the cash basis moves (so that it reaches full reconciliation and creates an exchange difference entry for this account as well)

            if caba_lines_to_reconcile:
                for (dummy, account, repartition_line), amls_to_reconcile in caba_lines_to_reconcile.items():
                    if not account.reconcile:
                        continue

                    exchange_line = exchange_move.line_ids.filtered(
                        lambda l: l.account_id == account and l.tax_repartition_line_id == repartition_line
                    )

                    (exchange_line + amls_to_reconcile).filtered(lambda l: not l.reconciled).reconcile()

        not_paid_invoices.filtered(lambda move:
            move.payment_state in ('paid', 'in_payment')
        )._invoice_paid_hook()
        for parcial in results['partials']:
            amount_usd = min(abs(parcial.debit_move_id.amount_residual_usd),
                             abs(parcial.credit_move_id.amount_residual_usd))
            parcial.write({'amount_usd': abs(amount_usd)})
            self.env.cr.commit()
        return results

    @api.model
    def _prepare_reconciliation_single_partial(self, debit_vals, credit_vals):
        """ Prepare the values to create an account.partial.reconcile later when reconciling the dictionaries passed
        as parameters, each one representing an account.move.line.
        :param debit_vals:  The values of account.move.line to consider for a debit line.
        :param credit_vals: The values of account.move.line to consider for a credit line.
        :return:            A dictionary:
            * debit_vals:   None if the line has nothing left to reconcile.
            * credit_vals:  None if the line has nothing left to reconcile.
            * partial_vals: The newly computed values for the partial.
        """

        def get_odoo_rate(vals):
            # if vals.get('record') and vals['record'].move_id.is_invoice(include_receipts=True):
            #     exchange_rate_date = vals['record'].move_id.invoice_date
            # else:
            #     exchange_rate_date = vals['date']
            # return recon_currency._get_conversion_rate(company_currency, recon_currency, vals['company'],
            #                                            exchange_rate_date)
            if vals.get('record') and vals['record'].move_id.is_invoice(include_receipts=True):
                exchange_rate_date = vals['record'].move_id.invoice_date
            else:
                exchange_rate_date = vals['date']
            to_re = recon_currency._get_conversion_rate(company_currency, recon_currency, vals['company'],
                                                        exchange_rate_date)
            return  1 / vals['record'].move_id.tax_today if vals['record'].move_id.tax_today > 0 else 1
            if debit_vals['record'].move_id.is_invoice(include_receipts=True):
                return (1 / credit_vals['record'].move_id.tax_today if credit_vals['record'].move_id.tax_today > 0 else 1)
            elif credit_vals['record'].move_id.is_invoice(include_receipts=True):
                return 1 / debit_vals['record'].move_id.tax_today if debit_vals['record'].move_id.tax_today > 0 else 1
            else:
                return to_re


        def get_accounting_rate(vals):
            if company_currency.is_zero(vals['balance']) or vals['currency'].is_zero(vals['amount_currency']):
                return None
            else:
                return abs(vals['amount_currency']) / abs(vals['balance'])

        # ==== Determine the currency in which the reconciliation will be done ====
        # In this part, we retrieve the residual amounts, check if they are zero or not and determine in which
        # currency and at which rate the reconciliation will be done.

        res = {
            'debit_vals': debit_vals,
            'credit_vals': credit_vals,
        }
        remaining_debit_amount_curr = debit_vals['amount_residual_currency']
        remaining_credit_amount_curr = credit_vals['amount_residual_currency']
        remaining_debit_amount = debit_vals['amount_residual']
        remaining_credit_amount = credit_vals['amount_residual']

        company_currency = debit_vals['company'].currency_id
        has_debit_zero_residual = company_currency.is_zero(remaining_debit_amount)
        has_credit_zero_residual = company_currency.is_zero(remaining_credit_amount)
        has_debit_zero_residual_currency = debit_vals['currency'].is_zero(remaining_debit_amount_curr)
        has_credit_zero_residual_currency = credit_vals['currency'].is_zero(remaining_credit_amount_curr)
        is_rec_pay_account = debit_vals.get('record') \
                             and debit_vals['record'].account_type in ('asset_receivable', 'liability_payable')

        if debit_vals['currency'] == credit_vals['currency'] == company_currency \
                and not has_debit_zero_residual \
                and not has_credit_zero_residual:
            # Everything is expressed in company's currency and there is something left to reconcile.
            recon_currency = company_currency
            debit_rate = credit_rate = 1.0
            recon_debit_amount = remaining_debit_amount
            recon_credit_amount = -remaining_credit_amount
        elif debit_vals['currency'] == company_currency \
                and is_rec_pay_account \
                and not has_debit_zero_residual \
                and credit_vals['currency'] != company_currency \
                and not has_credit_zero_residual_currency:
            # The credit line is using a foreign currency but not the opposite line.
            # In that case, convert the amount in company currency to the foreign currency one.
            recon_currency = credit_vals['currency']
            debit_rate = get_odoo_rate(debit_vals)
            credit_rate = get_accounting_rate(credit_vals)
            recon_debit_amount = recon_currency.round(remaining_debit_amount * debit_rate)
            recon_credit_amount = -remaining_credit_amount_curr
        elif debit_vals['currency'] != company_currency \
                and is_rec_pay_account \
                and not has_debit_zero_residual_currency \
                and credit_vals['currency'] == company_currency \
                and not has_credit_zero_residual:
            # The debit line is using a foreign currency but not the opposite line.
            # In that case, convert the amount in company currency to the foreign currency one.
            recon_currency = debit_vals['currency']
            debit_rate = get_accounting_rate(debit_vals)
            credit_rate = get_odoo_rate(credit_vals)
            recon_debit_amount = remaining_debit_amount_curr
            recon_credit_amount = recon_currency.round(-remaining_credit_amount * credit_rate)
        elif debit_vals['currency'] == credit_vals['currency'] \
                and debit_vals['currency'] != company_currency \
                and not has_debit_zero_residual_currency \
                and not has_credit_zero_residual_currency:
            # Both lines are sharing the same foreign currency.
            recon_currency = debit_vals['currency']
            debit_rate = get_accounting_rate(debit_vals)
            credit_rate = get_accounting_rate(credit_vals)
            recon_debit_amount = remaining_debit_amount_curr
            recon_credit_amount = -remaining_credit_amount_curr
        elif debit_vals['currency'] == credit_vals['currency'] \
                and debit_vals['currency'] != company_currency \
                and (has_debit_zero_residual_currency or has_credit_zero_residual_currency):
            # Special case for exchange difference lines. In that case, both lines are sharing the same foreign
            # currency but at least one has no amount in foreign currency.
            # In that case, we don't want a rate for the opposite line because the exchange difference is supposed
            # to reduce only the amount in company currency but not the foreign one.
            recon_currency = company_currency
            debit_rate = None
            credit_rate = None
            recon_debit_amount = remaining_debit_amount
            recon_credit_amount = -remaining_credit_amount
        else:
            # Multiple involved foreign currencies. The reconciliation is done using the currency of the company.
            recon_currency = company_currency
            debit_rate = get_accounting_rate(debit_vals)
            credit_rate = get_accounting_rate(credit_vals)
            recon_debit_amount = remaining_debit_amount
            recon_credit_amount = -remaining_credit_amount

        # Check if there is something left to reconcile. Move to the next loop iteration if not.
        skip_reconciliation = False
        if recon_currency.is_zero(recon_debit_amount):
            res['debit_vals'] = None
            skip_reconciliation = True
        if recon_currency.is_zero(recon_credit_amount):
            res['credit_vals'] = None
            skip_reconciliation = True
        if skip_reconciliation:
            return res

        # ==== Match both lines together and compute amounts to reconcile ====

        # Determine which line is fully matched by the other.
        compare_amounts = recon_currency.compare_amounts(recon_debit_amount, recon_credit_amount)
        min_recon_amount = min(recon_debit_amount, recon_credit_amount)
        debit_fully_matched = compare_amounts <= 0
        credit_fully_matched = compare_amounts >= 0

        # ==== Computation of partial amounts ====
        if recon_currency == company_currency:
            # Compute the partial amount expressed in company currency.
            partial_amount = min_recon_amount

            # Compute the partial amount expressed in foreign currency.
            if debit_rate:
                partial_debit_amount_currency = debit_vals['currency'].round(debit_rate * min_recon_amount)
                partial_debit_amount_currency = min(partial_debit_amount_currency, remaining_debit_amount_curr)
            else:
                partial_debit_amount_currency = 0.0
            if credit_rate:
                partial_credit_amount_currency = credit_vals['currency'].round(credit_rate * min_recon_amount)
                partial_credit_amount_currency = min(partial_credit_amount_currency, -remaining_credit_amount_curr)
            else:
                partial_credit_amount_currency = 0.0

        else:
            # recon_currency != company_currency
            # Compute the partial amount expressed in company currency.
            if debit_rate:
                partial_debit_amount = company_currency.round(min_recon_amount / debit_rate)
                partial_debit_amount = min(partial_debit_amount, remaining_debit_amount)
            else:
                partial_debit_amount = 0.0
            if credit_rate:
                partial_credit_amount = company_currency.round(min_recon_amount / credit_rate)
                partial_credit_amount = min(partial_credit_amount, -remaining_credit_amount)
            else:
                partial_credit_amount = 0.0
            partial_amount = min(partial_debit_amount, partial_credit_amount)

            # Compute the partial amount expressed in foreign currency.
            # Take care to handle the case when a line expressed in company currency is mimicking the foreign
            # currency of the opposite line.
            if debit_vals['currency'] == company_currency:
                partial_debit_amount_currency = partial_amount
            else:
                partial_debit_amount_currency = min_recon_amount
            if credit_vals['currency'] == company_currency:
                partial_credit_amount_currency = partial_amount
            else:
                partial_credit_amount_currency = min_recon_amount

        # Computation of the partial exchange difference. You can skip this part using the
        # `no_exchange_difference` context key (when reconciling an exchange difference for example).
        if not self._context.get('no_exchange_difference'):
            exchange_lines_to_fix = self.env['account.move.line']
            amounts_list = []
            if recon_currency == company_currency:
                if debit_fully_matched:
                    debit_exchange_amount = remaining_debit_amount_curr - partial_debit_amount_currency
                    if not debit_vals['currency'].is_zero(debit_exchange_amount):
                        if debit_vals.get('record'):
                            exchange_lines_to_fix += debit_vals['record']
                        amounts_list.append({'amount_residual_currency': debit_exchange_amount})
                        remaining_debit_amount_curr -= debit_exchange_amount
                if credit_fully_matched:
                    credit_exchange_amount = remaining_credit_amount_curr + partial_credit_amount_currency
                    if not credit_vals['currency'].is_zero(credit_exchange_amount):
                        if credit_vals.get('record'):
                            exchange_lines_to_fix += credit_vals['record']
                        amounts_list.append({'amount_residual_currency': credit_exchange_amount})
                        remaining_credit_amount_curr += credit_exchange_amount

            else:
                if debit_fully_matched:
                    # Create an exchange difference on the remaining amount expressed in company's currency.
                    debit_exchange_amount = remaining_debit_amount - partial_amount
                    if not company_currency.is_zero(debit_exchange_amount):
                        if debit_vals.get('record'):
                            exchange_lines_to_fix += debit_vals['record']
                        amounts_list.append({'amount_residual': debit_exchange_amount})
                        remaining_debit_amount -= debit_exchange_amount
                        if debit_vals['currency'] == company_currency:
                            remaining_debit_amount_curr -= debit_exchange_amount
                else:
                    # Create an exchange difference ensuring the rate between the residual amounts expressed in
                    # both foreign and company's currency is still consistent regarding the rate between
                    # 'amount_currency' & 'balance'.
                    debit_exchange_amount = partial_debit_amount - partial_amount
                    if company_currency.compare_amounts(debit_exchange_amount, 0.0) > 0:
                        if debit_vals.get('record'):
                            exchange_lines_to_fix += debit_vals['record']
                        amounts_list.append({'amount_residual': debit_exchange_amount})
                        remaining_debit_amount -= debit_exchange_amount
                        if debit_vals['currency'] == company_currency:
                            remaining_debit_amount_curr -= debit_exchange_amount

                if credit_fully_matched:
                    # Create an exchange difference on the remaining amount expressed in company's currency.
                    credit_exchange_amount = remaining_credit_amount + partial_amount
                    if not company_currency.is_zero(credit_exchange_amount):
                        if credit_vals.get('record'):
                            exchange_lines_to_fix += credit_vals['record']
                        amounts_list.append({'amount_residual': credit_exchange_amount})
                        remaining_credit_amount += credit_exchange_amount
                        if credit_vals['currency'] == company_currency:
                            remaining_credit_amount_curr -= credit_exchange_amount
                else:
                    # Create an exchange difference ensuring the rate between the residual amounts expressed in
                    # both foreign and company's currency is still consistent regarding the rate between
                    # 'amount_currency' & 'balance'.
                    credit_exchange_amount = partial_amount - partial_credit_amount
                    if company_currency.compare_amounts(credit_exchange_amount, 0.0) < 0:
                        if credit_vals.get('record'):
                            exchange_lines_to_fix += credit_vals['record']
                        amounts_list.append({'amount_residual': credit_exchange_amount})
                        remaining_credit_amount -= credit_exchange_amount
                        if credit_vals['currency'] == company_currency:
                            remaining_credit_amount_curr -= credit_exchange_amount

            if exchange_lines_to_fix:
                res['exchange_vals'] = exchange_lines_to_fix._prepare_exchange_difference_move_vals(
                    amounts_list,
                    exchange_date=max(debit_vals['date'], credit_vals['date']),
                )

        # ==== Create partials ====

        remaining_debit_amount -= partial_amount
        remaining_credit_amount += partial_amount
        remaining_debit_amount_curr -= partial_debit_amount_currency
        remaining_credit_amount_curr += partial_credit_amount_currency

        res['partial_vals'] = {
            'amount': partial_amount,
            'debit_amount_currency': partial_debit_amount_currency,
            'credit_amount_currency': partial_credit_amount_currency,
            'debit_move_id': debit_vals.get('record') and debit_vals['record'].id,
            'credit_move_id': credit_vals.get('record') and credit_vals['record'].id,
        }

        debit_vals['amount_residual'] = remaining_debit_amount
        debit_vals['amount_residual_currency'] = remaining_debit_amount_curr
        credit_vals['amount_residual'] = remaining_credit_amount
        credit_vals['amount_residual_currency'] = remaining_credit_amount_curr

        if debit_fully_matched:
            res['debit_vals'] = None
        if credit_fully_matched:
            res['credit_vals'] = None
        return res

    # def _create_reconciliation_partials(self):
    #     '''create the partial reconciliation between all the records in self
    #      :return: A recordset of account.partial.reconcile.
    #     '''
    #     partials_vals_list, exchange_data = self._prepare_reconciliation_partials([
    #         {
    #             'record': line,
    #             'balance': line.balance,
    #             'amount_currency': line.amount_currency,
    #             'amount_residual': line.amount_residual,
    #             'amount_residual_currency': line.amount_residual_currency,
    #             'company': line.company_id,
    #             'currency': line.currency_id,
    #             'date': line.date,
    #         }
    #         for line in self
    #     ])
    #     partials = self.env['account.partial.reconcile'].create(partials_vals_list)
    #
    #     # # ==== Create exchange difference moves ====
    #     # for index, exchange_vals in exchange_data.items():
    #     #     partials[index].exchange_move_id = self._create_exchange_difference_move(exchange_vals)
    #
    #     return partials

    #@api.model
    # def _prepare_reconciliation_partials(self, vals_list):
    #     ''' Prepare the partials on the current journal items to perform the reconciliation.
    #     Note: The order of records in self is important because the journal items will be reconciled using this order.
    #     :return: a tuple of 1) list of vals for partial reconciliation creation, 2) the list of vals for the exchange difference entries to be created
    #     '''
    #     exchange_data = {}
    #
    #     def fix_remaining_cent(currency, abs_residual, partial_amount):
    #         if abs_residual - currency.rounding <= partial_amount <= abs_residual + currency.rounding:
    #             return abs_residual
    #         else:
    #             return partial_amount
    #
    #     debit_lines = iter(self.filtered(lambda line: line.balance > 0.0 or line.amount_currency > 0.0 and not line.reconciled))
    #     credit_lines = iter(self.filtered(lambda line: line.balance < 0.0 or line.amount_currency < 0.0 and not line.reconciled))
    #     void_lines = iter(self.filtered(lambda line: not line.balance and not line.amount_currency and not line.reconciled))
    #     debit_line = None
    #     credit_line = None
    #
    #     debit_amount_residual = 0.0
    #     debit_amount_residual_currency = 0.0
    #     credit_amount_residual = 0.0
    #     credit_amount_residual_currency = 0.0
    #     debit_line_currency = None
    #     credit_line_currency = None
    #
    #     partials_vals_list = []
    #
    #     while True:
    #
    #         # Move to the next available debit line.
    #         if not debit_line:
    #             debit_line = next(debit_lines, None) or next(void_lines, None)
    #             if not debit_line:
    #                 break
    #             debit_amount_residual = debit_line.amount_residual
    #
    #             if debit_line.currency_id:
    #                 debit_amount_residual_currency = debit_line.amount_residual_currency
    #                 debit_line_currency = debit_line.currency_id
    #             else:
    #                 debit_amount_residual_currency = debit_amount_residual
    #                 debit_line_currency = debit_line.company_currency_id
    #
    #         # Move to the next available credit line.
    #         if not credit_line:
    #             credit_line = next(void_lines, None) or next(credit_lines, None)
    #             if not credit_line:
    #                 break
    #             credit_amount_residual = credit_line.amount_residual
    #
    #             if credit_line.currency_id:
    #                 credit_amount_residual_currency = credit_line.amount_residual_currency
    #                 credit_line_currency = credit_line.currency_id
    #             else:
    #                 credit_amount_residual_currency = credit_amount_residual
    #                 credit_line_currency = credit_line.company_currency_id
    #
    #         min_amount_residual = min(debit_amount_residual, -credit_amount_residual)
    #
    #         if debit_line_currency == credit_line_currency:
    #             # Reconcile on the same currency.
    #
    #             min_amount_residual_currency = min(debit_amount_residual_currency, -credit_amount_residual_currency)
    #             min_debit_amount_residual_currency = min_amount_residual_currency
    #             min_credit_amount_residual_currency = min_amount_residual_currency
    #
    #         else:
    #             # Reconcile on the company's currency.
    #             if credit_line_currency == credit_line.company_currency_id and debit_line_currency == debit_line.company_id.currency_id_dif:
    #                 self.env.context = dict(self.env.context, tasa_factura=debit_line.tax_today)
    #                 min_debit_amount_residual_currency = credit_line.company_currency_id._convert(
    #                     min_amount_residual,
    #                     debit_line.currency_id,
    #                     credit_line.company_id,
    #                     credit_line.date,
    #                 )
    #                 min_debit_amount_residual_currency = fix_remaining_cent(
    #                     debit_line.currency_id,
    #                     debit_amount_residual_currency,
    #                     min_debit_amount_residual_currency,
    #                 )
    #
    #                 self.env.context = dict(self.env.context, tasa_factura=None)
    #                 min_credit_amount_residual_currency = debit_line.company_currency_id._convert(
    #                     min_amount_residual,
    #                     credit_line.currency_id,
    #                     debit_line.company_id,
    #                     debit_line.date,
    #                 )
    #                 min_credit_amount_residual_currency = fix_remaining_cent(
    #                     credit_line.currency_id,
    #                     -credit_amount_residual_currency,
    #                     min_credit_amount_residual_currency,
    #                 )
    #
    #             if debit_line_currency == debit_line.company_currency_id and credit_line_currency == credit_line.company_id.currency_id_dif:
    #                 min_debit_amount_residual_currency = credit_line.company_currency_id._convert(
    #                     min_amount_residual,
    #                     debit_line.currency_id,
    #                     credit_line.company_id,
    #                     credit_line.date,
    #                 )
    #                 min_debit_amount_residual_currency = fix_remaining_cent(
    #                     debit_line.currency_id,
    #                     debit_amount_residual_currency,
    #                     min_debit_amount_residual_currency,
    #                 )
    #                 self.env.context = dict(self.env.context, tasa_factura=credit_line.tax_today)
    #                 min_credit_amount_residual_currency = debit_line.company_currency_id._convert(
    #                     min_amount_residual,
    #                     credit_line.currency_id,
    #                     debit_line.company_id,
    #                     debit_line.date,
    #                 )
    #                 min_credit_amount_residual_currency = fix_remaining_cent(
    #                     credit_line.currency_id,
    #                     -credit_amount_residual_currency,
    #                     min_credit_amount_residual_currency,
    #                 )
    #                 self.env.context = dict(self.env.context, tasa_factura=None)
    #             else:
    #                 min_debit_amount_residual_currency = credit_line.company_currency_id._convert(
    #                     min_amount_residual,
    #                     debit_line.currency_id,
    #                     credit_line.company_id,
    #                     credit_line.date,
    #                 )
    #                 min_debit_amount_residual_currency = fix_remaining_cent(
    #                     debit_line.currency_id,
    #                     debit_amount_residual_currency,
    #                     min_debit_amount_residual_currency,
    #                 )
    #                 min_credit_amount_residual_currency = debit_line.company_currency_id._convert(
    #                     min_amount_residual,
    #                     credit_line.currency_id,
    #                     debit_line.company_id,
    #                     debit_line.date,
    #                 )
    #                 min_credit_amount_residual_currency = fix_remaining_cent(
    #                     credit_line.currency_id,
    #                     -credit_amount_residual_currency,
    #                     min_credit_amount_residual_currency,
    #                 )
    #
    #         debit_amount_residual -= min_amount_residual
    #         debit_amount_residual_currency -= min_debit_amount_residual_currency
    #         credit_amount_residual += min_amount_residual
    #         credit_amount_residual_currency += min_credit_amount_residual_currency
    #
    #         partials_vals_list.append({
    #             'amount': min_amount_residual,
    #             'debit_amount_currency': min_debit_amount_residual_currency,
    #             'credit_amount_currency': min_credit_amount_residual_currency,
    #             'debit_move_id': debit_line.id,
    #             'credit_move_id': credit_line.id,
    #         })
    #
    #         has_debit_residual_left = not debit_line.company_currency_id.is_zero(debit_amount_residual) and debit_amount_residual > 0.0
    #         has_credit_residual_left = not credit_line.company_currency_id.is_zero(credit_amount_residual) and credit_amount_residual < 0.0
    #         has_debit_residual_curr_left = not debit_line_currency.is_zero(debit_amount_residual_currency) and debit_amount_residual_currency > 0.0
    #         has_credit_residual_curr_left = not credit_line_currency.is_zero(credit_amount_residual_currency) and credit_amount_residual_currency < 0.0
    #
    #         if debit_line_currency == credit_line_currency:
    #             # The debit line is now fully reconciled because:
    #             # - either amount_residual & amount_residual_currency are at 0.
    #             # - either the credit_line is not an exchange difference one.
    #             if not has_debit_residual_curr_left and (has_credit_residual_curr_left or not has_debit_residual_left):
    #                 debit_line = None
    #
    #             # The credit line is now fully reconciled because:
    #             # - either amount_residual & amount_residual_currency are at 0.
    #             # - either the debit is not an exchange difference one.
    #             if not has_credit_residual_curr_left and (has_debit_residual_curr_left or not has_credit_residual_left):
    #                 credit_line = None
    #
    #         else:
    #             # The debit line is now fully reconciled since amount_residual is 0.
    #             if not has_debit_residual_left:
    #                 debit_line = None
    #
    #             # The credit line is now fully reconciled since amount_residual is 0.
    #             if not has_credit_residual_left:
    #                 credit_line = None
    #
    #     return partials_vals_list, exchange_data
    #
    # @api.model
    # def _prepare_reconciliation_single_partial(self, debit_vals, credit_vals):
    #     """ Prepare the values to create an account.partial.reconcile later when reconciling the dictionaries passed
    #     as parameters, each one representing an account.move.line.
    #     :param debit_vals:  The values of account.move.line to consider for a debit line.
    #     :param credit_vals: The values of account.move.line to consider for a credit line.
    #     :return:            A dictionary:
    #         * debit_vals:   None if the line has nothing left to reconcile.
    #         * credit_vals:  None if the line has nothing left to reconcile.
    #         * partial_vals: The newly computed values for the partial.
    #     """
    #     #agregar variable al contexto para que no se cree el exchange
    #
    #     def get_odoo_rate(vals):
    #         if vals.get('record') and vals['record'].move_id.is_invoice(include_receipts=True):
    #             exchange_rate_date = vals['record'].move_id.invoice_date
    #         else:
    #             exchange_rate_date = vals['date']
    #         to_re =  recon_currency._get_conversion_rate(company_currency, recon_currency, vals['company'],
    #                                                    exchange_rate_date)
    #
    #         if debit_vals['record'].move_id.is_invoice(include_receipts=True):
    #             return (1 / credit_vals['record'].move_id.tax_today if credit_vals['record'].move_id.tax_today > 0 else 1)
    #         else:
    #             return 1 / debit_vals['record'].move_id.tax_today if debit_vals['record'].move_id.tax_today > 0 else 1
    #
    #
    #     def get_accounting_rate(vals):
    #         if company_currency.is_zero(vals['balance']) or vals['currency'].is_zero(vals['amount_currency']):
    #             return None
    #         else:
    #             #print('la get_accounting_rate es ', abs(vals['amount_currency']) / abs(vals['balance']))
    #             return abs(vals['amount_currency']) / abs(vals['balance'])
    #
    #     # ==== Determine the currency in which the reconciliation will be done ====
    #     # In this part, we retrieve the residual amounts, check if they are zero or not and determine in which
    #     # currency and at which rate the reconciliation will be done.
    #
    #     res = {
    #         'debit_vals': debit_vals,
    #         'credit_vals': credit_vals,
    #     }
    #     remaining_debit_amount_curr = debit_vals['amount_residual_currency']
    #     remaining_credit_amount_curr = credit_vals['amount_residual_currency']
    #     remaining_debit_amount = debit_vals['amount_residual']
    #     remaining_credit_amount = credit_vals['amount_residual']
    #
    #     company_currency = debit_vals['company'].currency_id
    #     has_debit_zero_residual = company_currency.is_zero(remaining_debit_amount)
    #     has_credit_zero_residual = company_currency.is_zero(remaining_credit_amount)
    #     has_debit_zero_residual_currency = debit_vals['currency'].is_zero(remaining_debit_amount_curr)
    #     has_credit_zero_residual_currency = credit_vals['currency'].is_zero(remaining_credit_amount_curr)
    #     is_rec_pay_account = debit_vals.get('record') \
    #                          and debit_vals['record'].account_type in ('asset_receivable', 'liability_payable')
    #
    #     if debit_vals['currency'] == credit_vals['currency'] == company_currency \
    #             and not has_debit_zero_residual \
    #             and not has_credit_zero_residual:
    #         # Everything is expressed in company's currency and there is something left to reconcile.
    #         recon_currency = company_currency
    #         debit_rate = credit_rate = 1.0
    #         recon_debit_amount = remaining_debit_amount
    #         recon_credit_amount = -remaining_credit_amount
    #     elif debit_vals['currency'] == company_currency \
    #             and is_rec_pay_account \
    #             and not has_debit_zero_residual \
    #             and credit_vals['currency'] != company_currency \
    #             and not has_credit_zero_residual_currency:
    #         # The credit line is using a foreign currency but not the opposite line.
    #         # In that case, convert the amount in company currency to the foreign currency one.
    #         recon_currency = credit_vals['currency']
    #         debit_rate = get_odoo_rate(debit_vals)
    #         credit_rate = get_accounting_rate(credit_vals)
    #         recon_debit_amount = recon_currency.round(remaining_debit_amount * debit_rate)
    #         recon_credit_amount = -remaining_credit_amount_curr
    #     elif debit_vals['currency'] != company_currency \
    #             and is_rec_pay_account \
    #             and not has_debit_zero_residual_currency \
    #             and credit_vals['currency'] == company_currency \
    #             and not has_credit_zero_residual:
    #         # The debit line is using a foreign currency but not the opposite line.
    #         # In that case, convert the amount in company currency to the foreign currency one.
    #         recon_currency = debit_vals['currency']
    #         debit_rate = get_accounting_rate(debit_vals)
    #         credit_rate = get_odoo_rate(credit_vals)
    #         recon_debit_amount = remaining_debit_amount_curr
    #         recon_credit_amount = recon_currency.round(-remaining_credit_amount * credit_rate)
    #     elif debit_vals['currency'] == credit_vals['currency'] \
    #             and debit_vals['currency'] != company_currency \
    #             and not has_debit_zero_residual_currency \
    #             and not has_credit_zero_residual_currency:
    #         # Both lines are sharing the same foreign currency.
    #         recon_currency = debit_vals['currency']
    #         debit_rate = get_accounting_rate(debit_vals)
    #         credit_rate = get_accounting_rate(credit_vals)
    #         recon_debit_amount = remaining_debit_amount_curr
    #         recon_credit_amount = -remaining_credit_amount_curr
    #     elif debit_vals['currency'] == credit_vals['currency'] \
    #             and debit_vals['currency'] != company_currency \
    #             and (has_debit_zero_residual_currency or has_credit_zero_residual_currency):
    #         # Special case for exchange difference lines. In that case, both lines are sharing the same foreign
    #         # currency but at least one has no amount in foreign currency.
    #         # In that case, we don't want a rate for the opposite line because the exchange difference is supposed
    #         # to reduce only the amount in company currency but not the foreign one.
    #         recon_currency = company_currency
    #         debit_rate = None
    #         credit_rate = None
    #         recon_debit_amount = remaining_debit_amount
    #         recon_credit_amount = -remaining_credit_amount
    #     else:
    #         # Multiple involved foreign currencies. The reconciliation is done using the currency of the company.
    #         recon_currency = company_currency
    #         debit_rate = get_accounting_rate(debit_vals)
    #         credit_rate = get_accounting_rate(credit_vals)
    #         recon_debit_amount = remaining_debit_amount
    #         recon_credit_amount = -remaining_credit_amount
    #
    #     # Check if there is something left to reconcile. Move to the next loop iteration if not.
    #     skip_reconciliation = False
    #     if recon_currency.is_zero(recon_debit_amount):
    #         res['debit_vals'] = None
    #         skip_reconciliation = True
    #     if recon_currency.is_zero(recon_credit_amount):
    #         res['credit_vals'] = None
    #         skip_reconciliation = True
    #     if skip_reconciliation:
    #         return res
    #
    #     # ==== Match both lines together and compute amounts to reconcile ====
    #
    #     # Determine which line is fully matched by the other.
    #     compare_amounts = recon_currency.compare_amounts(recon_debit_amount, recon_credit_amount)
    #     min_recon_amount = min(recon_debit_amount, recon_credit_amount)
    #     debit_fully_matched = compare_amounts <= 0
    #     credit_fully_matched = compare_amounts >= 0
    #
    #     # ==== Computation of partial amounts ====
    #     if recon_currency == company_currency:
    #         # Compute the partial amount expressed in company currency.
    #         partial_amount = min_recon_amount
    #
    #         # Compute the partial amount expressed in foreign currency.
    #         if debit_rate:
    #             partial_debit_amount_currency = debit_vals['currency'].round(debit_rate * min_recon_amount)
    #             partial_debit_amount_currency = min(partial_debit_amount_currency, remaining_debit_amount_curr)
    #         else:
    #             partial_debit_amount_currency = 0.0
    #         if credit_rate:
    #             partial_credit_amount_currency = credit_vals['currency'].round(credit_rate * min_recon_amount)
    #             partial_credit_amount_currency = min(partial_credit_amount_currency, -remaining_credit_amount_curr)
    #         else:
    #             partial_credit_amount_currency = 0.0
    #
    #     else:
    #         # recon_currency != company_currency
    #         # Compute the partial amount expressed in company currency.
    #         if debit_rate:
    #             partial_debit_amount = company_currency.round(min_recon_amount / debit_rate)
    #             partial_debit_amount = min(partial_debit_amount, remaining_debit_amount)
    #         else:
    #             partial_debit_amount = 0.0
    #         if credit_rate:
    #             partial_credit_amount = company_currency.round(min_recon_amount / credit_rate)
    #             partial_credit_amount = min(partial_credit_amount, -remaining_credit_amount)
    #         else:
    #             partial_credit_amount = 0.0
    #         partial_amount = min(partial_debit_amount, partial_credit_amount)
    #
    #         # Compute the partial amount expressed in foreign currency.
    #         # Take care to handle the case when a line expressed in company currency is mimicking the foreign
    #         # currency of the opposite line.
    #         if debit_vals['currency'] == company_currency:
    #             partial_debit_amount_currency = partial_amount
    #         else:
    #             partial_debit_amount_currency = min_recon_amount
    #         if credit_vals['currency'] == company_currency:
    #             partial_credit_amount_currency = partial_amount
    #         else:
    #             partial_credit_amount_currency = min_recon_amount
    #
    #     # Computation of the partial exchange difference. You can skip this part using the
    #     # `no_exchange_difference` context key (when reconciling an exchange difference for example).
    #     # if not self._context.get('no_exchange_difference'):
    #     #     exchange_lines_to_fix = self.env['account.move.line']
    #     #     amounts_list = []
    #     #     if recon_currency == company_currency:
    #     #         if debit_fully_matched:
    #     #             debit_exchange_amount = remaining_debit_amount_curr - partial_debit_amount_currency
    #     #             if not debit_vals['currency'].is_zero(debit_exchange_amount):
    #     #                 if debit_vals.get('record'):
    #     #                     exchange_lines_to_fix += debit_vals['record']
    #     #                 amounts_list.append({'amount_residual_currency': debit_exchange_amount})
    #     #                 remaining_debit_amount_curr -= debit_exchange_amount
    #     #         if credit_fully_matched:
    #     #             credit_exchange_amount = remaining_credit_amount_curr + partial_credit_amount_currency
    #     #             if not credit_vals['currency'].is_zero(credit_exchange_amount):
    #     #                 if credit_vals.get('record'):
    #     #                     exchange_lines_to_fix += credit_vals['record']
    #     #                 amounts_list.append({'amount_residual_currency': credit_exchange_amount})
    #     #                 remaining_credit_amount_curr += credit_exchange_amount
    #     #
    #     #     else:
    #     #         if debit_fully_matched:
    #     #             # Create an exchange difference on the remaining amount expressed in company's currency.
    #     #             debit_exchange_amount = remaining_debit_amount - partial_amount
    #     #             if not company_currency.is_zero(debit_exchange_amount):
    #     #                 if debit_vals.get('record'):
    #     #                     exchange_lines_to_fix += debit_vals['record']
    #     #                 amounts_list.append({'amount_residual': debit_exchange_amount})
    #     #                 remaining_debit_amount -= debit_exchange_amount
    #     #                 if debit_vals['currency'] == company_currency:
    #     #                     remaining_debit_amount_curr -= debit_exchange_amount
    #     #         else:
    #     #             # Create an exchange difference ensuring the rate between the residual amounts expressed in
    #     #             # both foreign and company's currency is still consistent regarding the rate between
    #     #             # 'amount_currency' & 'balance'.
    #     #             debit_exchange_amount = partial_debit_amount - partial_amount
    #     #             if company_currency.compare_amounts(debit_exchange_amount, 0.0) > 0:
    #     #                 if debit_vals.get('record'):
    #     #                     exchange_lines_to_fix += debit_vals['record']
    #     #                 amounts_list.append({'amount_residual': debit_exchange_amount})
    #     #                 remaining_debit_amount -= debit_exchange_amount
    #     #                 if debit_vals['currency'] == company_currency:
    #     #                     remaining_debit_amount_curr -= debit_exchange_amount
    #     #
    #     #         if credit_fully_matched:
    #     #             # Create an exchange difference on the remaining amount expressed in company's currency.
    #     #             credit_exchange_amount = remaining_credit_amount + partial_amount
    #     #             if not company_currency.is_zero(credit_exchange_amount):
    #     #                 if credit_vals.get('record'):
    #     #                     exchange_lines_to_fix += credit_vals['record']
    #     #                 amounts_list.append({'amount_residual': credit_exchange_amount})
    #     #                 remaining_credit_amount += credit_exchange_amount
    #     #                 if credit_vals['currency'] == company_currency:
    #     #                     remaining_credit_amount_curr -= credit_exchange_amount
    #     #         else:
    #     #             # Create an exchange difference ensuring the rate between the residual amounts expressed in
    #     #             # both foreign and company's currency is still consistent regarding the rate between
    #     #             # 'amount_currency' & 'balance'.
    #     #             credit_exchange_amount = partial_amount - partial_credit_amount
    #     #             if company_currency.compare_amounts(credit_exchange_amount, 0.0) < 0:
    #     #                 if credit_vals.get('record'):
    #     #                     exchange_lines_to_fix += credit_vals['record']
    #     #                 amounts_list.append({'amount_residual': credit_exchange_amount})
    #     #                 remaining_credit_amount -= credit_exchange_amount
    #     #                 if credit_vals['currency'] == company_currency:
    #     #                     remaining_credit_amount_curr -= credit_exchange_amount
    #     #
    #     #     if exchange_lines_to_fix:
    #     #         res['exchange_vals'] = exchange_lines_to_fix._prepare_exchange_difference_move_vals(
    #     #             amounts_list,
    #     #             exchange_date=max(debit_vals['date'], credit_vals['date']),
    #     #         )
    #
    #     # ==== Create partials ====
    #
    #     remaining_debit_amount -= partial_amount
    #     remaining_credit_amount += partial_amount
    #     remaining_debit_amount_curr -= partial_debit_amount_currency
    #     remaining_credit_amount_curr += partial_credit_amount_currency
    #
    #     res['partial_vals'] = {
    #         'amount': partial_amount,
    #         'debit_amount_currency': partial_debit_amount_currency,
    #         'credit_amount_currency': partial_credit_amount_currency,
    #         'debit_move_id': debit_vals.get('record') and debit_vals['record'].id,
    #         'credit_move_id': credit_vals.get('record') and credit_vals['record'].id,
    #     }
    #
    #     debit_vals['amount_residual'] = remaining_debit_amount
    #     debit_vals['amount_residual_currency'] = remaining_debit_amount_curr
    #     credit_vals['amount_residual'] = remaining_credit_amount
    #     credit_vals['amount_residual_currency'] = remaining_credit_amount_curr
    #
    #     if debit_fully_matched:
    #         res['debit_vals'] = None
    #     if credit_fully_matched:
    #         res['credit_vals'] = None
    #     #print('res final',res)
    #     return res



