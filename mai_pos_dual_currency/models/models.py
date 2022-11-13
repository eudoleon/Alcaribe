from odoo import fields, models,api


class PosPaymentMethod(models.Model):
	_inherit = 'pos.payment.method'

	pago_usd = fields.Boolean("Pago $")


class PosPayment(models.Model):
	_inherit="pos.payment"

	usd_amt = fields.Float("USD $")


class PosOrder(models.Model):
	_inherit = "pos.order"

	@api.model
	def _payment_fields(self, order, ui_paymentline):
		res = super(PosOrder, self)._payment_fields(order, ui_paymentline)
		res.update({
			'usd_amt': ui_paymentline.get('usd_amt')or 0.0,
		})
		return res


class PosConfig(models.Model):
	_inherit = "pos.config"

	show_dual_currency = fields.Boolean(
		"Show dual currency", help="Show Other Currency in POS", default=False
	)

	rate_company = fields.Float(string='Rate', related='currency_id.rate')

	show_currency = fields.Many2one('res.currency', string='Currency.', default=lambda self: self.env['res.currency'].search([('name', '=', 'USD')], limit=1))

	show_currency_rate = fields.Float(string='Rate.', related='show_currency.rate')

	show_currency_symbol = fields.Char(related='show_currency.symbol')

	show_currency_position = fields.Selection(related='show_currency.position')

	default_location_src_id = fields.Many2one(
		"stock.location", related="picking_type_id.default_location_src_id"
	)


class AccountMove(models.Model):
	_inherit = "account.move"

	currency_rate = fields.Monetary(string='Tasa', compute='_compute_currency_amount', currency_field='vef_currency_id')
	impuesto_en_vef = fields.Monetary(string='Impuesto en USD', compute='_compute_currency_amount', currency_field='vef_currency_id')
	total_amount_vef = fields.Monetary(string='Total en USD', compute='_compute_currency_amount', currency_field='vef_currency_id')
	vef_currency_id = fields.Many2one('res.currency', 'Currency.', default=lambda self: self.env.ref('base.VEF'))
	usd_currency_id = fields.Many2one('res.currency', 'Currency..', default=lambda self: self.env.ref('base.USD'))
	
	@api.onchange('vef_currency_id')
	def onchange_vef_currency(self):
		for move in self:
			move.currency_id = move.vef_currency_id.id


	def _compute_currency_amount(self):
		for move in self:
			if move.vef_currency_id:
				date = move.invoice_date or move.create_date.date()
				currency_rate = 0.0

				for rec in move.vef_currency_id.rate_ids:
					if date >= rec.name:
						currency_rate = rec.rate
						break

				if not currency_rate and move.vef_currency_id.rate_ids:
					currency_rate = move.vef_currency_id.rate_ids[-1].rate

				# move.currency_rate = currency_rate
				# move.impuesto_en_vef =  move.amount_tax_signed / currency_rate
				# move.total_amount_vef =  move.amount_total_signed / currency_rate

				move.currency_rate = currency_rate
				try:
					move.impuesto_en_vef =  move.amount_tax_signed / currency_rate
				except:
					print(move.impuesto_en_vef)
				try:
					move.total_amount_vef =  move.amount_total_signed / currency_rate
				except:
					print(move.total_amount_vef)