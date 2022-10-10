# coding: utf-8
##############################################################################

###############################################################################

from odoo import fields, models, api
from datetime import datetime

class IgtfPayment(models.TransientModel):

    _name = "igtf.payment.wizard"

    journal_id = fields.Many2one('account.journal', store=True, readonly=False,
                                 compute='_compute_journal_id',
                                 domain="[('company_id', '=', company_id), ('type', 'in', ('bank', 'cash'))]")
    currency_id = fields.Many2one('res.currency', string='Moneda del pago', default=lambda self: self.env.company.currency_id)
    date = fields.Date(string='Fecha del Pago IGTF', default=datetime.now().date())
    amount_igtf = fields.Float('Monto a pagar IGTF', compute='_get_igtf_debt', default=lambda self: self.env['account.move'].browse(self._context.get('active_ids', [])).igtf_debt, store=True, readonly=False)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.depends('company_id', 'currency_id')
    def _compute_journal_id(self):
        for wizard in self:
            domain = [
                ('type', 'in', ('bank', 'cash')),
                ('company_id', '=', wizard.company_id.id),
            ]
            journal = None
            if wizard.currency_id:
                journal = self.env['account.journal'].search(
                    domain + [('currency_id', '=', wizard.currency_id.id)], limit=1)
            if not journal:
                journal = self.env['account.journal'].search(domain, limit=1)
            wizard.journal_id = journal

    def _get_igtf_debt(self):
        if self._context.get('active_model') == 'account.move':
            move = self.env['account.move'].browse(self._context.get('active_ids', []))
            if self.currency_id.id != self.env.company.currency_id.id:
                    self.amount_igtf = move.igtf_usd
            else:
                    self.amount_igtf = move.igtf_debt

    def register_IGTF_payment(self):
        if self._context.get('active_model') == 'account.move':
            move = self.env['account.move'].browse(self._context.get('active_ids', []))

            if self.currency_id.id != self.env.company.currency_id.id:
                to_pay_conversion = self.amount_igtf
                to_pay = self.currency_id._convert(to_pay_conversion, self.env.company.currency_id, self.env.company, self.date)
            else:
                to_pay = self.amount_igtf
                to_pay_conversion = self.currency_id._convert(to_pay, move.igtf_currency, self.env.company, self.date)
            if move.igtf_usd - to_pay_conversion < 0.03 or move.igtf_debt - to_pay < 0.03:
                to_pay_conversion = move.igtf_usd
                to_pay = move.igtf_debt
            vals = {
                'date': self.date,
                'line_ids': False,
                'state': 'draft',
                'journal_id': self.journal_id.id,
                'ref': 'PAGO DE IGTF ' + move.name,
                'invoice_origin': move.name,
            }
            move_obj = self.env['account.move']
            move_id = move_obj.create(vals)
            move_advance_ = {
                'account_id': move.partner_id.property_account_receivable_id.id,
                'company_id': self.company_id.id,
                'date': self.date,
                'partner_id': move.partner_id.id,
                'move_id': move_id.id,
                'credit': to_pay,
                'debit': 0.0,
            }
            if self.currency_id.id != self.env.company.currency_id.id:
                move_advance_['currency_id'] = self.currency_id.id
                move_advance_['amount_currency'] = -to_pay_conversion
            asiento = move_advance_
            move_line_obj = self.env['account.move.line']
            move_line_id1 = move_line_obj.with_context(check_move_validity=False).create(asiento)
            asiento['account_id'] = self.journal_id.payment_debit_account_id.id
            asiento['credit'] = 0.0
            asiento['debit'] = to_pay
            if self.currency_id.id != self.env.company.currency_id.id:
                asiento['currency_id'] = self.currency_id.id
                asiento['amount_currency'] = to_pay_conversion
            move_line_id2 = move_line_obj.create(asiento)
            move_id.action_post()
            move.igtf_usd -= to_pay_conversion
            move.igtf_debt -= to_pay
            move._compute_amount()
            lines = move_line_id1
            lines += self.lines_to_reconcile(move, move_line_id1)
            lines.reconcile()




    def lines_to_reconcile(self, move, line_id):
        name = 'IGTF % de ' + move.name
        moves = self.env['account.move'].search([('ref', '=', name)])
        correct = None
        for i in moves:
            if not correct:
                correct = i.line_ids.filtered(lambda line: line.account_id == line_id[0].account_id and not line.reconciled)
        return correct

    @api.onchange('journal_id')
    def _compute_currency_id(self):
        for wizard in self:
            wizard.currency_id = wizard.journal_id.currency_id
            if wizard.currency_id.id != self.env.company.currency_id.id:
                if self._context.get('active_model') == 'account.move':
                    move = self.env['account.move'].browse(self._context.get('active_ids', []))
                    wizard.amount_igtf = move.igtf_usd
            else:
                if self._context.get('active_model') == 'account.move':
                    move = self.env['account.move'].browse(self._context.get('active_ids', []))
                    wizard.amount_igtf = move.igtf_debt
