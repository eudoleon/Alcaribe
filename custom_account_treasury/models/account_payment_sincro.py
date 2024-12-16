from odoo import models, fields, api, _,Command
from odoo.exceptions import UserError, ValidationError
from odoo.tools import (
    date_utils,
    email_re,
    email_split,
    float_compare,
    float_is_zero,
    float_repr,
    format_amount,
    format_date,
    formatLang,
    frozendict,
    get_lang,
    is_html_empty,
    sql
)
from odoo.osv import expression
import logging

_logger = logging.getLogger(__name__)

class AccountPayment(models.Model):
    _inherit = 'account.payment'


    def _get_multi_line_payment_domain(self):
        return [
                    ('payment_line_ids', '!=', False),
                    ('is_internal_transfer', '=', False)
                ]

    def _seek_for_lines(self):
        """Por defecto,  líneas de moviento con cuentas que no estén en liquidez, cuentas por cobrar o
         por pagar deben llevarse a writeoff_lines. Así que deberíamos mover estos movimientos
         Líneas que tienen cuentas en Payment_line_ids a Counter_lines.
        """
        self.ensure_one()

        liquidity_lines, counterpart_lines, writeoff_lines = super(AccountPayment, self)._seek_for_lines()
        if not self.payment_line_ids:
            return liquidity_lines, counterpart_lines, writeoff_lines
        payment_account_ids = self.payment_line_ids.mapped('account_id').ids
        counterpart_missing_lines = writeoff_lines.filtered(
            lambda l: l.account_id.id in payment_account_ids or l.account_id.reconcile
        )
        counterpart_lines |= counterpart_missing_lines
        writeoff_lines -= counterpart_missing_lines

        return liquidity_lines, counterpart_lines, writeoff_lines

     # from_moves
    def _synchronize_from_moves(self, changed_fields):
        if self._context.get('skip_account_move_synchronization'):
            return
        domain = self._get_multi_line_payment_domain()
        domain = expression.AND([domain, [('move_id.statement_line_id', '=', False)]])
        multi_line_payments = self.filtered_domain(domain)
        payments = self - multi_line_payments

        # if multi_line_payments:
        #     if multi_line_payments.payment_line_ids:
        multi_line_payments.with_context(skip_account_move_synchronization=True)._synchronize_multi_line_from_moves(changed_fields)
            # else:
            #     multi_line_payments.with_context(skip_account_move_synchronization=True)._synchronize_from_moves(changed_fields)
        if payments:
            super(AccountPayment, payments)._synchronize_from_moves(changed_fields)

    def _synchronize_multi_line_from_moves(self, changed_fields):
        for r in self:
            move = r.move_id
            move_vals_to_write = {}
            payment_vals_to_write = {}

            if 'journal_id' in changed_fields:
                if r.journal_id.type not in ('bank', 'cash'):
                    raise UserError(_("Un pago siempre debe pertenecer a un banco o diario de caja."))

            if 'line_ids' in changed_fields:
                all_lines = move.line_ids
                liquidity_lines, counterpart_lines, writeoff_lines = r._seek_for_lines()

                if len(liquidity_lines) != 1:
                    raise UserError(_(
                        "The journal entry %s reached an invalid state relative to its payment.\n"
                        "To be consistent, the journal entry must always have only one journal item involving the outstanding payment/receipts account"
                    ) % move.display_name)

                # if writeoff_lines and len(writeoff_lines.account_id) != 1:
                #     raise UserError(_(
                #         "The journal entry %s reached an invalid state relative to its payment.\n"
                #         "To be consistent, all the write-off journal items must share the same account."
                #     ) % move.display_name)
                # if any(line.currency_id != all_lines[0].currency_id for line in all_lines):
                #     raise UserError(_(
                #         "The journal entry %s reached an invalid state relative to its payment.\n"
                #         "To be consistent, the journal items must share the same currency."
                #     ) % move.display_name)
                # if any(line.partner_id != all_lines[0].partner_id for line in all_lines):
                #     raise UserError(_(
                #         "The journal entry %s reached an invalid state relative to its payment.\n"
                #         "To be consistent, the journal items must share the same partner."
                #     ) % move.display_name)
                partner_type = r.partner_type
               
                liquidity_amount = liquidity_lines.amount_currency
                # Save account move line for reconcile
                # Remove account payment line
                r.payment_line_ids = [(5, 0, 0)]
                # Update account payment line from account move line
                account_payment_line_vals = []
                for move_line in counterpart_lines:
                    account_payment_line_vals.append((0, 0, {
                            'name': move_line.name or liquidity_lines[0].name,
                            'account_id': move_line.account_id.id,
                            'debit': move_line.debit,
                            'credit': move_line.credit,
                            'payment_amount': move_line.balance,
                            'move_line_id': move_line.line_pay.id,
                            'partner_id': move_line.partner_id.id,
                            'ref': move_line.name,
                            'is_transfer': move_line.is_transfer,
                            'is_main': move_line.is_main,
                            'is_counterpart': move_line.is_counterpart,
                            'move_id': move_line.move_id.id,
                        }))
                for move_line in liquidity_lines:
                    account_payment_line_vals.append((0, 0, {
                            'name': move_line.name or liquidity_lines[0].name,
                            'account_id': move_line.account_id.id,
                            'debit': move_line.debit,
                            'credit': move_line.credit,
                            'payment_amount': move_line.amount_currency,
                            'move_line_id': move_line.line_pay.id,
                            'partner_id': move_line.partner_id.id,
                            'ref': move_line.name,
                            'move_id': move_line.move_id.id,
                            'is_transfer': move_line.is_transfer,
                            'is_main': move_line.is_main,
                            'is_counterpart': move_line.is_counterpart,
                            'display_type': 'asset_cash',
                        }))
                for move_line in writeoff_lines:
                    account_payment_line_vals.append((0, 0, {
                            'name': move_line.name or writeoff_lines[0].name,
                            'account_id': move_line.account_id.id,
                            'debit': move_line.debit,
                            'credit': move_line.credit,
                            'payment_amount': move_line.balance,
                            'move_line_id': move_line.line_pay.id,
                            'partner_id': move_line.partner_id.id,
                            'ref': move_line.name,
                            'move_id': move_line.move_id.id,
                            'is_transfer': move_line.is_transfer,
                            'is_main': move_line.is_main,
                            'is_counterpart': move_line.is_counterpart,
                        }))
                move_vals_to_write.update({
                    'currency_id': liquidity_lines.currency_id.id,
                    'partner_id': liquidity_lines.partner_id.id,
                })
                payment_vals_to_write.update({
                    'amount': abs(liquidity_amount),
                    'partner_type': partner_type,
                    'currency_id': liquidity_lines.currency_id.id,
                    'partner_id': liquidity_lines.partner_id.id,
                    'payment_line_ids': account_payment_line_vals,
                })
                #if liquidity_amount > 0.0:
                #    payment_vals_to_write.update({'payment_type': 'inbound'})
                #elif liquidity_amount < 0.0:
                #    payment_vals_to_write.update({'payment_type': 'outbound'})

            move.write(move._cleanup_write_orm_values(move, move_vals_to_write))
            r.write(move._cleanup_write_orm_values(r, payment_vals_to_write))

     # to_moves
    def _synchronize_multi_line_to_moves(self, changed_fields):
        if not any(field_name in changed_fields for field_name in (
            'date', 
            'amount', 
            'payment_type', 
            'partner_type', 
            'payment_reference', 
            'is_internal_transfer',
            'currency_id', 
            'partner_id', 
            'destination_account_id', 
            'partner_bank_id', 
            'journal_id', 
            'payment_line_ids',
        )):
            return

        for r in self:
            liquidity_lines, counterpart_lines, writeoff_lines = r._seek_for_lines()
            if liquidity_lines and counterpart_lines and writeoff_lines:
                counterpart_amount = sum(counterpart_lines.mapped('amount_currency'))
                writeoff_amount = sum(writeoff_lines.mapped('amount_currency'))

                if (counterpart_amount > 0.0) == (writeoff_amount > 0.0):
                    sign = -1
                else:
                    sign = 1
                writeoff_amount = abs(writeoff_amount) * sign

                write_off_line_vals = {
                    'name': writeoff_lines[0].name,
                    'amount': writeoff_amount,
                    'account_id': writeoff_lines[0].account_id.id,
                }
            else:
                write_off_line_vals = {}
            line_vals_list = r._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals)

            line_ids_commands = []
            if liquidity_lines:
                # if len(liquidity_lines) > 1:
                #     raise UserError(_(
                #         "The journal entry %s reached an invalid state relative to its payment.\n"
                #         "To be consistent, the journal entry must always contains:\n"
                #         "- one journal item involving the outstanding payment/receipts account.\n"
                #         "- one or more journal items involving a receivable/payable account.\n"
                #     ) % r.move_id.display_name)
                line_ids_commands.append((1, liquidity_lines.id, line_vals_list[0]))
            else:
                line_ids_commands.append((0, 0, line_vals_list[0]))
            if counterpart_lines:
                for line in counterpart_lines:
                    line_ids_commands.append((2, line.id, 0))
                for counterpart_vals in line_vals_list[1:]:
                    line_ids_commands.append((0, 0, counterpart_vals))
            else:
                line_ids_commands.append((0, 0, line_vals_list[1]))

            for line in writeoff_lines:
                line_ids_commands.append((2, line.id))

            r.move_id.write({
                'partner_id': r.partner_id.id,
                'currency_id': r.currency_id.id,
                'partner_bank_id': r.partner_bank_id.id,
                'line_ids': line_ids_commands,
            })

    def _synchronize_to_moves(self, changed_fields):
        if self._context.get('skip_account_move_synchronization'):
            return

        domain = self._get_multi_line_payment_domain()
        multi_line_payments = self.filtered_domain(domain)
        payments = self - multi_line_payments

        #if multi_line_payments:
        multi_line_payments.with_context(skip_account_move_synchronization=True)._synchronize_multi_line_to_moves(changed_fields)
        if not multi_line_payments and 'payment_line_ids' in changed_fields:
           self.move_id.with_context(skip_account_move_synchronization=True).write({
               'line_ids': [(5, 0, 0)]
               })
        if payments:
           super(AccountPayment, payments)._synchronize_to_moves(changed_fields)


    @api.model_create_multi
    @api.returns('self', lambda value:value.id)
    def create(self, vals_list):
        skip_account_move_synchronization_payments_vals_list = []
        account_move_synchronization_payments_vals_list = []
        Payments = self.env['account.payment']
        for vals in vals_list:
            if vals.get('payment_line_ids', []):
                skip_account_move_synchronization_payments_vals_list.append(vals)
            else:
                account_move_synchronization_payments_vals_list.append(vals)
        if skip_account_move_synchronization_payments_vals_list:
            skip_payments = super(AccountPayment, self.with_context(skip_account_move_synchronization=True))\
            .create(skip_account_move_synchronization_payments_vals_list)
            Payments |= skip_payments
        if account_move_synchronization_payments_vals_list:
            payments = super(AccountPayment, self).create(account_move_synchronization_payments_vals_list)
            Payments |= payments
        for payment in Payments:
            liquidity_lines, counterpart_lines, writeoff_lines = payment._seek_for_lines()
            if len(liquidity_lines) > 1:
                    raise UserError(_(
                        "El asiento de diario %s alcanzó un estado no válido en relación con su pago.\n"
                        "Para ser coherente, el asiento del diario siempre debe contener:\n"
                        "- un elemento del diario relacionado con la cuenta de pagos/recibos pendientes.\n"
                        "- uno o más elementos del diario relacionados con una cuenta por cobrar/por pagar.\n"
                    ) % payment.move_id.display_name)
        return Payments


    @api.model
    def _get_trigger_fields_to_synchronize(self):
        return (
            'date', 'amount', 'payment_type', 'partner_type', 'payment_reference', 'is_internal_transfer',
            'currency_id', 'partner_id', 'destination_account_id', 'partner_bank_id', 'journal_id', 'payment_line_ids',
        )