from odoo import fields, models, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    rate = fields.Float(string='Tasa', default=lambda x: x.env['res.currency.rate'].search([
        ('name', '<=', fields.Date.today()), ('currency_id', '=', 2)], limit=1).sell_rate, digits=(12, 2))
    custom_rate = fields.Boolean(string='¿Usar tasa de cambio personalizada?')
    currency_id2 = fields.Many2one('res.currency', string='Moneda Secundaria')
    amount_total_signed_rate = fields.Monetary(string='Total', currency_field='currency_id2',
                                               compute='_compute_amount_rate', store=True)
    amount_untaxed_signed_rate = fields.Monetary(string='Base Imponible', currency_field='currency_id2',
                                                 compute='_compute_amount_rate', store=True)
    amount_tax_rate = fields.Monetary(string='impuestos', currency_field='currency_id2',
                                      compute='_compute_amount_rate', store=True)
    doc_type = fields.Selection(related='partner_id.doc_type')
    vat = fields.Char(related='partner_id.vat')

    def _prepare_invoice(self):
        res = super(PurchaseOrder, self)._prepare_invoice()
        res['custom_rate'] = self.custom_rate
        res['os_currency_rate'] = self.rate
        res['currency_id2'] = self.currency_id2.id
        return res

    @api.constrains('currency_id')
    @api.onchange('currency_id')
    def _onchange_currency_second(self):
        for sale in self:
            if sale.company_id.currency_id2 == sale.currency_id:
                sale.currency_id2 = sale.company_id.currency_id.id
            if sale.company_id.currency_id == sale.currency_id:
                sale.currency_id2 = sale.company_id.currency_id2.id

    @api.depends('amount_total', 'currency_id2', 'amount_untaxed', 'amount_tax', 'rate')
    def _compute_amount_rate(self):
        for purchase in self:
            if purchase.company_id.currency_id2 == purchase.currency_id:
                purchase.update({
                    'amount_untaxed_signed_rate': (purchase.amount_untaxed * purchase.rate),
                    'amount_tax_rate': (purchase.amount_tax * purchase.rate),
                    'amount_total_signed_rate': (purchase.amount_total * purchase.rate),
                })
            if purchase.company_id.currency_id == purchase.currency_id:
                if purchase.rate:
                    purchase.update({
                        'amount_untaxed_signed_rate': (purchase.amount_untaxed / purchase.rate),
                        'amount_tax_rate': (purchase.amount_tax / purchase.rate),
                        'amount_total_signed_rate': (purchase.amount_total / purchase.rate)
                    })

    class PurchaseOrderLine(models.Model):
        _inherit = 'purchase.order.line'

        currency_id2 = fields.Many2one(related='order_id.currency_id2', depends=['order_id.currency_id2'], store=True,
                                       string='Moneda Secundaria')
        price_subtotal_rate = fields.Float(string='Subtotal', currency_field='currency_id2',
                                           compute='_compute_amount_rate_line', store=True)
        price_unit_rate = fields.Float(string='Precio unidad', currency_field='currency_id2',
                                       compute='_compute_amount_rate_line', store=True)

        @api.depends('order_id.rate', 'currency_id2', 'price_unit', 'price_subtotal')
        def _compute_amount_rate_line(self):
            for line in self:
                if line.order_id.company_id.currency_id2 == line.order_id.currency_id:
                    line.update({
                        'price_unit_rate': (line.price_unit * line.order_id.rate),
                        'price_subtotal_rate': (line.price_subtotal * line.order_id.rate),
                    })
                if line.order_id.company_id.currency_id == line.order_id.currency_id:
                    if line.order_id.rate:
                        line.update({
                            'price_unit_rate': (line.price_unit / line.order_id.rate),
                            'price_subtotal_rate': (line.price_subtotal / line.order_id.rate)
                        })
