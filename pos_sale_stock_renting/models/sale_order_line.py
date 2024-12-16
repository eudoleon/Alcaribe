from odoo import api, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _compute_qty_delivered(self):
        super()._compute_qty_delivered()
        if 'sale_order_line_id' not in self.env['pos.order.line']:
            return
        for sale_line in self:
            if sale_line.is_rental and sale_line.pos_order_line_ids:
                sale_line.qty_delivered = sum([self._convert_qty(sale_line, pos_line.qty, 'p2s') for pos_line in sale_line.pos_order_line_ids if sale_line.product_id.type != 'service'], 0)
