# -*- coding: utf-8 -*-

from odoo import fields, models

class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _get_payment_terminal_selection(self):
        return super(PosPaymentMethod, self)._get_payment_terminal_selection() + [('vpos', 'Vpos')]

    vpos_methodType=fields.Selection([('tarjeta', 'Tarjeta'), ('cheque', 'Cheque'), ('cambio','Cambio'),('compraConCards','Compra Con Cards')], default='tarjeta', string="Tipo")
    valid_to_change = fields.Boolean('Válido para Cambio', default=False)