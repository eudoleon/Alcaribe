# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    currency_id_dif = fields.Many2one("res.currency",
                                      string="Divisa de Referencia",
                                      related="company_id.currency_id_dif", store=True)

    amount_usd = fields.Monetary(currency_field='currency_id_dif', string='Importe $', required=True, default=0.0)

    @api.model
    def create(self, vals):
        print("vals",vals)
        if isinstance(vals, list):
            for val in vals:
                if 'move_line_id' in val:
                    move_id = self.env['account.move.line'].search([('id','=',val['move_line_id'])])
                    amount_usd = move_id.debit_usd if move_id.debit_usd > 0 else move_id.credit_usd
                    val['amount_usd'] = amount_usd
        else:
            if 'move_line_id' in vals:
                move_id = self.env['account.move.line'].search([('id', '=', vals['move_line_id'])])
                amount_usd = move_id.debit_usd if move_id.debit_usd > 0 else move_id.credit_usd
                vals['amount_usd'] = amount_usd
        return super(AccountAnalyticLine, self).create(vals)