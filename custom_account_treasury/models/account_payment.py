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

import logging

_logger = logging.getLogger(__name__)

class AccountPayment(models.Model):
	_inherit = 'account.payment'

	@api.depends('payment_line_ids.invoice_id')
	def _compute_domain_move_line(self):
		for pay in self:
			invoices = pay.mapped('payment_line_ids.invoice_id')
			pay.domain_move_lines = [(6,0,invoices.ids)]

	@api.depends('payment_line_ids.move_line_id')
	def _compute_domain_accountmove_line(self):
		for pay in self:
			invoices = pay.mapped('payment_line_ids.move_line_id')
			pay.domain_account_move_lines = [(6,0,invoices.ids)]


	move_diff_ids = fields.Many2many('account.move', 'account_move_payment_rel_ids', 'move_id', 'payment_id', copy=False)
	payment_line_ids = fields.One2many('account.payment.detail', 'payment_id', copy=False, string="Detalle de pago", help="detalle de pago")
	currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        compute='_compute_currency_id', store=True, readonly=False, precompute=True, default=lambda self: self.env.company.currency_id,
        help="The payment's currency.")
	destination_account_id = fields.Many2one(
		comodel_name='account.account',
		string='Destination Account',
		store=True, readonly=False,
		compute='_compute_destination_account_id',
		domain="[('account_type', 'in', ('asset_receivable', 'liability_payable')), ('company_id', '=', company_id)]",
		check_company=True)
	change_destination_account = fields.Char(string="cambio de cuenta destino")

	invoice_cash_rounding_id = fields.Many2one(
		comodel_name='account.cash.rounding',
		string='Cash Rounding Method',
		readonly=True,
		states={'draft': [('readonly', False)]},
		help='Defines the smallest coinage of the currency that can be used to pay by cash.',
	)

	company_currency_id = fields.Many2one('res.currency', string="Moneda de la compañia",
		required=True, default=lambda self: self.env.company.currency_id)

	# === Buscar Documentos fields === #
	customer_invoice_ids = fields.Many2many("account.move", "customer_invoice_payment_rel", 'invoice_id', 'payment_id',
		string="Buscar Documentos Clientes", domain="[('state','!=','draft')]")
	supplier_invoice_ids = fields.Many2many("account.move", "supplier_invoice_payment_rel", 'invoice_id', 'payment_id',
		string="Buscar Documentos Proveedores", domain="[('state','!=','draft')]")
	account_move_payment_ids = fields.Many2many("account.move.line", "account_move_payment_rel", 'moe_line_id','payment_id',
		string="Buscar Otros Documentos", domain="[('amount_residual','!=', 0),('parent_state','!=','draft'),('account_id.account_type', 'in', ['asset_receivable', 'liability_payable'])]")
	
	invoice_id = fields.Many2one(
		comodel_name='account.move',
		string='Factura',
		required=False)

	# === Filtrar Documentos fields === #
	domain_account_move_lines = fields.Many2many("account.move.line", 'domain_account_move_line_pay_rel', string="restriccion de campos", compute="_compute_domain_accountmove_line")
	domain_move_lines = fields.Many2many("account.move", 'domain_move_line_pay_rel', string="restriccion de campos", compute="_compute_domain_move_line")


	# === advance fields === #
	advance_type_id = fields.Many2one('advance.type', string="Tipo de anticipo")
	advance = fields.Boolean('Anticipo', default=False)
	code_advance = fields.Char(string="Número de anticipo", copy=False)
	partner_type = fields.Selection(selection_add=[
		('employee', 'Empleado'),
	], ondelete={'employee': 'set default'})

	# === writeoff fields === #
	writeoff_account_id = fields.Many2one('account.account', string="Cuenta de diferencia", copy=False,
		domain="[('deprecated', '=', False), ('company_id', '=', company_id)]")
	writeoff_label = fields.Char(string='Journal Item Label', default='Diferencia',
		help='Change label of the counterpart that will hold the payment difference')
	payment_difference_line = fields.Monetary(string="Diferencia de pago",
		store=True, readonly=True,
		tracking=True)
	def open_reconcile_view(self):
		return self.move_id.line_ids.open_reconcile_view()

	@api.depends('journal_id')
	def _compute_currency_id(self):
		for pay in self:
			pay.currency_id = pay.journal_id.currency_id or pay.journal_id.company_id.currency_id or self.env.company.currency_id.id


	@api.onchange('payment_line_ids','payment_line_ids.tax_ids')
	def _onchange_matched_manual_ids(self, force_update = False):
		in_draft_mode = self != self._origin
		
		def need_update():
			amount = 0
			for line in self.payment_line_ids:
				if line.auto_tax_line:
					amount -= line.balance
					continue
				if line.tax_ids:
					balance_taxes_res = line.tax_ids._origin.compute_all(
						line.invoice_id.amount_untaxed  or line.payment_amount or line.balance,
						currency=line.currency_id,
						quantity=1,
						product=line.product_id,
						partner=line.partner_id,
						is_refund=False,
						handle_price_include=True,
					)
					for tax_res in balance_taxes_res.get("taxes"):
						amount += tax_res['amount']
			return amount 
		
		if not force_update and not need_update():
			return
		
		to_remove = self.env['account.payment.detail']		
		if self.payment_line_ids:
			for line in list(self.payment_line_ids):
				print(line, line.auto_tax_line)
				if line.auto_tax_line:
					to_remove += line
					continue
				if line.tax_ids:
					balance_taxes_res = line.tax_ids._origin.compute_all(
						line.invoice_id.amount_untaxed or line.payment_amount or line.balance,
						currency=line.currency_id,
						quantity=1,
						product=line.product_id,
						partner=line.partner_id,
						is_refund=False,
						handle_price_include=True,
					)
					for tax_res in balance_taxes_res.get("taxes"):
						create_method = in_draft_mode and line.new or line.create
						create_method({
							'payment_id' : self.id,
							'partner_id' : line.partner_id.id,
							'account_id' : tax_res['account_id'],
							'name' : tax_res['name'],
							'payment_amount' : tax_res['amount'],
							'tax_repartition_line_id' : tax_res['tax_repartition_line_id'],
							'tax_tag_ids' : tax_res['tag_ids'],
							'auto_tax_line' : True,
							'tax_line_id2' :tax_res['id'],
							'tax_base_amount' : line.invoice_id.amount_untaxed or line.payment_amount or line.balance,
							'tax_line_id' : line.id,
							})
			
			if in_draft_mode:
				self.payment_line_ids -=to_remove
			else:
				to_remove.unlink()

	def _prepare_move_line_default_vals(self, write_off_line_vals=None):
		res = super(AccountPayment, self)._prepare_move_line_default_vals(
			write_off_line_vals
		)
		new_aml_lines = []
		for line in self.payment_line_ids.filtered(lambda x: not float_is_zero(x.amount_currency, precision_digits=self.currency_id.decimal_places)):
			# Fully Paid line
			new_aml_lines.append(
				{
					'debit': line.debit,
					'credit': line.credit,
					'balance': line.debit - line.credit,
					'amount_currency': line.amount_currency if line.amount_currency != 0.0 else (line.debit - line.credit),
					'journal_id': self.journal_id.id,
					'account_id': line.account_id.id,
					'analytic_distribution': line.analytic_distribution or False,
					'tax_ids': [(6, 0, line.tax_ids.ids)],
					'tax_tag_ids': [(6, 0, line.tax_tag_ids.ids)],
					'tax_repartition_line_id': line.tax_repartition_line_id.id,
					'tax_base_amount': line.tax_base_amount,
					'inv_id': line.invoice_id.id,
					'line_pay': line.move_line_id.id,
					"date_maturity": self.date,
					"partner_id": line.partner_id.commercial_partner_id.id,
					"currency_id": line.payment_id.currency_id.id,
					"payment_id": self.id,
					#**line._get_counterpart_move_line_vals() 
				}
			)
		if len(res) >= 2 and new_aml_lines:
			res.pop(1)
			res += new_aml_lines
		return res




	
	# def _prepare_move_line_default_vals(self, write_off_line_vals=None): 
	# 	res = super(AccountPayment, self)._prepare_move_line_default_vals(write_off_line_vals)
	# 	#res[0].update({'is_main': True})
	# 	new_aml_lines = []
		
	# 	for line in self.payment_line_ids:
	# 		new_aml_lines.append(
	# 			{
	# 				'debit': line.debit,
	# 				'credit': line.credit,
	# 				'balance': line.debit - line.credit,
	# 				'amount_currency': line.amount_currency if line.amount_currency != 0.0 else (line.debit - line.credit),
	# 				'journal_id': self.journal_id.id,
	# 				'account_id': line.account_id.id,
	# 				'analytic_distribution': line.analytic_distribution or False,
	# 				'tax_ids': [(6, 0, line.tax_ids.ids)],
	# 				'tax_tag_ids': [(6, 0, line.tax_tag_ids.ids)],
	# 				'tax_repartition_line_id': line.tax_repartition_line_id.id,
	# 				'tax_base_amount': line.tax_base_amount,
	# 				'inv_id': line.invoice_id.id,
	# 				'line_pay': line.move_line_id.id,
	# 				"date_maturity": self.date,
	# 				"partner_id": line.partner_id.commercial_partner_id.id,
	# 				"currency_id": line.payment_id.currency_id.id,
	# 				"payment_id": self.id,
	# 				#'to_pay': line.to_pay,
	# 				#"payment_detail_id": line.id,
	# 				**line._get_counterpart_move_line_vals() 
	# 			}
	# 		)
		
	# 	if self.payment_line_ids:
	# 		res = new_aml_lines
			
	# 	return res

	@api.onchange('advance_type_id')
	def _onchange_advance_type_id(self):
		self._onchange_payment_type()

	@api.onchange('advance')
	def _onchange_advance(self):
		res = {}
		if not self.reconciled_invoice_ids:
			if self.payment_type == 'transfer':
				self.advance = False
				self.advance_type_id = False
			elif not self.advance:
				self.advance_type_id = False
		if self.advance:
			self.advance_type_id = False
			res['domain'] = {'advance_type_id': [('internal_type','=', self.payment_type == 'outbound' and 'asset_receivable' or 'liability_payable')]}
		return res

	def action_post(self):
		for rec in self:
			if not rec.code_advance:
				sequence_code = ''
				if rec.advance:
					if rec.partner_type == 'customer':
						sequence_code = 'account.payment.advance.customer'
					if rec.partner_type == 'supplier':
						sequence_code = 'account.payment.advance.supplier'
					if rec.partner_type == 'employee':
						sequence_code = 'account.payment.advance.employee'

				rec.code_advance = self.env['ir.sequence'].with_context(ir_sequence_date=rec.date).next_by_code(sequence_code)
				if not rec.code_advance and rec.advance:
					raise UserError(_("You have to define a sequence for %s in your company.") % (sequence_code,))
			if not rec.name:
				if rec.partner_type == 'employee':
					sequence_code = 'account.payment.employee'
					rec.name = self.env['ir.sequence'].with_context(ir_sequence_date=rec.date).next_by_code(sequence_code)
					if not rec.name:
						raise UserError(_("You have to define a sequence for %s in your company.") % (sequence_code,))
			if rec.payment_line_ids and rec.payment_type != 'transfer':
				amount = rec.amount * (rec.payment_type in ('outbound', 'transfer') and 1 or -1)
				rec._create_payment_entry_line(rec.move_id)
				super().action_post()
				for line in rec.line_ids:
					invoice_line = line.line_pay
					if line and invoice_line:
						# Comprobar que la línea de factura y la línea de pago coinciden en cuenta y partner
						if (invoice_line.account_id == line.account_id and
							invoice_line.partner_id == line.partner_id and
							not invoice_line.reconciled):
							# Conciliar la línea de movimiento específica con la línea de factura
							(line + invoice_line).with_context(skip_account_move_synchronization=True).reconcile()
			else:
				super(AccountPayment, rec).action_post()
		return True

	##### END advance

	@api.onchange('payment_type')
	def _onchange_payment_type(self):
		self.change_destination_account = None

	@api.onchange('reconciled_invoice_ids', 'payment_type', 'partner_type', 'partner_id', 'journal_id', 'destination_account_id')
	def _change_destination_account(self):
		change_destination_account = '0'
		account_id = None
		partner = self.partner_id.with_context(company_id=self.company_id.id)
		if self.reconciled_invoice_ids:
			self.change_destination_account = self.reconciled_invoice_ids[0].account_id.id
			return
		elif self.payment_type == 'transfer':
			self._onchange_amount()
			if not self.company_id.transfer_account_id.id:
				raise UserError(_('There is no Transfer Account defined in the accounting settings. Please define one to be able to confirm this transfer.'))
			account_id = self.company_id.transfer_account_id.id
		elif self.partner_id:
			if self.partner_type == 'customer':
				account_id = partner.property_account_receivable_id.id
			else:
				account_id = partner.property_account_payable_id.id
		elif self.partner_type == 'customer':
			default_account = partner.property_account_receivable_id
			account_id = default_account.id
		elif self.partner_type == 'supplier':
			default_account = partner.property_account_payable_id
			account_id = default_account.id
		if self.destination_account_id.id != account_id:
			change_destination_account = self.destination_account_id.id
		self.change_destination_account = change_destination_account

	@api.depends('journal_id','partner_id','is_internal_transfer','reconciled_invoice_ids','journal_id','payment_type', 'partner_type', 'partner_id', 'change_destination_account', 'advance_type_id')
	def _compute_destination_account_id(self):
		for val in self:
			if val.change_destination_account not in (False,'0') :
				val.destination_account_id = int(val.change_destination_account)
			if val.advance_type_id:
				val.destination_account_id = val.advance_type_id.account_id.id
			else:
				super(AccountPayment, self)._compute_destination_account_id()
			if val.partner_type == 'employee':
				val.destination_account_id = int(val.change_destination_account)

	def _get_liquidity_move_line_vals(self, amount):
		res = super(AccountPayment, self)._get_liquidity_move_line_vals(amount)
		res.update(
			account_id = self.outstanding_account_id  and self.outstanding_account_id .id or res.get('account_id'),
			name = self.advance and self.code_advance or res.get('name')
			)
		return res

	def button_journal_difference_entries(self):
		return {
			'name': _('Diarios'),
			'view_type': 'form',
			'view_mode': 'tree,form',
			'res_model': 'account.move',
			'view_id': False,
			'type': 'ir.actions.act_window',
			'domain': [('id', 'in', self.move_diff_ids.ids)],
		}

	### END manual account ###
	def _compute_payment_difference_line(self):
		for val in self:
			amount = 0.0
			if val.payment_type != 'transfer':
				for line in val.payment_line_ids:
					sign = 1.0
					if not line.is_counterpart and not line.is_account_line and not line.is_manual_currency and not line.is_diff:
						if line.move_line_id and line.balance < 0:
							sign = -1.0
						amount += (line.payment_amount * sign)
					if line.is_account_line or line.is_counterpart:
						# Agrega una verificación de condición basada en el saldo del movimiento (line.balance)
						if line.balance < 0:
							amount -= abs(line.payment_amount * sign) or val.amount
						else:
							amount += (line.payment_amount * sign) or val.amount

				if val.payment_type == 'outbound':
					amount *= -1.0

			val.payment_difference_line = val.currency_id.round(amount)

	@api.onchange('currency_id')
	def _onchange_currency(self):
		for line in self.payment_line_ids:
			line.payment_currency_id = self.currency_id.id or False
			line._onchange_to_pay()
			line._onchange_payment_amount()
	@api.returns('self', lambda value: value.id)
	def copy(self, default=None):
		default = dict(default or {})
		default.update(payment_line_ids=[])
		return super(AccountPayment, self).copy(default)

	@api.onchange('account_move_payment_ids', 'customer_invoice_ids', 'supplier_invoice_ids')
	def _onchange_invoice_field(self):
		fields_to_check = ['account_move_payment_ids', 'customer_invoice_ids', 'supplier_invoice_ids']

		for field_name in fields_to_check:
			field_ids = self[field_name]
			if field_ids:
				if field_name == "account_move_payment_ids":
					where_clause = "account_move_line.amount_residual != 0 AND ac.reconcile AND account_move_line.id in %s"
				else:  # Para 'customer_invoice_ids' y 'supplier_invoice_ids'
					where_clause = "account_move_line.amount_residual != 0 AND ac.reconcile AND am.id in %s"
					
				where_params = [tuple(field_ids.ids)]
				
				self._cr.execute('''
				SELECT account_move_line.id
				FROM account_move_line
				LEFT JOIN account_move am ON (account_move_line.move_id = am.id)
				LEFT JOIN account_account ac ON (account_move_line.account_id = ac.id)
				WHERE ''' + where_clause, where_params
				)
				
				res = self._cr.fetchall()
				
				if res:
					for r in res:
						moves = self.env['account.move.line'].browse(r)
						self._change_and_add_payment_detail(moves)
				
				self[field_name] = None
				break

	def _change_and_add_payment_detail(self, moves):
		SelectPaymentLine = self.env['account.payment.detail']
		current_payment_lines = self.payment_line_ids.filtered(lambda line: line.is_main == False)
		move_lines = moves - current_payment_lines.mapped('move_line_id')
		payment_lines_to_create = []
		for line in move_lines:
			data = self._get_data_move_lines_payment(line)
			pay = SelectPaymentLine.new(data)
			pay._onchange_move_lines()
			pay._onchange_to_pay()
			pay._onchange_payment_amount()
			values_to_create = pay._convert_to_write(pay._cache)
			payment_lines_to_create.append(values_to_create)
		# Crear todas las líneas de pago en una sola operación en la base de datos
		SelectPaymentLine.create(payment_lines_to_create)

	def _get_data_move_lines_payment(self, line):
		data = {
			'move_line_id': line.id,
			'account_id': line.account_id.id,
			'analytic_distribution' : line.analytic_distribution and line.analytic_distribution or False,
			'tax_ids' : [(6, 0, line.tax_ids.ids)],
			'tax_repartition_line_id' : line.tax_repartition_line_id.id,
			'tax_base_amount': line.tax_base_amount,
			'tax_tag_ids' : [(6, 0, line.tax_tag_ids.ids)],
			'payment_id': self.id,
			'payment_currency_id': self.currency_id.id,
			'payment_difference_handling': 'open',
			'writeoff_account_id': False,
			'to_pay': True
			}
		return data


	@api.onchange('currency_id')
	def _onchange_payment_amount_currency(self):
		self.writeoff_account_id = self._get_account_diff_currency(self.payment_difference_line)
		self._recompute_dynamic_lines_payment()

	def _get_account_diff_currency(self, amount):
		account = False
		company = self.env.company
		account = amount > 0 and company.expense_currency_exchange_account_id 
		if not account:
			account = company.income_currency_exchange_account_id
		return account

	@api.onchange('date')
	def _onchange_payment_date(self):
		for line in self.payment_line_ids.filtered(lambda line: line.is_main == False):
			line._onchange_to_pay()
			line._onchange_payment_amount()
			line._compute_payment_difference()
			line._compute_debit_credit_balance()
		self._recompute_dynamic_lines_payment()

	@api.onchange('payment_line_ids', 'outstanding_account_id','payment_type', 'destination_account_id','amount','journal_id','currency_id')
	def _onchange_recompute_dynamic_line(self):
		self._recompute_dynamic_lines_payment()

	def _recompute_dynamic_lines_payment(self):
		"""La primera línea del método, self.ensure_one(), asegura que el objeto de pago esté en modo de solo lectura. Esto garantiza que el método no realice cambios no deseados en el objeto de pago.
			amount = self.amount * (self.payment_type in ('outbound', 'transfer') and 1 or -1), calcula la cantidad del pago que debe asignarse a la cuenta de efectivo del activo.
			self._onchange_accounts(-amount, account_id=self.outstanding_account_id , display_type='asset_cash', is_main=True), crea una línea para la cuenta de efectivo del activo.
			if self.payment_type != 'transfer':, comprueba si el tipo de pago es transfer. Si no lo es, el método crea líneas para cualquier entrada manual que se haya realizado en el pago.
			manual_entries_total = sum(line.payment_amount for line in self.payment_line_ids.filtered(lambda l: l.display_type not in ['asset_cash',] and l.is_main == False)), calcula la suma de las cantidades de todas las entradas manuales.
			counter_part_amount = amount - manual_entries_total, calcula la cantidad del pago que debe asignarse a la cuenta contraparte.
			amount_diff = counter_part_amount - amount, calcula la diferencia entre la cantidad del pago que debe asignarse a la cuenta contraparte y la cantidad del pago original.
			display_type = 'counterpart', establece el tipo de visualización de la línea para la cuenta contraparte.
			account_id = self.destination_account_id, establece la cuenta de contrapartida.
			should_compute_difference = (self.payment_type == 'outbound' and amount_diff > 0) or (self.payment_type == 'inbound' and amount_diff < 0), comprueba si la diferencia entre la cantidad del pago que debe asignarse a la cuenta contraparte y la cantidad del pago original es positiva o negativa.
			if should_compute_difference:, crea una línea para la cuenta de diferencia de moneda, si es necesario.
			counter_part_amount = amount - manual_entries_total, actualiza la cantidad de la línea para la cuenta
		"""
		self.ensure_one()
		diff_cash = self.payment_line_ids.filtered(lambda line: line.is_counterpart and line.is_main)
		if len(diff_cash) > 1:
			diff_cash.unlink()
		amount = self.amount * (self.payment_type in ('outbound', 'transfer') and 1 or -1)
		self._onchange_accounts(-amount, account_id=self.outstanding_account_id.id , display_type='asset_cash', is_main=True, is_counterpart=False)
		
		if self.payment_type != 'transfer':
			manual_entries_total = sum(line.balance for line in self.payment_line_ids.filtered(lambda l: l.display_type not in ['asset_cash',] and l.is_main == False))
			counter_part_amount = amount - manual_entries_total
			amount_diff = counter_part_amount - amount
			display_type = 'counterpart'
			account_id = self.destination_account_id
			self._compute_payment_difference_line()
			diif_amount =self.payment_difference_line 
			if (self.payment_type == 'outbound' and diif_amount != 0) or (self.payment_type == 'inbound' and diif_amount != 0):
				account_id =  self.writeoff_account_id
				display_type = 'counterpart'
			counter_part_amount = amount - manual_entries_total
			self._onchange_accounts(counter_part_amount, account_id, display_type=display_type, is_main=True, is_counterpart=True)
		if self.payment_type == 'transfer':
			self._onchange_accounts(amount, account_id=self.destination_account_id.id, is_transfer=True)

	def _onchange_accounts(self, amount, account_id=None, is_transfer=False, display_type=None, is_main=False, is_counterpart=False):
		self.ensure_one()
		in_draft_mode = self != self._origin
		existing_line = is_main and self.payment_line_ids.filtered(lambda line: line.display_type == display_type and line.is_main) or None
		if not account_id or self.currency_id.is_zero(amount):
			if existing_line:
				self.payment_line_ids -= existing_line
			return
		line_values = self._set_fields_detail(amount, account_id, is_transfer, display_type, is_main, is_counterpart)
		
		if existing_line:
			existing_line.update(line_values)
		else:
			if in_draft_mode:
				self.env['account.payment.detail'].new(line_values)
			else:
				self.env['account.payment.detail'].create(line_values)

	def _set_fields_detail(self, total_balance, account, is_transfer, display_type,is_main,is_counterpart):
		line_values = {
			'payment_amount': total_balance,
			'partner_id': self.partner_id.id or False,
			'payment_id': self.id,
			'company_currency_id': self.env.company.currency_id.id,
			'display_type': display_type,
			'is_transfer': is_transfer,
			'is_main': is_main,
			'is_counterpart': is_counterpart,
			'name': self.ref or '/',
			'currency_id': self.currency_id.id,
			'account_id': account,
			'ref': self.name or '/',
			'payment_currency_id': self.currency_id.id,
		}
		company_currency = self.env.company.currency_id
		if self.currency_id and self.currency_id != company_currency:
			amount = company_currency._convert(total_balance, self.currency_id, self.env.company, self.date or fields.Date.today())
			line_values.update({
				'amount_currency': amount
			})
		return line_values


	def _cleanup_lines(self):
		""" 
		Limpiar lineas aplica para evitar errores, comunes dentro del ORM evita:
		--> Si hay más de una línea que cumple el criterio de 'diff_cash', elimínalas todas (Para cuando se vuelva a computar el asiento quede cuadrado)
		---> Encuentra y elimina las líneas con cantidad de pago igual a cero evita crear en la base de datos datos inecesaro
		"""
		diff_cash = self.payment_line_ids.filtered(lambda line: line.display_type != 'asset_cash' and line.is_main)

		# Si hay más de una línea que cumple el criterio de 'diff_cash', elimínalas todas
		if len(diff_cash) > 1:
			diff_cash.unlink()

		# Encuentra y elimina las líneas con cantidad de pago igual a cero
		zero_lines = self.payment_line_ids.filtered(lambda l: self.currency_id.is_zero(l.payment_amount))
		zero_lines.unlink()

	def _is_advance(self):
		return self.advance

	def _get_counterpart_move_line_vals(self, invoice=False):
		res = super(AccountPayment, self)._get_counterpart_move_line_vals(invoice=invoice)
		if self.advance:
			name = ''
			if self.partner_type == 'employee':
				name += _('Employee Payment Advance')
			elif self.partner_type == 'customer':
				name += _('Customer Payment Advance')
			elif self.partner_type == 'supplier':
				name += _('Vendor Payment Advance')
			name += self.code_advance or ''
			res.update(name=name)
		return res

	def _get_shared_move_line_vals(self, line_debit, line_credit, line_amount_currency, move, invoice_id=False):
		""" Returns values common to both move lines (except for debit, credit and amount_currency which are reversed)
		"""
		return {
			'partner_id': self.payment_type in ('inbound', 'outbound') and self.env['res.partner']._find_accounting_partner(self.partner_id).id or False,
			'inv_id': invoice_id and invoice_id.id or False,
			'move_id': move,
			'debit': line_debit,
			'credit': line_credit,
			'amount_currency': line_amount_currency or False,
			'payment_id': self.id,
			'journal_id': self.journal_id.id,
		}
	def _create_payment_entry_line(self, move):
		aml_obj = self.env['account.move.line'].with_context(check_move_validity=False, skip_account_move_synchronization=True)
		self.line_ids.unlink()
		# Usamos una lista de comprensión para construir los diccionarios
		aml_dicts = [{
			'partner_id': self.payment_type in ('inbound', 'outbound') and self.env['res.partner']._find_accounting_partner(self.partner_id).id or False,
			'move_id': move.id,
			'debit': line.debit,
			'credit': line.credit,
			'amount_currency': line.amount_currency if line.amount_currency != 0.0 else line.balance,
			'payment_id': self.id,
			'journal_id': self.journal_id.id,
			'account_id': line.account_id.id,
			'analytic_distribution': line.analytic_distribution or False,
			'tax_ids': [(6, 0, line.tax_ids.ids)],
			'tax_tag_ids': [(6, 0, line.tax_tag_ids.ids)],
			'tax_repartition_line_id': line.tax_repartition_line_id.id,
			'tax_base_amount': line.tax_base_amount,
			'inv_id': line.invoice_id.id,
			'line_pay': line.move_line_id.id,
			**line._get_counterpart_move_line_vals()  # Merging the dictionary directly
		} for line in self.payment_line_ids]

		# Crear entradas de una vez, sin bucle for
		aml_obj.create(aml_dicts)

		return True

	# def _synchronize_to_moves(self, changed_fields):
	# 	''' Update the account.move regarding the modified account.payment.
	# 	:param changed_fields: A list containing all modified fields on account.payment.
	# 	'''
	# 	if self._context.get('skip_account_move_synchronization'):
	# 		return

	# 	if not any(field_name in changed_fields for field_name in self._get_trigger_fields_to_synchronize()):
	# 		return

	# 	for pay in self.with_context(skip_account_move_synchronization=True):
	# 		liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()

	# 		# Make sure to preserve the write-off amount.
	# 		# This allows to create a new payment with custom 'line_ids'.

	# 		write_off_line_vals = []
	# 		if liquidity_lines and counterpart_lines and writeoff_lines:
	# 			write_off_line_vals.append({
	# 				'name': writeoff_lines[0].name,
	# 				'account_id': writeoff_lines[0].account_id.id,
	# 				'partner_id': writeoff_lines[0].partner_id.id,
	# 				'currency_id': writeoff_lines[0].currency_id.id,
	# 				'amount_currency': sum(writeoff_lines.mapped('amount_currency')),
	# 				'balance': sum(writeoff_lines.mapped('balance')),
	# 			})

	# 		line_vals_list = pay._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals)

	# 		line_ids_commands = []

	# 		if hasattr(self, 'payment_line_ids'):
       
	# 			for i, line_vals in enumerate(line_vals_list):
	# 				payment_line = self.payment_line_ids.filtered(lambda line: line.account_id.id == line_vals['account_id'])
	# 				for rec in payment_line:
	# 					if rec:
	# 						line_ids_commands.append(Command.update(rec.id, line_vals))
	# 					else:
	# 						line_ids_commands.append(Command.create(line_vals))
	# 		else:
	# 			line_ids_commands = [
	# 				Command.update(liquidity_lines.id, line_vals_list[0]) if liquidity_lines else Command.create(line_vals_list[0]),
	# 				Command.update(counterpart_lines.id, line_vals_list[1]) if counterpart_lines else Command.create(line_vals_list[1])
	# 			]
	# 		if hasattr(self, 'payment_line_ids'):
	# 			for line in writeoff_lines:
	# 				line_ids_commands.append((2, line.id))

	# 			for extra_line_vals in line_vals_list[2:]:
	# 				line_ids_commands.append((0, 0, extra_line_vals))

	# 		# Update the existing journal items.
	# 		# If dealing with multiple write-off lines, they are dropped and a new one is generated.

	# 		pay.move_id\
	# 			.with_context(skip_invoice_sync=True)\
	# 			.write({
	# 				'partner_id': pay.partner_id.id,
	# 				'currency_id': pay.currency_id.id,
	# 				'partner_bank_id': pay.partner_bank_id.id,
	# 				'line_ids': line_ids_commands,
	# 			})



	def _synchronize_from_moves(self, changed_fields):
		''' Update the account.payment regarding its related account.move.
		Also, check both models are still consistent.
		:param changed_fields: A set containing all modified fields on account.move.
		'''
		if self._context.get('skip_account_move_synchronization'):
			return

		for pay in self.with_context(skip_account_move_synchronization=True):

			# After the migration to 14.0, the journal entry could be shared between the account.payment and the
			# account.bank.statement.line. In that case, the synchronization will only be made with the statement line.
			if pay.move_id.statement_line_id:
				continue

			move = pay.move_id
			move_vals_to_write = {}
			payment_vals_to_write = {}

			if 'journal_id' in changed_fields:
				if pay.journal_id.type not in ('bank', 'cash'):
					raise UserError(_("A payment must always belongs to a bank or cash journal."))

			if 'line_ids' in changed_fields:
				all_lines = move.line_ids
				liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()

				# if len(liquidity_lines) != 1:
				# 	raise UserError(_(
				# 		"Journal Entry %s is not valid. In order to proceed, the journal items must "
				# 		"include one and only one outstanding payments/receipts account.",
				# 		move.display_name,
				# 	))

				# if len(counterpart_lines) != 1:
				# 	raise UserError(_(
				# 		"Journal Entry %s is not valid. In order to proceed, the journal items must "
				# 		"include one and only one receivable/payable account (with an exception of "
				# 		"internal transfers).",
				# 		move.display_name,
				# 	))

				if any(line.currency_id != all_lines[0].currency_id for line in all_lines):
					raise UserError(_(
						"Journal Entry %s is not valid. In order to proceed, the journal items must "
						"share the same currency.",
						move.display_name,
					))

				# if any(line.partner_id != all_lines[0].partner_id for line in all_lines):
				# 	raise UserError(_(
				# 		"Journal Entry %s is not valid. In order to proceed, the journal items must "
				# 		"share the same partner.",
				# 		move.display_name,
				# 	))
				for counterpart_line in counterpart_lines:
					if counterpart_line.account_id.account_type == 'asset_receivable':
						partner_type = 'customer'
					else:
						partner_type = 'supplier'
					for line in liquidity_lines:
						liquidity_amount = line.amount_currency
						liquidity_amount = liquidity_lines.amount_currency
						move_vals_to_write.update({
							'currency_id': line.currency_id.id or self.currency_id.id,
							'partner_id': line.partner_id.id,
						})
						payment_vals_to_write.update({
							'amount': abs(liquidity_amount),
							'partner_type': partner_type,
							'currency_id': line.currency_id.id or self.currency_id.id,
							'destination_account_id': counterpart_line.account_id.id,
							'partner_id': line.partner_id.id,
						})
						if liquidity_amount > 0.0:
							payment_vals_to_write.update({'payment_type': 'inbound'})
						elif liquidity_amount < 0.0:
							payment_vals_to_write.update({'payment_type': 'outbound'})

					move.write(move._cleanup_write_orm_values(move, move_vals_to_write))
					pay.write(move._cleanup_write_orm_values(pay, payment_vals_to_write))


class ResPartner(models.Model):
	_inherit = 'res.partner'

	def _find_accounting_partner(self, partner):
		''' Find the partner for which the accounting entries will be created '''
		return partner.commercial_partner_id
