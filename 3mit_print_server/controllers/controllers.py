# -*- coding: utf-8 -*-
from odoo import http
@http.route('/pos/get_payment_method_data', type='json', auth='public') 
def get_payment_method_data(self, name):
    method = self.env['pos.payment.method'].search([('name', '=', name)], limit=1)
    return {
        'dolar_active': method.dolar_active, 
        'fiscal_print_code': method.fiscal_print_code
    }
