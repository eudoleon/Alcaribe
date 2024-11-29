# -*- coding: utf-8 -*-
from odoo import models, fields, osv , api
from odoo.exceptions import UserError, ValidationError,Warning
import logging
import requests
from decimal import Decimal, ROUND_DOWN
_logger = logging.getLogger(__name__)



class accountPaymnent(models.Model):
    _inherit = 'account.payment'

    currency_ref_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.ref('base.VEF'))

    @api.model
    def getRate(self):
        res_currency_id = self.env['res.currency'].sudo().search([('name','=','VEF'),('active','=',True)], limit=1)
        if res_currency_id and res_currency_id.rate_ids:
            rate_day = res_currency_id.rate_ids.sorted('name', reverse=True)[:1]
            tx = Decimal(str(rate_day.company_rate))
            tx_amount = tx.quantize(Decimal('1.00'), rounding=ROUND_DOWN)
            return tx_amount
        else :
            return   3.00

    tax_day  = fields.Monetary(
        string='Tasa del día', 
        digits=(16, 3),
        currency_field='currency_ref_id',
        default = getRate,
    )

    amount_total_bs = fields.Monetary(
        string="Importe en  BS.", 
        store=True, 
        compute='_compute_amounts_bs', 
        currency_field='currency_ref_id',
        tracking=4)
    
    rel_code_currency_id  = fields.Char(related = 'currency_id.name',string='Codigo moneda')

    # partner_id = fields.Many2one('res.partner', string='Partner', related='order_id.partner_id')

    @api.depends('tax_day', 'amount')
    def _compute_amounts_bs(self):
        for payment in self:
            if payment.tax_day > 0:
                if payment.rel_code_currency_id == 'USD':
                    payment.amount_total_bs = round(
                        round(payment.amount, 3) * round(payment.tax_day, 3), 3)  # Dividir amount entre tax_day
                elif payment.rel_code_currency_id == 'VEF':  # Verificar si la moneda es VEF
                    payment.amount_total_bs = round(
                        round(payment.amount, 3) / round(payment.tax_day, 3), 3)  # Dividir amount entre tax_day
            else:
                payment.amount_total_bs = 0.000
