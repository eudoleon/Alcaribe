# -*- coding: utf-8 -*-

from odoo import models

class PosPaymentMethod(models.Model):
    _inherit = 'pos.session'

    def _loader_params_pos_payment_method(self):
    
        result = super()._loader_params_pos_payment_method()
        result['search_params']['fields'].extend(['vpos_methodType','valid_to_change'])        
        return result
