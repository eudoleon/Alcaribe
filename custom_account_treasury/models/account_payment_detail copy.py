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

	@api.depends('move_line_id', 'date', 'currency_id')
	def _amount_residual(self):
		# for line in self:
		residual, residual_currency = 0.0, 0.0
		for val in self:
			if val.move_line_id:
				residual, residual_currency = val._compute_payment_amount_currency()
				val.amount_residual = residual 
				val.amount_residual_currency = residual_currency 

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
				if val.move_line_id.balance > 0:
					sign = 1
				else:
					sign = -1
			#else:
			#	sign = val.payment_id.payment_type == 'outbound' and 1 or -1

			balance *= sign * -1

			if val.account_id.user_type_id.id == 2:
				balance *= 1
				if val.move_line_id.balance < 0.0:
					balance = abs(balance)

			val.debit = balance > 0.0 and balance or False
			val.credit = balance < 0.0 and abs(balance) or False
			val.balance = balance


	@api.depends('balance')
	def _compute_type(self):
		for val in self:
			val.type = val.balance > 0 and 'Ingreso' or "Egreso"

	name = fields.Char('Etiqueta')
	payment_id = fields.Many2one('account.payment', string="Pago y/o Cobro", 
		index=True, auto_join=True, ondelete="cascade")
	state = fields.Selection(related='payment_id.state', store=True)
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
	debit = fields.Monetary('Debit', compute='_compute_debit_credit_balance', store=True, readonly=True, currency_field='company_currency_id')
	credit = fields.Monetary('Credit', compute='_compute_debit_credit_balance', store=True, readonly=True, currency_field='company_currency_id')
	balance = fields.Monetary(compute='_compute_debit_credit_balance', store=True, readonly=True, currency_field='company_currency_id',
		help="Technical field holding the debit - credit in order to open meaningful graph views from reports")
	amount_currency = fields.Monetary(string="Moneda de importes")
	journal_id = fields.Many2one('account.journal', related="payment_id.journal_id", string="Diario", store=True)
	company_id = fields.Many2one('res.company', related="journal_id.company_id", store=True)
	date = fields.Date(related="payment_id.date")
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
	analytic_account_id = fields.Many2one('account.analytic.account', compute="_compute_analytic_account", string='Analytic Account', index=True,  store=True, readonly=False, check_company=True, copy=True)
	analytic_tag_ids = fields.Many2many('account.analytic.tag', compute="_compute_analytic_account", string='Analytic Tags', store=True, readonly=False, check_company=True, copy=True)
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
	tax_base_amount = fields.Monetary(string="Base Amount", 
        currency_field='company_currency_id')

	@api.onchange('account_id', 'partner_id', 'date')
	def _compute_analytic_account(self):
		for record in self:
			rec = self.env['account.analytic.default'].account_get(
				partner_id=record.partner_id.commercial_partner_id.id or record.move_id.partner_id.commercial_partner_id.id,
				account_id=record.account_id.id,
				user_id=record.env.uid,
				date=record.date,
				company_id=record.move_id.company_id.id
			)
			if rec:
				record.analytic_account_id = rec.analytic_id
				record.analytic_tag_ids = rec.analytic_tag_ids

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
				amount_currency = 0.0
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
			if not val.exclude_from_payment_detail and val.payment_id.payment_type != 'transfer':
				if val.payment_currency_id != val.company_id.currency_id:
					amount = val.payment_amount
					currency = val.payment_currency_id or False
			elif val.exclude_from_payment_detail and val.payment_id.payment_type != 'transfer':
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
						val.payment_amount = abs(val._compute_payment_amount(currency=val.payment_currency_id))
					else:
						val.payment_amount = abs(val.amount_residual)

	@api.onchange('move_line_id')
	def _onchange_move_lines(self):
		for val in self:
			if val.move_line_id:
				val.invoice_id = val.move_line_id.move_id and val.move_line_id.move_id.id or False
				val.name = val.move_line_id.name
				val.ref = val.move_line_id.ref or False
				val.account_id = val.move_line_id.account_id.id
				val.partner_id = val.move_line_id.partner_id.id
				val.number = val.move_line_id.move_id.name
				val.company_currency_id = val.move_line_id.company_currency_id.id
				val.other_payment_id = val.move_line_id.payment_id.id
			vals = val._onchange_payment_amount()
			val.currency_id = vals['values'].get('currency_id')
			val.amount_currency = vals['values'].get('amount_currency')



	def _onchange_read_line_pay(self):
		for line in self:
			line._onchange_to_pay()
			line._onchange_payment_amount()

	def _get_counterpart_move_line_vals(self):
		vals = {
			'account_id' : self.account_id.id,
			'currency_id' : self.currency_id != self.company_currency_id and self.currency_id.id or False,
			'partner_id' : self.partner_id and self.partner_id.id or False,
			'analytic_account_id' : self.analytic_account_id and self.analytic_account_id.id or False,
			'analytic_tag_ids' : self.analytic_tag_ids and self.analytic_tag_ids.ids or False,
			'tax_ids' : [(6, 0, self.tax_ids.ids)],
			'tax_tag_ids' : [(6, 0, self.tax_tag_ids.ids)],
			'tax_base_amount': self.tax_base_amount,
			'tax_line_id': self.tax_line_id2.id,
			'tax_repartition_line_id' :  self.tax_repartition_line_id.id,
		}
		if self.invoice_id:
			name = "Pago Documento: " + self.invoice_id.name
			analytic_account_id = self.analytic_tag_ids and self.analytic_tag_ids.id or False,
			analytic_tag_ids = self.analytic_tag_ids and self.analytic_tag_ids.id or False,
			tax_ids = [(6, 0, self.tax_ids.ids)],
			tax_repartition_line_id = self.tax_repartition_line_id and self.tax_repartition_line_id.id  or False,
		else:
			name = self.name or ''
		vals.update(
			name = name,
			ref = self.payment_id.ref or ''
		)
		if self.currency_id and self.currency_id != self.company_currency_id:
			sing = self.debit > 0.0 and 1 or -1
			vals.update({
				'amount_currency': abs(self.amount_currency) * sing
				})
		return vals
