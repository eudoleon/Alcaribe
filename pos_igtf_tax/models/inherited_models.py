# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError

# class PosSession(models.Model):
#     _inherit = 'pos.session'
#
#     def _loader_params_pos_payment_method(self):
#         print('metodo de pagos result')
#         result = super()._loader_params_pos_payment_method()
#         result['search_params']['fields'].extend([
#             "x_igtf_percentage",
#             "x_is_foreign_exchange",
#         ])
#         print('metodo de pagos result', result)
#         return result

class PosOrder(models.Model):
    _inherit = "pos.order"

    x_igtf_amount = fields.Monetary("Monto IGTF", compute="_compute_x_igtf_amount", store=True)

    @api.depends("lines.x_is_igtf_line", "lines.price_subtotal_incl")
    def _compute_x_igtf_amount(self):
        for rec in self:
            rec.x_igtf_amount = sum(rec.lines.filtered("x_is_igtf_line").mapped("price_subtotal_incl"))

    def _get_fields_for_order_line(self):
        fields = super()._get_fields_for_order_line()

        fields.append('x_is_igtf_line')
        
        return fields
        
class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    x_is_igtf_line = fields.Boolean("Linea IGTF")

    def _order_line_fields(self, line, session_id):
        result = super()._order_line_fields(line, session_id)
        vals = result[2]

        vals["x_is_igtf_line"] = vals.get("x_is_igtf_line", line[2].get("x_is_igtf_line", False))

        return result

    def _export_for_ui(self, orderline):
        res = super()._export_for_ui(orderline)

        res["x_is_igtf_line"] = orderline.x_is_igtf_line

        return res

class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    x_igtf_percentage = fields.Float("Porcentaje de IGTF")
    x_is_foreign_exchange = fields.Boolean("Pago en divisas")

    @api.constrains("x_igtf_percentage")
    def _check_x_igtf_percentage(self):
        for rec in self:
            if rec.x_igtf_percentage < 0 and rec.x_is_foreign_exchange:
                raise ValidationError("El porcentage IGTF debe ser mayor a cero")

class PosConfig(models.Model):
    _inherit = "pos.config"

    x_igtf_product_id = fields.Many2one("product.product", "Producto IGTF", tracking=True)

    aplicar_igtf = fields.Boolean("Aplicar IGTF", default=False)

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_x_igtf_product_id = fields.Many2one(
        string="Producto IGTF", 
        related="pos_config_id.x_igtf_product_id",
        readonly=False,
        store=True,
    )

    aplicar_igtf = fields.Boolean(related="pos_config_id.aplicar_igtf", readonly=False, store=True)

    @api.constrains("pos_x_igtf_product_id")
    def _check_pos_x_igtf_product_id(self):
        for rec in self.filtered("pos_x_igtf_product_id"):
            if sum(rec.pos_x_igtf_product_id.taxes_id.mapped("amount")) != 0:
                raise ValidationError("El producto IGTF debe ser exento")
