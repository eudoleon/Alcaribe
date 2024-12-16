from odoo import fields, models, api, _
import logging
_logger = logging.getLogger(__name__)
from odoo.tools import float_is_zero, float_compare

MAP_INVOICE_TYPE_PAYMENT_SIGN = {
	'out_invoice': 1,
	'in_refund': 1,
	'in_invoice': -1,
	'out_refund': -1,
	'entry': 1,
}

class AccountPaymentDetail(models.Model):
	_name = "account.payment.detail"
	_description = "Detalle de transferencia, pago y/o cobro"
	_inherit = "analytic.mixin"

	@api.depends('move_line_id', 'date', 'currency_id',)
	def _amount_residual(self):
		for val in self:
			if val.move_line_id:
				#amount, amount_currency = val._compute_payment_amount_currency()
				val.amount_residual = val.move_line_id.amount_residual
				val.amount_residual_currency = val.move_line_id.amount_residual_currency

	@api.depends('payment_amount', 'payment_currency_id', 'invoice_id', 'move_line_id',
			'payment_id.payment_type', 'payment_id.date', 'payment_id.currency_id')
	def _compute_debit_credit_balance(self):
		sign = -1
		for val in self:

			balance = val.payment_amount
			company = val.company_id or val.env.company

			if val.payment_id.currency_id and self.payment_id.currency_id != company.currency_id:
				currency = val.payment_id.currency_id
				balance = currency._convert(balance, val.company_currency_id, company, val.payment_id.date or fields.Date.today())

			if val.move_line_id:
				# if val.move_line_id.balance > 0:
				# 	sign = 1
				# else:
				# 	sign = -1			
				# balance *= sign * -1

				# if val.account_id.account_type == 'asset_receivable':
				# 	balance *= 1
				# 	if val.move_line_id.balance < 0.0:
				# 		balance = abs(balance)

				val.debit = balance > 0.0 and balance or False
				val.credit = balance < 0.0 and abs(balance) or False
				val.balance = balance
				val._amount_residual()	
			else:
				val.debit = balance > 0.0 and balance or False
				val.credit = balance < 0.0 and abs(balance) or False
				val.balance = balance


	@api.depends('balance')
	def _compute_type(self):
		for val in self:
			val.type = val.balance > 0 and 'Ingreso' or "Egreso"
	
	name = fields.Char('Etiqueta')
	sequence = fields.Integer(compute='_compute_sequence', store=True, readonly=False, precompute=True)
	payment_id = fields.Many2one('account.payment', string="Pago y/o Cobro", index=True, auto_join=True, ondelete="cascade")
	state = fields.Selection(related='payment_id.state', store=True)
	display_type = fields.Selection(
		selection=[
			('asset_cash', 'Banco o Caja'),
			('bill', 'Factura de Compra'),
			('invoice', 'Factura de Venta'),
			('entry', 'Apunte Manual'),
			('reverse', 'Notas Creditos'),
			('tax', 'Impuestos'),
			('rounding', "Rounding"),
			('counterpart', 'Contra partida'),
			('diff', 'Contra partida Diferencia en cambio'),
			('diff_curr', 'Contra partida Diferencia en cambio'),
			('advance', 'Anticipo'),
			('line_section', 'Section'),
			('line_note', 'Note'),
			('epd', 'Early Payment Discount')
		],
		compute='_compute_display_type', store=True, readonly=False, precompute=True,
		required=True,
	)
	other_payment_id = fields.Many2one('account.payment', string="Pagos")
	move_line_id = fields.Many2one('account.move.line', string="Documentos, pagos/cobros", copy=False)
	partner_type = fields.Selection(related="payment_id.partner_type") 
	account_id = fields.Many2one('account.account', string="Cuenta", required=True)
	invoice_id = fields.Many2one('account.move', string="Factura")
	partner_id = fields.Many2one('res.partner', string="Empresa")
	currency_id = fields.Many2one('res.currency', string="Moneda")
	company_currency_id = fields.Many2one('res.currency', string="Moneda de la compañia",
		required=True, default=lambda self: self.env.company.currency_id)
	move_id = fields.Many2one('account.move', string="Comprobante diario")
	ref = fields.Char(string="Referencia")
	number = fields.Char('Número')
	type = fields.Char(compute="_compute_type", store=True, readonly=True, string="Type")
	debit = fields.Monetary('Debit', compute='_compute_debit_credit_balance', inverse='_inverse_debit', precompute=True, store=True, readonly=True, currency_field='company_currency_id')
	credit = fields.Monetary('Credit', compute='_compute_debit_credit_balance', inverse='_inverse_credit', precompute=True, store=True, readonly=True, currency_field='company_currency_id')
	balance = fields.Monetary(compute='_compute_debit_credit_balance', store=True, readonly=False, currency_field='company_currency_id', precompute=True, help="Technical field holding the debit - credit in order to open meaningful graph views from reports")
	amount_currency = fields.Monetary(string="Moneda de importes")
	journal_id = fields.Many2one('account.journal', related="payment_id.journal_id", string="Diario", store=True)
	company_id = fields.Many2one('res.company', related="journal_id.company_id", store=True)
	date = fields.Date(related="payment_id.date")
	is_main = fields.Boolean(string="Is Principal", default=False)
	is_account_line = fields.Boolean(string="Cuenta origen", default=False)
	is_transfer = fields.Boolean(string="Es transferencia", default=False)
	is_diff = fields.Boolean(string="Es Diferencia", default=False)
	is_counterpart = fields.Boolean(string="Es Contrapartida", default=False)
	is_manual_currency = fields.Boolean(string="Moneda manual", default=False)
	amount_residual = fields.Monetary(string="Deuda MN", compute="_amount_residual", store=True, currency_field='company_currency_id',
		help="The residual amount on a journal item expressed in the company currency.")
	amount_residual_currency = fields.Monetary(string="Deuda ME", compute="_amount_residual", store=True, currency_field='currency_id',
		help="The residual amount on a journal item expressed in its currency (possibly not the company currency).")
	date_maturity = fields.Date(related="move_line_id.date_maturity", store=True, string="Fecha vencimiento")
	payment_currency_id = fields.Many2one('res.currency', string="Moneda de pago", default=lambda self: self.env.company.currency_id)
	payment_amount = fields.Monetary('Monto de pago', currency_field="payment_currency_id")
	exclude_from_payment_detail = fields.Boolean(help="Campo tecnico utilizado para excluir algunas lineas de la \
		pestaña detalle de payment_lines en la vista formulario")
	to_pay = fields.Boolean('A pagar', default=False)
	product_id = fields.Many2one('product.product', string='Product')
	tax_ids = fields.Many2many('account.tax', string='Taxes', help="Taxes that apply on the base amount", index=True,  store=True, check_company=True)
	tax_tag_ids = fields.Many2many(string="Tags", comodel_name='account.account.tag', ondelete='restrict',
		help="Tags assigned to this line by the tax creating it, if any. It determines its impact on financial reports.")
	tax_repartition_line_id = fields.Many2one('account.tax.repartition.line',
		string="Originator Tax Distribution Line", ondelete='restrict', 
		check_company=True,
		help="Tax distribution line that caused the creation of this move line, if any") 
  
	auto_tax_line = fields.Boolean()
	tax_line_id = fields.Many2one('account.payment.detail', ondelete = 'cascade')
	tax_line_id2 = fields.Many2one('account.tax', ondelete = 'cascade')
	tax_base_amount = fields.Monetary(string="Base Amount", currency_field='company_currency_id')

	@api.depends('display_type')
	def _compute_sequence(self):
		seq_map = {
			'tax': 10000,
			'rounding': 11000,
			'payment_term': 12000,
		}
		for line in self:
			line.sequence = seq_map.get(line.display_type, 100)
	@api.depends('payment_id')
	def _compute_display_type(self):
		for line in self.filtered(lambda l: not l.display_type):
			line.display_type = (
				'tax' if line.tax_line_id else
				'invoice' if line.move_line_id.move_id.move_type in ("out_invoice","out_receipt") else 
				'bill' if line.move_line_id.move_id.move_type in ("in_invoice","in_receipt") else 
				'reverse' if line.move_line_id.move_id.move_type in ("in_refund","out_refund") else 
				'entry' if line.move_line_id.move_id.move_type == 'entry' else 
				'advance' if not line.move_line_id and line.account_id.used_for_advance_payment  else
				'product' if line.product_id  else
				'counterpart'
			)


	@api.onchange('debit')
	def _inverse_debit(self):
		for line in self:
			if line.debit:
				line.credit = 0
			line.balance = line.debit - line.credit
			line.payment_amount = line.debit - line.credit

	@api.onchange('credit')
	def _inverse_credit(self):
		for line in self:
			if line.credit:
				line.debit = 0
			line.balance = line.debit - line.credit
			line.payment_amount = line.debit - line.credit	
		
	@api.onchange('partner_id')
	def _onchange_partner_id(self):
		if not self.payment_currency_id:
			self.payment_currency_id = self.payment_id and self.payment_id.currency_id.id or self.env.company.currency_id.id

	@api.depends('move_line_id', 'invoice_id', 'payment_amount', 'payment_id.date', 'payment_currency_id')
	def _compute_payment_difference(self):
		for val in self:
			if val.move_line_id:
				payment_amount = -val.payment_amount if val.payment_id.payment_type == 'outbound' else val.payment_amount
				if val.move_line_id.currency_id and  val.move_line_id.currency_id != val.move_line_id.company_currency_id:
					payment_amount =  val.move_line_id.company_currency_id._convert(
						payment_amount, val.currency_id, val.company_id, val.date or fields.Date.today()
						)
				val.payment_difference = val._compute_payment_amount() - payment_amount
			else:
				val.payment_difference = 0.0

	payment_difference = fields.Monetary(compute='_compute_payment_difference', string='Payment Difference', readonly=True, store=True)
	payment_difference_handling = fields.Selection([('open', 'Mantener abierto'), ('reconcile', 'Marcar la factura como totalmente pagada')], default='open', string="Payment Difference Handling", copy=False)
	writeoff_account_id = fields.Many2one('account.account', string="Difference Account", domain=[('deprecated', '=', False)], copy=False)

	# esta funciona es para capturar el monto convertido en dolares o soles a la fecha de pago
	def _compute_payment_amount_currency(self):
		total = 0.0
		for val in self:
			payment_currency = val.currency_id or val.journal_id.currency_id or val.journal_id.company_id.currency_id or val.company_currency_id
			if not val.move_line_id:
				total = val.payment_amount
				amount_currency = total
			else:
				amount = val.move_line_id.amount_residual
				amount_currency = val.move_line_id.amount_residual_currency
			if float_is_zero(amount_currency, precision_rounding=payment_currency.rounding):
				return amount, amount_currency
			else:
				amount = payment_currency._convert(amount_currency, val.company_currency_id,
														val.company_id, val.date or fields.date.today())
				return amount, amount_currency

	def _compute_payment_amount(self, invoices=None, currency=None):
		for val in self:
			payment_currency = currency
			if not payment_currency:
				payment_currency = val.currency_id or val.journal_id.currency_id or val.journal_id.company_id.currency_id or val.company_currency_id
			sign = 1
			if val.move_line_id:
				if val.move_line_id.move_id:
					sign = MAP_INVOICE_TYPE_PAYMENT_SIGN[val.move_line_id.move_id.move_type]
			amount = val.amount_residual
			if not val.move_line_id:
				amount = val.payment_amount

			if (payment_currency == val.move_line_id.company_currency_id) or (payment_currency == val.company_currency_id):
				total = sign * amount
			else:
				if val.move_line_id:
					if not val.move_line_id.amount_residual_currency:
						total = sign * val.company_currency_id._convert(
							amount, payment_currency, val.company_id, val.date or fields.Date.today()
						)
					else:
						total = sign * val.move_line_id.amount_residual_currency
				else:
					total = sign * val.company_currency_id._convert(
							amount, payment_currency, val.company_id, val.date or fields.Date.today()
						)
			return total

	@api.onchange('payment_amount', 'payment_currency_id', 'payment_id.payment_type', 'date')
	def _onchange_payment_amount(self):
		for val in self:
			currency = False
			amount = 0.0
			if not val.is_main and val.payment_id.payment_type != 'transfer':
				if val.payment_currency_id != val.company_id.currency_id:
					amount = val.payment_amount
					currency = val.payment_currency_id or False
			elif val.is_main and val.payment_id.payment_type != 'transfer':
				company = val.company_id or val.env.company
				currency = val.journal_id.currency_id or val.journal_id.company_id.currency_id or val.env.company.currency_id
				if currency != val.journal_id.company_id.currency_id:
					if currency != val.payment_currency_id:
						amount = val.company_currency_id._convert(val.payment_amount, currency, company, val.payment_id.date or fields.Date.today())
					else:
						amount = val.payment_amount
			if val.account_id.currency_id:
				currency = val.account_id.currency_id
				if currency != val.company_currency_id and val.payment_id.currency_id == val.company_currency_id:
					amount = val.company_currency_id._convert(val.payment_amount, currency, val.company_id, val.payment_id.date or fields.Date.today())
			else:
				if val.invoice_id and val.invoice_id.currency_id != val.company_currency_id:
					currency = val.invoice_id.currency_id
					amount = val.payment_currency_id._convert(val.payment_amount, currency, val.company_id, val.payment_id.date or fields.Date.today())
			val.amount_currency = amount
			val.currency_id = currency
			return {'values':{'currency_id':currency and currency.id or False, 'amount_currency': amount}}

	@api.onchange('to_pay', 'payment_id.payment_type', 'payment_amount')
	def _onchange_to_pay(self):
		for val in self:
			if val.payment_id.payment_type != 'transfer':
				if val.to_pay:
					if val.payment_currency_id != val.company_currency_id:
						val.payment_amount = val._compute_payment_amount(currency=val.payment_currency_id) * -1
					else:
						val.payment_amount = val.amount_residual * -1

	@api.onchange('move_line_id')
	def _onchange_move_lines(self):
		for val in self:
			move_line = val.move_line_id
			if move_line:
				move = move_line.move_id
				move_type = move.move_type if move else False
				val.invoice_id = move and move.id or False
				val.name = move_line.name
				val.ref = move_line.ref or False
				val.account_id = move_line.account_id.id
				val.partner_id = move_line.partner_id.id
				val.number = move.name if move else False
				val.company_currency_id = move_line.company_currency_id.id
				val.other_payment_id = move_line.payment_id.id
				# Determinar el display_type
				type_map = {
					'out_invoice': 'invoice',
					'out_receipt': 'invoice',
					'in_invoice': 'bill',
					'in_receipt': 'bill',
					'in_refund': 'reverse',
					'out_refund': 'reverse',
					'entry': 'entry'
				}
				val.display_type = type_map.get(move_type, 'entry')
				# Manejo de valores a partir de _onchange_payment_amount
				vals = val._onchange_payment_amount()
				values = vals.get('values', {})
				val.currency_id = values.get('currency_id')
				val.amount_currency = values.get('amount_currency')



	def _onchange_read_line_pay(self):
		for line in self:
			line._onchange_to_pay()
			line._onchange_payment_amount()

	def _get_counterpart_move_line_vals(self):
		vals = {
			'account_id' : self.account_id.id,
			'currency_id' : self.currency_id != self.company_currency_id and self.currency_id.id or self.payment_currency_id.id,
			'partner_id' : self.partner_id and self.partner_id.id or False,
			'tax_ids' : [(6, 0, self.tax_ids.ids)],
			'tax_tag_ids' : [(6, 0, self.tax_tag_ids.ids)],
			'tax_base_amount': self.tax_base_amount,
			'tax_line_id': self.tax_line_id2.id,
			'tax_repartition_line_id' :  self.tax_repartition_line_id.id,
		}
		if self.invoice_id:
			name = "Pago Documento: " + self.invoice_id.name
		else:
			name = self.name or ''
		vals.update(
			name = name,
			ref = self.payment_id.ref or ''
		)
		if self.analytic_distribution:
			vals.update({"analytic_distribution": self.analytic_distribution})
		if self.currency_id and self.currency_id != self.company_currency_id:
			sing = self.debit > 0.0 and 1 or -1
			vals.update({
				'amount_currency': abs(self.amount_currency) * sing
				})
		return vals
