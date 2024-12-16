# -*- coding: utf-8 -*-

from odoo import models, fields, _


# ---------------------------------------------------------------------
# This model is for the scrap reasons
# ---------------------------------------------------------------------

class StockScrapReason(models.Model):
    _name = "stock.scrap.reason"
    _description = "Stock Scrap Reason"
    _order = "sequence asc"

    sequence = fields.Integer()
    name = fields.Char(string=_("Reason"))
    scrap_order_count = fields.Integer(compute="_compute_scrap_order_count")

    # def _compute_scrap_order_count(self):
    #     self.scrap_order_count = self.env['stock.scrap'].search_count([
    #         ('reason_id', '=', self.id),
    #         ('state', '=', 'done')]
    #     )

    def _compute_scrap_order_count(self):
        # Calculate the count of scrap orders for each reason using read_group
        scrap_data = self.env['stock.scrap'].read_group(
            domain=[('reason_id', 'in', self.ids), ('state', '=', 'done')],
            fields=['reason_id'],
            groupby=['reason_id']
        )
        scrap_count = {data['reason_id'][0]: data['reason_id_count'] for data in scrap_data}
        for reason in self:
            reason.scrap_order_count = scrap_count.get(reason.id, 0)

    def action_see_scrap_orders(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_stock_scrap")
        scraps = self.env['stock.scrap'].search([
            ('reason_id', '=', self.id),
            ('state', '=', 'done')]
        )
        action['domain'] = [('id', 'in', scraps.ids)]
        action['context'] = dict(self._context, create=False)
        return action
