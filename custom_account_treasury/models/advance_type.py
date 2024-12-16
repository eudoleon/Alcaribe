from odoo import fields, models, api, _

class AdvanceType(models.Model):
	_name = "advance.type"
	_description = "Tipo de anticipo"

	name = fields.Char(string="Name", required=True)
	account_id = fields.Many2one('account.account', string="Cuenta de anticipo", required=True, domain=[('account_type','in',('asset_receivable', 'liability_payable'))])
	internal_type = fields.Selection(related='account_id.account_type', string="Internal Type", store=True, readonly=True)
	company_id = fields.Many2one('res.company', related='account_id.company_id', string='Company', store=True, readonly=True)

class Account(models.Model):
    _inherit = 'account.account'

    used_for_advance_payment = fields.Boolean()

    @api.onchange('used_for_advance_payment')
    def onchange_used_for_advance_payment(self):
        if self.used_for_advance_payment:
            self.reconcile = self.used_for_advance_payment