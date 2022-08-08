# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, date_utils, email_split, email_re
from odoo.tools.misc import formatLang, format_date, get_lang
from collections import defaultdict


class AccountMove(models.Model):
    _inherit = "account.move"

    amount_withholding = fields.Monetary(string="Withholding Amount",
        compute='_compute_invoice_withholding_taxes', store=True)
    wht_executed = fields.Boolean(string="WHT Executed")

    @api.depends('line_ids.withholding_tax', 'line_ids.withholding_tax_id')
    def _compute_invoice_withholding_taxes(self):
        for move in self:
            if move.invoice_line_ids:
                move.amount_withholding = sum(rec.withholding_subtotal for rec in move.invoice_line_ids)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    withholding_tax = fields.Boolean(string="Withholding")
    withholding_tax_id = fields.Many2one('account.tax', string="Withholding Tax", domain=[("withholding_tax", "=", True)])
    withholding_subtotal = fields.Monetary(string="Withholding Subtotal",
        compute='_compute_withholding_subtotal')

    @api.onchange('withholding_tax_id')
    def onchange_withholding_tax_id(self):
        if self.withholding_tax_id:
            if not self.withholding_tax_id.invoice_repartition_line_ids:
                raise ValidationError(_("Warning, please set account in Tax/Withholding Tax (%s, %s)" % (self.product_id.withholding_tax_id.id, self.product_id.withholding_tax_id.name or "")))
            for tax in self.withholding_tax_id.invoice_repartition_line_ids:
                if not tax.account_id and tax.repartition_type == 'tax':
                    raise ValidationError(_("Warning, please set account in Tax/Withholding Tax (%s, %s)" % (self.product_id.withholding_tax_id.id, self.product_id.withholding_tax_id.name or "")))   

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id.apply_withholding:
            self.withholding_tax = True
        else:
            self.withholding_tax = False
        
        tax_ids = []
        if self.product_id.apply_withholding and self.product_id.withholding_tax_id:
            if not self.product_id.withholding_tax_id.invoice_repartition_line_ids:
                raise ValidationError(_("Warning, please set account in Tax/Withholding Tax (%s, %s)" % (self.product_id.withholding_tax_id.id, self.product_id.withholding_tax_id.name or "")))
            for tax in self.product_id.withholding_tax_id.invoice_repartition_line_ids:
                if not tax.account_id and tax.repartition_type == 'tax':
                    raise ValidationError(_("Warning, please set account in Tax/Withholding Tax (%s, %s)" % (self.product_id.withholding_tax_id.id, self.product_id.withholding_tax_id.name or "")))
        
            self.update({
               # 'withholding_tax_id': [(6, 0, tax_ids)]
               'withholding_tax_id': self.product_id.withholding_tax_id
            })
        else:
            self.withholding_tax_id = False

    @api.depends('quantity', 'price_unit', 'withholding_tax', 'withholding_tax_id')
    def _compute_withholding_subtotal(self):
        for rec in self:
            if rec.withholding_tax and rec.withholding_tax_id:
                tax = rec.withholding_tax_id
                amount = ((rec.quantity * rec.price_unit) * (tax.amount * 0.01))
                rec.withholding_subtotal = amount
            else:
                rec.withholding_subtotal = 0


class WithholdingLine(models.Model):
    _name = 'withholding.line'

    payment_id = fields.Many2one('account.payment', string="Account Payment")
    account_id = fields.Many2one('account.account', string="Account")
    name = fields.Char(string="Label")
    amount_withholding = fields.Float(string="Amount")
