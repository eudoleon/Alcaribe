from odoo import models, fields, api, _,Command
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class AccountPayment(models.Model):
	_inherit = 'account.payment'

	@api.depends('payment_lines.invoice_id')
	def _compute_domain_move_line(self):
		for pay in self:
			invoices = pay.mapped('payment_lines.invoice_id')
			pay.domain_move_lines = [(6,0,invoices.ids)]

	@api.depends('payment_lines.move_line_id')
	def _compute_domain_accountmove_line(self):
		for pay in self:
			invoices = pay.mapped('payment_lines.move_line_id')
			pay.domain_account_move_lines = [(6,0,invoices.ids)]


	move_diff_ids = fields.Many2many('account.move', 'account_move_payment_rel_ids', 'move_id', 'payment_id', copy=False)
	payment_line_ids = fields.One2many('account.payment.detail', 'payment_id', copy=False,
		string="Detalle de pago", help="detalle de pago")
	payment_lines = fields.One2many('account.payment.detail', 'payment_id', copy=False,
		domain=[('exclude_from_payment_detail', '=', False)], string="Documentos", help="detalle de pago y/o cobro")
	account_id = fields.Many2one(
		comodel_name='account.account',
		string='Cuenta de origen',
		store=True, readonly=False,
		compute='_compute_destination_account_id',
		domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
		check_company=True)
	destination_account_id = fields.Many2one(
		comodel_name='account.account',
		string='Destination Account',
		store=True, readonly=False,
		compute='_compute_destination_account_id',
		domain="[('user_type_id.type', 'in', ('receivable', 'payable')), ('company_id', '=', company_id)]",
		check_company=True)
	change_destination_account = fields.Char(string="cambio de cuenta destino")

	company_currency_id = fields.Many2one('res.currency', string="Moneda de la compañia",
		required=True, default=lambda self: self.env.company.currency_id)

	customer_invoice_ids = fields.Many2many("account.move", "customer_invoice_payment_rel", 'invoice_id', 'payment_id',
		string="Buscar Documentos Clientes", domain="[('state','!=','draft')]")
	supplier_invoice_ids = fields.Many2many("account.move", "supplier_invoice_payment_rel", 'invoice_id', 'payment_id',
		string="Buscar Documentos Proveedores", domain="[('state','!=','draft')]")
	account_move_payment_ids = fields.Many2many("account.move.line", "account_move_payment_rel", 'moe_line_id','payment_id',
		string="Buscar Otros Documentos", domain="[('amount_residual','!=', 0),('parent_state','!=','draft'),('account_id.internal_type', 'in',['payable','receivable']),('id','not in',domain_move_lines)]")
	debts_to_pay_ids = fields.One2many(comodel_name="account.move", inverse_name="pay_id",string="Cuentas por cobrar")
	supplier_to_pay_ids = fields.One2many(comodel_name="account.move", inverse_name="payment_id", string="Cuentas por pagar")
	estado_cuenta_ids = fields.Many2many("account.move.line", "account_move_activos_rel", 'moe_line_id','payment_id',string="Buscar Otros Documentos", domain="[('parent_state','!=','draft'),('amount_residual','!=', 0)]")
	invoice_id = fields.Many2one(
		comodel_name='account.move',
		string='Factura',
		required=False)

	process_prepaid = fields.Boolean(
		string='Procesar Anticipo',
		required=False)
	processed  = fields.Boolean(
		string='Procesado',
		required=False)
	domain_account_move_lines = fields.Many2many("account.move.line", 'domain_account_move_line_pay_rel', string="restriccion de campos", compute="_compute_domain_accountmove_line")
	domain_move_lines = fields.Many2many("account.move", 'domain_move_line_pay_rel', string="restriccion de campos", compute="_compute_domain_move_line")
	payment_method_line_id = fields.Many2one('account.payment.method.line', string='Payment Method',
		readonly=False, store=True, copy=False,
		compute='_compute_payment_method_line_id',
		domain="[('id', 'in', available_payment_method_line_ids)]",
		help="Manual: Pay or Get paid by any method outside of Odoo.\n"
		"Payment Acquirers: Each payment acquirer has its own Payment Method. Request a transaction on/to a card thanks to a payment token saved by the partner when buying or subscribing online.\n"
		"Check: Pay bills by check and print it from Odoo.\n"
		"Batch Deposit: Collect several customer checks at once generating and submitting a batch deposit to your bank. Module account_batch_payment is necessary.\n"
		"SEPA Credit Transfer: Pay in the SEPA zone by submitting a SEPA Credit Transfer file to your bank. Module account_sepa is necessary.\n"
		"SEPA Direct Debit: Get paid in the SEPA zone thanks to a mandate your partner will have granted to you. Module account_sepa is necessary.\n")
	payment_difference_line = fields.Monetary(string="Diferencia de pago",
		store=True, readonly=True,
		compute="_compute_payment_difference_line", 
		tracking=True)
	payment_date = fields.Date(tracking=True)
	account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account')
	# advane
	advance_type_id = fields.Many2one('advance.type', string="Tipo de anticipo")
	advance = fields.Boolean('Anticipo', default=False)
	code_advance = fields.Char(string="Número de anticipo", copy=False)
	partner_type = fields.Selection(selection_add=[
		('employee', 'Empleado'),
	], ondelete={'employee': 'set default'})
	writeoff_account_id = fields.Many2one('account.account', string="Cuenta de diferencia", copy=False,
		domain="[('deprecated', '=', False), ('company_id', '=', company_id)]")
	writeoff_label = fields.Char(string='Journal Item Label', default='Write-Off',
		help='Change label of the counterpart that will hold the payment difference')

	def open_reconcile_view(self):
		return self.move_id.line_ids.open_reconcile_view()
    
	@api.onchange('journal_id','partner_id', 'payment_type', 'payment_method_line_id')
	def _compute_outstanding_account_treasury_id(self):
		for pay in self:
			if pay.payment_type == 'inbound': 
				pay.account_id = (pay.payment_method_line_id.payment_account_id.id or pay.journal_id.company_id.account_journal_payment_debit_account_id.id)
			elif pay.payment_type in 'outbound':
				pay.account_id = (pay.payment_method_line_id.payment_account_id.id or pay.journal_id.company_id.account_journal_payment_credit_account_id.id)
			else:
				pay.account_id = False

	@api.onchange('payment_line_ids','payment_line_ids.tax_ids','payment_lines','payment_lines.tax_ids')
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
    
	@api.depends('available_payment_method_line_ids')
	def _compute_payment_method_line_id(self):
		''' Compute the 'payment_method_line_id' field.
		This field is not computed in '_compute_payment_method_line_fields' because it's a stored editable one.
		'''
		for pay in self:
			available_payment_method_lines = pay.available_payment_method_line_ids

			# Select the first available one by default.
			if pay.payment_method_line_id in available_payment_method_lines:
				pay.payment_method_line_id = pay.payment_method_line_id
			elif available_payment_method_lines:
				pay.payment_method_line_id = available_payment_method_lines[0]._origin
			else:
				pay.payment_method_line_id = False

	def _prepare_move_line_default_vals(self, write_off_line_vals=None):
		''' Prepare the dictionary to create the default account.move.lines for the current payment.
		:param write_off_line_vals: Optional dictionary to create a write-off account.move.line easily containing:
			* amount:	   The amount to be added to the counterpart amount.
			* name:		 The label to set on the line.
			* account_id:   The account on which create the write-off.
		:return: A list of python dictionary to be passed to the account.move.line's 'create' method.
		'''
		self.ensure_one()
		write_off_line_vals = write_off_line_vals or {}

		if not self.payment_method_line_id.payment_account_id:
			raise UserError(_(
				"You can't create a new payment without an outstanding payments/receipts account set on the %s journal.",
				self.journal_id.display_name))

		# Compute amounts.
		write_off_amount_currency = write_off_line_vals.get('amount', 0.0)

		if self.payment_type == 'inbound':
			# Receive money.
			liquidity_amount_currency = self.amount
		elif self.payment_type == 'outbound':
			# Send money.
			liquidity_amount_currency = -self.amount
			write_off_amount_currency *= -1
		else:
			liquidity_amount_currency = write_off_amount_currency = 0.0

		write_off_balance = self.currency_id._convert(
			write_off_amount_currency,
			self.company_id.currency_id,
			self.company_id,
			self.date,
		)
		liquidity_balance = self.currency_id._convert(
			liquidity_amount_currency,
			self.company_id.currency_id,
			self.company_id,
			self.date,
		)
		counterpart_amount_currency = -liquidity_amount_currency - write_off_amount_currency
		counterpart_balance = -liquidity_balance - write_off_balance
		currency_id = self.currency_id.id

		if self.is_internal_transfer:
			if self.payment_type == 'inbound':
				liquidity_line_name = _('Transfer to %s', self.journal_id.name)
			else: # payment.payment_type == 'outbound':
				liquidity_line_name = _('Transfer from %s', self.journal_id.name)
		else:
			liquidity_line_name = self.payment_reference

		# Compute a default label to set on the journal items.

		payment_display_name = {
			'outbound-customer': _("Customer Reimbursement"),
			'inbound-customer': _("Customer Payment"),
			'outbound-supplier': _("Vendor Payment"),
			'inbound-supplier': _("Vendor Reimbursement"),
			'outbound-employee': _("Employee Payment"),
			'inbound-employee': _("Employee Reimbursement"),
		}

		default_line_name = self.env['account.move.line']._get_default_line_name(
			_("Internal Transfer") if self.is_internal_transfer else payment_display_name['%s-%s' % (self.payment_type, self.partner_type)],
			self.amount,
			self.currency_id,
			self.date,
			partner=self.partner_id,
		)
		line_vals_list = [
			# Liquidity line.
			{
				'name': liquidity_line_name or default_line_name,
				'date_maturity': self.date,
				'amount_currency': liquidity_amount_currency,
				'currency_id': currency_id,
				'debit': liquidity_balance if liquidity_balance > 0.0 else 0.0,
				'credit': -liquidity_balance if liquidity_balance < 0.0 else 0.0,
				'partner_id': self.partner_id.id,
				'account_id': self.payment_method_line_id.payment_account_id.id if liquidity_balance < 0.0 else self.payment_method_line_id.payment_account_id.id or self.journal_id.company_id.account_journal_payment_debit_account_id.id,
			},
			# Receivable / Payable.
			{
				'name': self.payment_reference or default_line_name,
				'date_maturity': self.date,
				'amount_currency': counterpart_amount_currency,
				'currency_id': currency_id,
				'debit': counterpart_balance if counterpart_balance > 0.0 else 0.0,
				'credit': -counterpart_balance if counterpart_balance < 0.0 else 0.0,
				'partner_id': self.partner_id.id,
				'account_id': self.destination_account_id.id,
			},
		]
		if not self.currency_id.is_zero(write_off_amount_currency):
			# Write-off line.
			line_vals_list.append({
				'name': write_off_line_vals.get('name') or default_line_name,
				'amount_currency': write_off_amount_currency,
				'currency_id': currency_id,
				'debit': write_off_balance if write_off_balance > 0.0 else 0.0,
				'credit': -write_off_balance if write_off_balance < 0.0 else 0.0,
				'partner_id': self.partner_id.id,
				'account_id': write_off_line_vals.get('account_id'),
			})
		return line_vals_list

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
			res['domain'] = {'advance_type_id': [('internal_type','=', self.payment_type == 'outbound' and 'receivable' or 'payable')]}
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
			if self.payment_line_ids and self.payment_type != 'transfer':
				amount = rec.amount * (rec.payment_type in ('outbound', 'transfer') and 1 or -1)
				self._create_payment_entry_line(rec.move_id)
				super().action_post()
				for line in self.line_ids:
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
	@api.onchange('journal_id', 'payment_type')
	def _onchange_account_id(self):
		account = self._compute_destination_account_id()
		self.account_id = account

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
			# Esta comentado porque no corresponde al modulo
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
			account = val.payment_method_line_id.payment_account_id.id or val.journal_id.company_id.account_journal_payment_debit_account_id.id
			if account:
				val.account_id = account
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
			account_id = self.account_id and self.account_id.id or res.get('account_id'),
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

	@api.depends('payment_line_ids.balance', 'amount')
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

	@api.onchange('account_move_payment_ids')
	def _onchange_account_move_payment_ids(self):
		if self.account_move_payment_ids:
			where_clause = "account_move_line.amount_residual != 0 AND ac.reconcile AND account_move_line.id in %s"
			where_params = [tuple(self.account_move_payment_ids.ids)]
			self._cr.execute('''
			SELECT account_move_line.id
			FROM account_move_line
			LEFT JOIN account_account ac ON (account_move_line.account_id = ac.id)
			WHERE ''' + where_clause, where_params
			)
			res = self._cr.fetchall()
			if res:
				for r in res:
					moves = self.env['account.move.line'].browse(r)
					self._change_and_add_payment_detail(moves)
		self.account_move_payment_ids = None


	@api.onchange('customer_invoice_ids')
	def _onchange_customer_invoice_ids(self):
		if self.customer_invoice_ids:
			where_clause = "account_move_line.amount_residual != 0 AND ac.reconcile AND am.id in %s"
			where_params = [tuple(self.customer_invoice_ids.ids)]
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
		self.customer_invoice_ids = None

	@api.onchange('supplier_invoice_ids')
	def _onchange_supplier_invoice_ids(self):
		if self.supplier_invoice_ids:
			where_clause = "account_move_line.amount_residual != 0 AND ac.reconcile AND am.id in %s"
			where_params = [tuple(self.supplier_invoice_ids.ids)]
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
		self.supplier_invoice_ids = None

	def _change_and_add_payment_detail(self, moves):
		SelectPaymentLine = self.env['account.payment.detail']
		current_payment_lines = self.payment_line_ids.filtered(lambda line: not line.exclude_from_payment_detail)
		move_lines = moves - current_payment_lines.mapped('move_line_id')
		other_lines = self.payment_line_ids - current_payment_lines
		self.payment_line_ids = other_lines + self.payment_lines
		for line in move_lines:
			data = self._get_data_move_lines_payment(line)
			pay = SelectPaymentLine.new(data)
			pay._onchange_move_lines()
			pay._onchange_to_pay()
			pay._onchange_payment_amount()

	def _get_data_move_lines_payment(self, line):
		data = {
			'move_line_id': line.id,
			'account_id': line.account_id.id,
			'analytic_account_id' : line.analytic_account_id and line.analytic_account_id.id or False,
			'analytic_tag_ids' : line.analytic_tag_ids and line.analytic_tag_ids.ids or False,
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

	@api.onchange('payment_lines')
	def _onchange_payment_lines(self):
		current_payment_lines = self.payment_line_ids.filtered(lambda line: not line.exclude_from_payment_detail)
		other_lines = self.payment_line_ids - current_payment_lines
		self.payment_line_ids = other_lines + self.payment_lines
		self._onchange_recompute_dynamic_line()

	@api.onchange('currency_id', 'amount', 'payment_type')
	def _onchange_payment_amount_currency(self):
		self.writeoff_account_id = self._get_account_diff_currency(self.payment_difference_line)
		self._recompute_dynamic_lines()

	def _get_account_diff_currency(self, amount):
		account = False
		company = self.env.company
		exchange_journal = company.currency_exchange_journal_id
		account = amount > 0 and exchange_journal.company_id.account_journal_payment_debit_account_id 
		if not account:
			account = company.income_currency_exchange_account_id
		return account

	@api.onchange('payment_difference_line', 'account_id','writeoff_account_id')
	def _onchange_diference_account(self):
		self._recompute_dynamic_lines()

	@api.onchange('date')
	def _onchange_payment_date(self):
		for line in self.payment_line_ids.filtered(lambda line: not line.exclude_from_payment_detail):
			line._onchange_to_pay()
			line._onchange_payment_amount()
			line._compute_payment_difference()
			line._compute_debit_credit_balance()
		self._recompute_dynamic_lines()

	@api.onchange('payment_line_ids', 'account_id', 'destination_account_id')
	def _onchange_recompute_dynamic_line(self):
		self._recompute_dynamic_lines()

	def _recompute_dynamic_lines(self):
		amount = self.amount * (self.payment_type in ('outbound', 'transfer') and 1 or -1)
		self._onchange_accounts(-amount, account_id=self.account_id, is_account_line=True)

		# Diferencia de cambio
		if self.payment_type != 'transfer':
			payment_lines = self.payment_line_ids.filtered(lambda line: not line.exclude_from_payment_detail)
			if not payment_lines:
				counter_part_amount = amount
			else:
				counter_part_amount = 0.0
			self._onchange_accounts(counter_part_amount, account_id=self.destination_account_id, is_counterpart=True)
			payment_difference =  self.payment_difference_line * (self.payment_type in ('outbound', 'transfer') and 1.0 or -1.0)
			self._onchange_accounts(payment_difference, account_id=self.writeoff_account_id, is_diff=True)

		# para destino transferencia y/o destin
		if self.payment_type == 'transfer':
			self._onchange_accounts(amount, account_id=self.destination_account_id, is_transfer=True)

		if self != self._origin:
			self.payment_lines = self.payment_line_ids.filtered(lambda line: not line.exclude_from_payment_detail)

	def _onchange_accounts(self, amount,
								account_id=None, is_account_line=False, is_manual_currency=False, is_transfer=False, is_diff=False, is_counterpart=False):
		self.ensure_one()
		in_draft_mode = self != self._origin
		def _create_origin_and_transfer_payment(self, total_balance, account, journal, new_payment_line):
			line_values = self._set_fields_detail(total_balance, is_account_line, is_manual_currency, is_counterpart, is_transfer, is_diff, account)
			if self.payment_type == 'transfer' and (journal and journal.type == 'bank'):
				if journal.bank_account_id and journal.bank_account_id.partner_id:
					line_values.update({
						'partner_id': journal.bank_account_id.partner_id.id
						})
			if new_payment_line:
				new_payment_line.update(line_values)
			else:
				line_values.update({
					'company_id': self.company_id and self.company_id.id or False,
					})
				create_method = in_draft_mode and self.env['account.payment.detail'].new or self.env['account.payment.detail'].create
				new_payment_line = create_method(line_values)

			new_payment_line._onchange_to_pay()
			new_payment_line._onchange_payment_amount()
		journal = self.journal_id
		if is_account_line:
			existing_account_origin_line = self.payment_line_ids.filtered(lambda line: line.is_account_line)
		elif is_counterpart:
			existing_account_origin_line = self.payment_line_ids.filtered(lambda line: line.is_counterpart)
		elif is_manual_currency:
			existing_account_origin_line = self.payment_line_ids.filtered(lambda line: line.is_manual_currency)
		elif is_diff:
			existing_account_origin_line = self.payment_line_ids.filtered(lambda line: line.is_diff)
		elif is_transfer:
			existing_account_origin_line = self.payment_line_ids.filtered(lambda line: line.is_transfer)
			journal = self.destination_journal_id
		if not account_id:
			self.payment_line_ids -= existing_account_origin_line
			return
		if self.currency_id.is_zero(amount):
			self.payment_line_ids -= existing_account_origin_line
			return

		_create_origin_and_transfer_payment(self, amount, account_id, journal, existing_account_origin_line)

	def _set_fields_detail(self, total_balance, is_account_line, is_manual_currency, is_counterpart, is_transfer, is_diff, account):
		line_values = {
			'payment_amount': total_balance,
			'partner_id': self.partner_id.id or False,
			'payment_id': self.id,
			'company_currency_id': self.env.company.currency_id.id,
			'is_account_line': is_account_line,
			'is_manual_currency': is_manual_currency,
			'is_counterpart': is_counterpart,
			'is_transfer': is_transfer,
			'is_diff': is_diff,
			'name':	self.ref or '/',
			'currency_id' : self.currency_id.id,
			'account_id': account,
			'ref': self.name or '/',
			'exclude_from_payment_detail': True,
			'payment_currency_id': self.currency_id.id,
		}
		company_currency = self.env.company.currency_id
		if self.currency_id and self.currency_id != company_currency:
			amount = company_currency._convert(total_balance, self.currency_id, self.env.company, self.date or fields.Date.today())
			line_values.update({
				'amount_currency' : amount
				})
		return line_values

	def _move_autocomplete_payment_lines_create(self, vals_list):
		new_vals_list = []
		for vals in vals_list:
			if not vals.get('payment_lines'):
				new_vals_list.append(vals)
				continue
			if vals.get('payment_line_ids'):
				vals.pop('payment_lines', None)
				new_vals_list.append(vals)
				continue

			vals['payment_line_ids'] = vals.pop('payment_lines')
		return new_vals_list

	def _move_autocomplete_payment_lines_write(self, vals):
		enable_autocomplete = 'payment_lines' in vals and 'payment_line_ids' not in vals and True or False
		if not enable_autocomplete:
			return False
		vals.pop('payment_lines', None)
		self.write(vals)
		return True

	@api.model_create_multi
	def create(self, vals_list):
		vals_list = self._move_autocomplete_payment_lines_create(vals_list)
		return super(AccountPayment, self).create(vals_list)

	def write(self, vals):
		if self._move_autocomplete_payment_lines_write(vals):
			return True
		else:
			vals.pop('payment_lines', None)
			res = super(AccountPayment, self).write(vals)
		return res

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
		aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
		balance = 0.0
		self.line_ids.unlink()
		for line in self.payment_line_ids:
			sign = line.balance > 0.0 and 1.0 or -1.0
			balance += line.balance
			currency = line.account_id.currency_id or line.currency_id
			counterpart_aml_dict = {
				'partner_id': self.payment_type in ('inbound', 'outbound') and self.env['res.partner']._find_accounting_partner(self.partner_id).id or False,
				'move_id': move.id,
				'debit': line.debit,
				'credit': line.credit,
				'amount_currency': abs(line.amount_currency) * sign or False,
				'payment_id': self.id,
				'journal_id': self.journal_id.id,
				'account_id':line.account_id.id,
				'analytic_account_id' : line.analytic_account_id and line.analytic_account_id.id or False,
				'analytic_tag_ids' : [(6, 0, line.analytic_tag_ids.ids)],
				'tax_ids' : [(6, 0, line.tax_ids.ids)],
				'tax_tag_ids' : [(6, 0, line.tax_tag_ids.ids)],
				'tax_repartition_line_id' : line.tax_repartition_line_id.id,
				'tax_base_amount': line.tax_base_amount,
				'inv_id':line.invoice_id.id,
				'line_pay': line.move_line_id.id,
			}
			print("counterpart_aml_dict...............",counterpart_aml_dict)
			counterpart_aml_dict.update(line._get_counterpart_move_line_vals())
			counterpart_aml = aml_obj.with_context(skip_account_move_synchronization=True).create(counterpart_aml_dict)
		# PAra la diferencia de cambio
		if self.currency_id.round(balance):
			company = self.company_id
			balance *= -1
			if self.currency_id != company.currency_id:
				balance = company.currency_id._convert(balance, self.currency_id, company, self.date or fields.Date.today(), round=False)
			line_debit, line_credit, line_amount_currency, line_currency_id = aml_obj.with_context(
				date=self.date)._compute_amount_fields(balance, self.currency_id, company.currency_id)
			counterpart_aml_dict = self._get_shared_move_line_vals(line_debit, line_credit, line_amount_currency, move.id, False)
			account = self._get_account_diff_currency(balance)
			counterpart_aml_dict.update({
				'name': "Diferencia de cambio",
				'account_id' : account.id,
				'currency_id': self.currency_id != self.company_id.currency_id and self.currency_id.id or False,
				'partner_id': self.partner_id.id or False
				})
			aml_obj.with_context(skip_account_move_synchronization=True).create(counterpart_aml_dict)
		return True

	def _update_account_on_negative(self, line, vals):
		if not line.opt_account_id:
			return
		for key in ["debit", "credit"]:
			if vals[key] < 0:
				ikey = (key == "debit") and "credit" or "debit"
				vals["account_id"] = line.opt_account_id.id
				vals[ikey] = abs(vals[key])
				vals[key] = 0

	def _synchronize_to_moves(self, changed_fields):
		''' Update the account.move regarding the modified account.payment.
		:param changed_fields: A list containing all modified fields on account.payment.
		'''
		if self._context.get('skip_account_move_synchronization'):
			return

		if not any(field_name in changed_fields for field_name in (
			'date', 'amount', 'payment_type', 'partner_type', 'payment_reference', 'is_internal_transfer',
			'currency_id', 'partner_id', 'destination_account_id', 'partner_bank_id', 'journal_id'
		)):
			return

		for pay in self.with_context(skip_account_move_synchronization=True):
			liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()

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

			line_vals_list = pay._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals)

			line_ids_commands = [
				Command.update(liquidity_lines.id, line_vals_list[0]) if liquidity_lines else Command.create(line_vals_list[0]),
			]

			# Manejar múltiples líneas de contraparte si hay más de una
			if len(counterpart_lines) == 1:
				line_ids_commands.append(Command.update(counterpart_lines.id, line_vals_list[1]))
			else:
				for line in counterpart_lines:
					line_ids_commands.append(Command.update(line.id, line_vals_list[1]))

			for line in writeoff_lines:
				line_ids_commands.append((2, line.id))

			for extra_line_vals in line_vals_list[2:]:
				line_ids_commands.append((0, 0, extra_line_vals))

			# Update the existing journal items.
			# If dealing with multiple write-off lines, they are dropped and a new one is generated.

			pay.move_id.write({
				'partner_id': pay.partner_id.id,
				'currency_id': pay.currency_id.id,
				'partner_bank_id': pay.partner_bank_id.id,
				'line_ids': line_ids_commands,
			})

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

				# if not pay.move_id.statement_line_id:
				# 	if len(counterpart_lines) != 1:
				# 		raise UserError(_(
				# 			"Journal Entry %s is not valid. In order to proceed, the journal items must "
				# 			"include one and only one receivable/payable account (with an exception of "
				# 			"internal transfers).",
				# 			move.display_name,
				# 		))

				# if writeoff_lines and len(writeoff_lines.account_id) != 1:
				# 	raise UserError(_(
				# 		"Journal Entry %s is not valid. In order to proceed, "
				# 		"all optional journal items must share the same account.",
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
				partner_type = None
				for counterpart_line in counterpart_lines:
					if counterpart_line.account_id.user_type_id.type == 'receivable':
						partner_type = 'customer'
					else:
						partner_type = 'supplier'

					liquidity_amount = liquidity_lines.amount_currency

					move_vals_to_write.update({
						'currency_id': liquidity_lines.currency_id.id or self.currency_id.id,
						'partner_id': liquidity_lines.partner_id.id,
					})
					payment_vals_to_write.update({
						'amount': abs(liquidity_amount),
						'partner_type': partner_type,
						'currency_id': liquidity_lines.currency_id.id or self.currency_id.id,
						'destination_account_id': counterpart_line.account_id.id,
						'partner_id': liquidity_lines.partner_id.id,
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
