# Copyright 2019 Komit Consulting - Duc Dao Dong
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from odoo import api, fields, models


class LandedCostLine(models.Model):
    _inherit = "stock.landed.cost.lines"

    price_unit = fields.Monetary(currency_field="company_currency_id", string="Cost in Company Currency")
    currency_id = fields.Many2one(related="cost_id.currency_id")
    currency_price_unit = fields.Monetary(currency_field="currency_id", string="Cost")

    company_currency_id = fields.Many2one(related="cost_id.company_currency_id")

    tax_today = fields.Float(string="Tasa", store=True,
                             default=lambda self: self.env.company.currency_id_dif.inverse_rate,
                             tracking=True, digits='Dual_Currency_rate')

    @api.onchange("currency_price_unit")
    def _onchange_currency_price_unit(self):
        for rec in self:
            if rec.currency_price_unit:
                date = rec.cost_id.date
                company = rec.cost_id.company_id
                if rec.cost_id.currency_id != company.currency_id:
                    rec.price_unit = rec.currency_price_unit * rec.tax_today
                else:
                    rec.price_unit = rec.currency_price_unit

    @api.onchange("product_id")
    def onchange_product_id(self):
        res = super(LandedCostLine, self).onchange_product_id()
        self.currency_price_unit = self.price_unit
        return res
