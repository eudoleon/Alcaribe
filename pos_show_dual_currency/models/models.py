from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
class PosConfig(models.Model):
    _inherit = "pos.config"

    show_dual_currency = fields.Boolean(
        "Show dual currency", help="Show Other Currency in POS", default=True
    )

    rate_company = fields.Float(string='Rate', related='currency_id.rate')

    show_currency = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env['res.currency'].search([('name', '=', 'USD')], limit=1))

    show_currency_rate = fields.Float(string='Rate', related='show_currency.rate')

    #show_currency_rate_real = fields.Float(string='Rate', related='show_currency.rate_real')# darrell

    show_currency_symbol = fields.Char(related='show_currency.symbol')

    show_currency_position = fields.Selection([('after', 'After'),
                      ('before', 'Before'),
                      ],related='show_currency.position')

    default_location_src_id = fields.Many2one(
        "stock.location", related="picking_type_id.default_location_src_id"
    )


    @api.constrains('pricelist_id', 'use_pricelist', 'available_pricelist_ids', 'journal_id', 'invoice_journal_id', 'payment_method_ids')
    def _check_currencies(self):
        for config in self:
            if config.use_pricelist and config.pricelist_id not in config.available_pricelist_ids:
                raise ValidationError(_("The default pricelist must be included in the available pricelists."))

            # Check if the config's payment methods are compatible with its currency
            # for pm in config.payment_method_ids:
            #     if pm.journal_id and pm.journal_id.currency_id and pm.journal_id.currency_id != config.currency_id:
            #         raise ValidationError(_("All payment methods must be in the same currency as the Sales Journal or the company currency if that is not set."))

        if any(self.available_pricelist_ids.mapped(lambda pricelist: pricelist.currency_id != self.currency_id)):
            raise ValidationError(_("All available pricelists must be in the same currency as the company or"
                                    " as the Sales Journal set on this point of sale if you use"
                                    " the Accounting application."))
        if self.invoice_journal_id.currency_id and self.invoice_journal_id.currency_id != self.currency_id:
            raise ValidationError(_("The invoice journal must be in the same currency as the Sales Journal or the company currency if that is not set."))

