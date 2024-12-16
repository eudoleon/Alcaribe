from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, format_date, get_lang
import logging
import json
from json import dumps
from odoo.tools import float_is_zero, UserError, datetime
from contextlib import ExitStack, contextmanager
_logger = logging.getLogger(__name__)

class AccountPaymentRegister(models.TransientModel):
	_inherit='account.payment.register'

	account_id = fields.Many2one(
		comodel_name='account.account',
		string='Cuenta de origen',
		store=True, readonly=False,
		domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
		check_company=True)
	destination_account_id = fields.Many2one(
		comodel_name='account.account',
		string='Destination Account',
		store=True, readonly=False,
		domain="[('account_type', 'in', ('asset_receivable', 'liability_payable')), ('company_id', '=', company_id)]",
		check_company=True)
	change_destination_account = fields.Char(string="cambio de cuenta destino")

	# def _create_payment_vals_from_wizard(self):
	# 	payment_vals = super(AccountPaymentRegister, self)._create_payment_vals_from_wizard()
	# 	if self.account_id:
	# 		payment_vals['account_id'] = self.account_id.id
	# 	if self.destination_account_id:
	# 		payment_vals['destination_account_id'] = self.destination_account_id.id
	# 	return payment_vals

class AccountMove(models.Model):
	_inherit = "account.move"

	pay_id = fields.Many2one(
		comodel_name='account.payment',
		string='Pago',
		required=False)

	# @contextmanager
	# def _check_balanced(self, container):
	# 	''' Assert the move is fully balanced debit = credit.
	# 	An error is raised if it's not the case.
	# 	'''
	# 	with self._disable_recursion(container, 'check_move_validity', default=True, target=False) as disabled:
	# 		yield
	# 		if disabled:
	# 			return

	# 	unbalanced_moves = self._get_unbalanced_moves(container)
	# 	if unbalanced_moves:
	# 		error_msg = _("An error has occurred.")
	# 		for move_id, sum_debit, sum_credit in unbalanced_moves:
	# 			move = self.browse(move_id)
	# 		#raise UserError(error_msg)

		
class AccountMoveLine(models.Model):
	_inherit = "account.move.line"

	line_pay = fields.Many2one('account.move.line', string='line Invoice')
	inv_id = fields.Many2one('account.move', string='Invoice')
	processed  = fields.Boolean(
		string='Procesado',
		required=False)

	@api.depends('ref', 'move_id')
	def name_get(self):
		super().name_get()
		result = []
		for line in self:
			if self._context.get('show_number', False):
				name = '%s - %s' %(line.move_id.name, abs(line.amount_residual_currency or line.amount_residual))
				result.append((line.id, name))
			elif line.ref:
				result.append((line.id, (line.move_id.name or '') + '(' + line.ref + ')'))
			else:
				result.append((line.id, line.move_id.name))
		return result

	@api.ondelete(at_uninstall=False)
	def _prevent_automatic_line_deletion(self):
		if not self.env.context.get('dynamic_unlink'):
			for line in self:
				#if line.display_type == 'tax' and line.move_id.line_ids.tax_ids:
				#	raise ValidationError(_(
				#		"You cannot delete a tax line as it would impact the tax report"
				#	))
				if line.display_type == 'payment_term':
					raise ValidationError(_(
						"You cannot delete a payable/receivable line as it would not be consistent "
						"with the payment terms"
					))

