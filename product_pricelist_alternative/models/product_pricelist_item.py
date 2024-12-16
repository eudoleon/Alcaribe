# Copyright 2024 Camptocamp (<https://www.camptocamp.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class PricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    alternative_pricelist_policy = fields.Selection(
        selection=[
            ("use_lower_price", "Use lower price"),
            ("ignore", "Ignore alternatives"),
        ],
        default="use_lower_price",
        required=True,
    )
    fixed_price_usd = fields.Float(string="Precio Fijo USD", digits='Product Price')


    def convert_price_to_company_currency(self):
        for price_list in self:
            if price_list.fixed_price_usd and price_list.pricelist_id.currency_usd_id:
                company_currency = self.env.company.currency_id
                fixed_price = price_list.pricelist_id.currency_usd_id._convert(
                    price_list.fixed_price_usd,
                    company_currency,
                    self.env.company,
                    fields.Date.today()
                )
                price_list.fixed_price = fixed_price