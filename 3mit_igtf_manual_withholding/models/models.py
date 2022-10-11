# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import json
from odoo.tools.misc import formatLang

class AccountTax(models.Model):
    _inherit = 'account.tax'

    appl_type = fields.Selection(string='Tipo de Alicuota', required=False,
                                 selection=[('igtf', 'IGTF')],
                                 help='Especifique el tipo de alícuota para el impuesto para que pueda procesarse ')

class Company(models.Model):
    _inherit = 'res.company'

    igtf_description = fields.Char(string='Descripción IGTF')
    igtf_transition_account = fields.Many2one('account.account', string="Cuenta Transitoria de IGTF VENTAS")
    igtf_purchase_transition_account = fields.Many2one('account.account', string="Cuenta Transitoria de IGTF COMPRAS")
    igtf_sale_journal_id = fields.Many2one('account.journal', string="Diario de IGTF Ventas", company_dependent=True)
    igtf_purchase_journal_id = fields.Many2one('account.journal', string="Diario de IGTF Compras",
                                               company_dependent=True)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    igtf_description = fields.Char(string='Descripción IGTF', related="company_id.igtf_description", readonly=False,
                                   help="Descripción del IGTF para añadir a la factura.")
    igtf_transition_account = fields.Many2one('account.account', string="Cuenta Transitoria de IGTF VENTAS", related="company_id.igtf_transition_account", readonly=False)
    igtf_purchase_transition_account = fields.Many2one('account.account', string="Cuenta Transitoria de IGTF COMPRAS",
                                              related="company_id.igtf_purchase_transition_account", readonly=False)

class AccountMoveInherit(models.Model):
    _inherit = 'account.move'

    igtf_by_group = fields.Binary(string="Tax amount by group",
                                  compute='_compute_invoice_taxes_by_group',
                                  help='Edit Tax amounts if you encounter rounding issues.')
    # igtf_by_group_bs = fields.Binary(string="Tax amount by group",
    #                                  compute='_compute_invoice_taxes_by_group_bs',
    #                                  help='Edit Tax amounts if you encounter rounding issues.')
    total_with_igtf = fields.Monetary(string='Total con IGTF', copy=False)
    total_with_igtf_bs = fields.Monetary(string='Total con IGTF', copy=False)
    igtf_debt = fields.Float(string='3% en Bs', default=0, copy=False)
    igtf_import = fields.Float(default=0, copy=False)
    igtf_currency = fields.Many2one('res.currency', default=lambda self: self.env['res.currency'].search([('name', '=', 'USD')], limit=1))
    amount_igtf_usd = fields.Float(string='COBRO EN USD', default=0, copy=False)
    igtf_usd = fields.Float(string='3% del Importe', default=0, copy=False)
    is_igtf = fields.Boolean(string='APLICAR 3% IGTF' ,default=False, copy=False)
    igtf_move = fields.Boolean(default=False, copy=False)

    def action_post(self):
        # En caso de que se halla especificado el monto de IGTF
        for move in self:
            if move.loc_ven and move.is_igtf and move.amount_igtf_usd > 0:
                move.with_context(check_move_validity=False).add_line_igtf()
        return super(AccountMoveInherit, self).action_post()

    #Función que agrega la línea del impuesto de IGTF a la factura en los apuntes y modifica el primer monto
    def add_line_igtf(self, change=0):
        lines = list(filter(lambda line: line.name == "IGTF %", self.line_ids))
        if self.move_type in ['out_invoice', 'in_invoice']:
            if not lines:
                move_line_obj = self.env['account.move.line']
                line1 = {
                    'account_id': self.company_id.igtf_transition_account.id if self.move_type == 'out_invoice' else self.company_id.igtf_purchase_transition_account.id,
                    'company_id': self.company_id.id,
                    'date': self.invoice_date,
                    'partner_id': self.partner_id.id,
                    'move_id': self.id,
                    'name': "IGTF %",
                    'journal_id': self.journal_id.id,
                    'debit': self.igtf_debt if self.move_type == 'in_invoice' else 0.0,
                    'credit': self.igtf_debt if self.move_type == 'out_invoice' else 0.0,
                    'exclude_from_invoice_tab': True,
                }
                sign = 1 if self.move_type == 'in_invoice' else -1
                if self.currency_id.id != self.env.company.currency_id.id:
                    line1['currency_id'] = self.currency_id.id
                    line1['amount_currency'] = sign * self.igtf_import
                move_line_obj.with_context(check_move_validity=False).create(line1)
                account_to_edit = self.partner_id.property_account_receivable_id if self.move_type == 'out_invoice' else self.partner_id.property_account_payable_id
                for line in self.line_ids:
                    if line.account_id.id == account_to_edit.id:
                        if line.debit:
                            line.debit = line.debit + self.igtf_debt
                            if self.currency_id.id != self.env.company.currency_id.id:
                                line.amount_currency = line.amount_currency + abs(self.igtf_import)
                        if line.credit:
                            line.credit = line.credit + self.igtf_debt
                            if self.currency_id.id != self.env.company.currency_id.id:
                                line.amount_currency = line.amount_currency - abs(self.igtf_import)
            elif change:
                for line_1 in lines:
                    old_credit = line_1.credit if self.move_type == 'out_invoice' else line_1.debit
                    old_import = line_1.amount_currency
                    if self.move_type == 'out_invoice':
                        line_1.credit = self.igtf_debt
                    else:
                        line_1.debit = self.igtf_debt
                    sign = 1 if self.move_type == 'in_invoice' else -1
                    if self.currency_id.id != self.env.company.currency_id.id:
                        line_1.amount_currency = sign * self.igtf_import
                    account_to_edit = self.partner_id.property_account_receivable_id if self.move_type == 'out_invoice' else self.partner_id.property_account_payable_id
                    for line in self.line_ids:
                        if line.account_id.id == account_to_edit.id:
                            if line.debit:
                                line.debit = line.debit - old_credit
                                line.debit = line.debit + self.igtf_debt
                                if self.currency_id.id != self.env.company.currency_id.id:
                                    line.amount_currency = line.amount_currency - abs(old_import)
                                    line.amount_currency = line.amount_currency + abs(self.igtf_import)
                            if line.credit:
                                line.credit = line.credit - old_credit
                                line.credit = line.credit + self.igtf_debt
                                if self.currency_id.id != self.env.company.currency_id.id:
                                    line.amount_currency = line.amount_currency + abs(old_import)
                                    line.amount_currency = line.amount_currency - abs(self.igtf_import)

    def write(self, vals):
        change = 0
        is_igtf_change = False
        if 'amount_igtf_usd' in vals:
            if vals.get('amount_igtf_usd') != self.amount_igtf_usd:
                change = vals.get('amount_igtf_usd')
        if 'is_igtf' in vals:
            if vals.get('is_igtf') == False:
                is_igtf_change = True
        res = super(AccountMoveInherit, self).write(vals)
        line_to_remove = list(filter(lambda line: line.name == "IGTF %", self.line_ids))
        for i in self:
            if i.move_type in ['out_invoice', 'in_invoice']:
                if line_to_remove and not i.is_igtf and is_igtf_change:
                    for line in line_to_remove:
                        i.with_context(check_move_validity=False).delete_igtf_line(line, i)
                        i.amount_igtf_usd = 0
                        i.activate_igtf()
                if i.is_igtf:
                    i.with_context(check_move_validity=False).add_line_igtf(change)
        return res


    @api.onchange('amount_igtf_usd')
    def activate_igtf(self):
        for move in self:
            if move.loc_ven:
                if not move.is_igtf or not move.amount_igtf_usd:
                    move.igtf_usd = 0
                    move.igtf_debt = 0
                    move.igtf_import = 0
                else:
                    move.igtf_usd = round(move.amount_igtf_usd * 0.03, 2)
                    move.igtf_debt = move.igtf_currency._convert(move.igtf_usd, self.env.company.currency_id,
                                                                 self.env.company, move.invoice_date)
                    if move.currency_id.id != self.env.company.currency_id.id:
                        move.igtf_import = move.igtf_currency._convert(move.igtf_usd, self.currency_id,
                                                                     self.env.company, move.invoice_date)
                    else:
                        move.igtf_import = 0

    # @api.depends('line_ids.price_subtotal', 'line_ids.tax_base_amount', 'line_ids.tax_line_id', 'partner_id',
    #              'currency_id')
    # def _compute_invoice_taxes_by_group_bs(self):
    #     res = super(AccountMoveInherit, self)._compute_invoice_taxes_by_group_bs()
    #     reconciled_vals = []
    #     for move in self:
    #         if move.is_igtf:
    #             if move.move_type == 'out_invoice' and move.move_type in ['out_invoice', 'in_invoice']:
    #                 impuesto = self.env['account.tax'].search(
    #                     [('appl_type', '=', 'igtf'), ('company_id', '=', move.company_id.id),
    #                      ('type_tax_use', '=', 'sale')])
    #             if move.move_type == 'in_invoice':
    #                 impuesto = self.env['account.tax'].search(
    #                     [('appl_type', '=', 'igtf'), ('company_id', '=', move.company_id.id),
    #                      ('type_tax_use', '=', 'purchase')])
    #             group_id = impuesto.tax_group_id
    #             base = move.igtf_debt
    #             tax = round(base, 2)
    #             if base and tax:
    #                 lang_env = self.with_context(lang=move.partner_id.lang).env
    #                 move.igtf_by_group_bs = [(
    #                     group_id.name, tax,
    #                     base,
    #                     formatLang(lang_env, tax, currency_obj=self.env.company.currency_id),
    #                     formatLang(lang_env, base, currency_obj=self.env.company.currency_id),
    #                     1,
    #                     group_id.id
    #                 )]
    #             else:
    #                 move.igtf_by_group_bs = None
    #             if move.igtf_by_group_bs:
    #                 for i in move.igtf_by_group_bs:
    #                     move.total_with_igtf_bs = move.amount_total_conversion + i[1]
    #             else:
    #                 move.total_with_igtf_bs = move.amount_total_conversion
    #         else:
    #             for move in self:
    #                 move.igtf_by_group_bs = None
    #     return res

    @api.depends('line_ids.price_subtotal', 'line_ids.tax_base_amount', 'line_ids.tax_line_id', 'partner_id',
                 'currency_id')
    def _compute_invoice_taxes_by_group(self):
        res = super(AccountMoveInherit, self)._compute_invoice_taxes_by_group()
        reconciled_vals = []
        for move in self:
            if self.env.company.loc_ven and move.is_igtf and move.move_type in ['out_invoice', 'in_invoice']:
                if move.move_type == 'out_invoice':
                    impuesto = self.env['account.tax'].search(
                        [('appl_type', '=', 'igtf'), ('company_id', '=', move.company_id.id),
                         ('type_tax_use', '=', 'sale')])
                if move.move_type == 'in_invoice':
                    impuesto = self.env['account.tax'].search(
                        [('appl_type', '=', 'igtf'), ('company_id', '=', move.company_id.id),
                         ('type_tax_use', '=', 'purchase')])
                group_id = impuesto.tax_group_id
                if move.currency_id.id == self.env.company.currency_id.id:
                    base = move.igtf_debt
                elif move.currency_id.id == move.igtf_currency.id:
                    base = move.igtf_usd
                else:
                    base = move.igtf_import
                tax = round(base, 2)
                if base and tax:
                    largo = 1
                    lang_env = self.with_context(lang=move.partner_id.lang).env
                    move.igtf_by_group = [(
                        group_id.name, tax,
                        base,
                        formatLang(lang_env, tax, currency_obj=move.currency_id),
                        formatLang(lang_env, base, currency_obj=move.currency_id),
                        largo,
                        group_id.id
                    )]
                else:
                    move.igtf_by_group = None
                if move.igtf_by_group:
                    for i in move.igtf_by_group:
                        move.total_with_igtf = move.amount_total + i[1]
                else:
                    move.total_with_igtf = move.amount_total
            else:
                for move in self:
                    move.igtf_by_group = None
        return res


    @api.model_create_multi
    def create(self, vals):
        res = super(AccountMoveInherit, self).create(vals)
        if self.env.company.loc_ven:
            for i in res:
                i.narration = self.env.company.igtf_description
                if i.amount_igtf_usd:
                    i.add_line_igtf()
        return res

    def copy(self, default=None):
        res = super(AccountMoveInherit, self).copy(default)
        line_to_remove = list(filter(lambda line: line.name == "IGTF %", res.line_ids))
        for line in line_to_remove:
            res.with_context(check_move_validity=False).delete_igtf_line(line, res)
        return res

    def delete_igtf_line(self, line, res):
        credit = line.credit
        amount_currency = line.amount_currency
        line.with_context(check_move_validity=False).unlink()
        account_to_edit = res.partner_id.property_account_receivable_id if res.move_type == 'out_invoice' else res.partner_id.property_account_payable_id
        for i in res.line_ids:
            if i.account_id.id == account_to_edit.id:
                i.debit = i.debit - credit
                if res.currency_id.id != self.env.company.currency_id.id:
                    i.amount_currency = i.amount_currency - abs(amount_currency)

    @api.depends(
        'line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.debit',
        'line_ids.credit',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id')
    def _compute_amount(self):
        res = super(AccountMoveInherit, self)._compute_amount()
        for move in self:
            if move.amount_residual == 0.0 and move.state == 'posted' and not move.igtf_move and move.is_igtf and move.loc_ven:
                move.create_igtf_move_payment()
                move.igtf_move = True
        return res

    def create_igtf_move_payment(self):
        vals = {
            'date': self.invoice_date,
            'line_ids': False,
            'state': 'draft',
            'journal_id': self.company_id.igtf_sale_journal_id.id if self.move_type == 'out_invoice' else self.company_id.igtf_purchase_journal_id.id,
            'ref': 'IGTF ' + self.name,
            'invoice_origin': self.name,
            'currency_id': self.env.company.currency_id.id,
            # 'currency_bs_rate': self.currency_bs_rate,
        }
        move_obj = self.env['account.move']
        move_id = move_obj.create(vals)
        move_advance_ = {
            'account_id': self.company_id.igtf_transition_account.id if self.move_type == 'out_invoice' else self.company_id.igtf_purchase_transition_account.id,
            'company_id': self.company_id.id,
            'date': self.invoice_date,
            'partner_id': self.partner_id.id,
            'move_id': move_id.id,
            'debit': self.igtf_debt if self.move_type == 'out_invoice' else 0.0,
            'credit': self.igtf_debt if self.move_type == 'in_invoice' else 0.0,
        }
        asiento = move_advance_
        move_line_obj = self.env['account.move.line']
        move_line_id1 = move_line_obj.with_context(check_move_validity=False).create(asiento)
        cuenta = False
        if self.move_type == 'out_invoice':
            impuesto = self.env['account.tax'].search(
                [('appl_type', '=', 'igtf'), ('company_id', '=', self.company_id.id), ('type_tax_use', '=', 'sale')])
        if self.move_type == 'in_invoice':
            impuesto = self.env['account.tax'].search(
                [('appl_type', '=', 'igtf'), ('company_id', '=', self.company_id.id),
                 ('type_tax_use', '=', 'purchase')])
        for i in impuesto.invoice_repartition_line_ids:
            if i.account_id:
                cuenta = i.account_id
        asiento['account_id'] = cuenta.id
        asiento['credit'] = self.igtf_debt if self.move_type == 'out_invoice' else 0.0
        asiento['debit'] = self.igtf_debt if self.move_type == 'in_invoice' else 0.0
        move_line_id2 = move_line_obj.create(asiento)
        move_id.action_post()

