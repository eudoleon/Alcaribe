# coding: utf-8
from odoo import fields, models, api, _
from datetime import datetime, date, timedelta

class GenerarIgftWizard(models.TransientModel):
    _name = "generar.igtf.wizard"
    _description = "Generar Retención IGTF"

    invoice_id = fields.Many2one('account.move', string='Factura', required=True)
    tax_today = fields.Float(string="Tasa Actual", digits='Dual_Currency_rate')
    amount = fields.Monetary(currency_field='currency_id_dif', string='Monto $', required=True)
    igtf_porcentage = fields.Float('Porcentaje', required=True, readonly=True)
    igtf_amount = fields.Monetary(currency_field='currency_id_dif', string='Monto IGTF $', required=True, default=0.0,
                                  compute='compute_igtf_amount')
    igtf_amount_bs = fields.Monetary(currency_field='currency_id_company', string='Monto IGTF Bs', required=True,
                                     default=0.0, compute='compute_igtf_amount')
    currency_id_dif = fields.Many2one('res.currency', string='Moneda $', required=True)
    currency_id_company = fields.Many2one('res.currency', string='Moneda Compañia', required=True)
    journal_id = fields.Many2one('account.journal', string='Diario Retención IGTF', required=True)
    account_id = fields.Many2one('account.account', string='Cuenta retención IGFT', required=True)

    @api.onchange('amount')
    def compute_igtf_amount(self):
        for rec in self:
            rec.igtf_amount = rec.amount * rec.igtf_porcentage / 100
            rec.igtf_amount_bs = (rec.amount * rec.igtf_porcentage / 100) * rec.tax_today

    def generar_retencion(self):
        for rec in self:
            line_ids = []
            account_to_reconcile = False
            if rec.invoice_id.move_type in ['out_invoice','out_refund']:
                line_ids.append((0, 0, {
                    'name': 'Retención IGTF %s' % rec.invoice_id.name,
                    'currency_id': rec.currency_id_dif.id,
                    'amount_currency': rec.igtf_amount,
                    'debit': rec.igtf_amount_bs,
                    'debit_usd': rec.igtf_amount,
                    'credit': 0.0,
                    'account_id': rec.account_id.id,
                }))
                line_ids.append((0, 0, {
                    'name': 'Retención IGTF %s' % rec.invoice_id.name,
                    'currency_id': rec.currency_id_dif.id,
                    'amount_currency': - rec.igtf_amount,
                    'debit': 0.0,
                    'credit': rec.igtf_amount_bs,
                    'credit_usd': rec.igtf_amount,
                    'account_id': rec.invoice_id.partner_id.property_account_receivable_id.id,
                    'partner_id': rec.invoice_id.partner_id.id,
                }))
                account_to_reconcile = rec.invoice_id.partner_id.property_account_receivable_id.id
            elif rec.invoice_id.move_type in ['in_invoice','in_refund']:
                line_ids.append((0, 0, {
                    'name': 'Retención IGTF %s' % rec.invoice_id.name,
                    'currency_id': rec.currency_id_dif.id,
                    'amount_currency': - rec.igtf_amount,
                    'debit': 0.0,
                    'credit': rec.igtf_amount_bs,
                    'credit_usd': rec.igtf_amount,
                    'account_id': rec.account_id.id,
                }))
                line_ids.append((0, 0, {
                    'name': 'Retención IGTF %s' % rec.invoice_id.name,
                    'currency_id': rec.currency_id_dif.id,
                    'amount_currency': rec.igtf_amount,
                    'debit': rec.igtf_amount_bs,
                    'debit_usd': rec.igtf_amount,
                    'credit': 0.0,
                    'account_id': rec.invoice_id.partner_id.property_account_payable_id.id,
                    'partner_id': rec.invoice_id.partner_id.id,
                }))
                account_to_reconcile = rec.invoice_id.partner_id.property_account_payable_id.id
            move_flete = {
                'journal_id': rec.journal_id.id,
                'currency_id': rec.currency_id_dif.id,
                'date': datetime.now(),
                'move_type': 'entry',
                'ref': 'Retención IGTF ' + rec.invoice_id.name,
                'tax_today': rec.tax_today,
                'line_ids': line_ids,
            }
            move_rete_igtf = self.env['account.move'].with_context(check_move_validity=False).create(move_flete)
            move_rete_igtf.action_post()
            rec.invoice_id.move_igtf_id = move_rete_igtf
            to_reconcile = rec.invoice_id.line_ids.filtered_domain(
                [('account_id', '=', account_to_reconcile), ('reconciled', '=', False)])
            ret_lines = move_rete_igtf.line_ids.filtered_domain(
                [('account_id', '=', account_to_reconcile), ('reconciled', '=', False)])

            results = (ret_lines + to_reconcile).reconcile()
            if 'partials' in results:
                if results['partials'].amount_usd == 0:
                    ret_lines._compute_amount_residual_usd()
                    monto_usd = abs(ret_lines.amount_residual_usd)
                    results['partials'].write({'amount_usd': monto_usd})
                    ret_lines._compute_amount_residual_usd()