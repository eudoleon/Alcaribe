# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class stock_on_hand(models.Model):
    _inherit = 'purchase.order.line'
    
    qty_available = fields.Float(string='Qty Available', compute='_get_qty_available')
   
    
    

    @api.depends('product_id')
    def _get_qty_available(self):
        qty_line_obj = self.env['product.template']
        for rec in self:       
            qty_available_obj = qty_line_obj.search([['id','=',rec.product_id.product_tmpl_id.id]])
            
            _logger.info('=================================================================')
            _logger.info(qty_available_obj)
            _logger.info('=================================================================')
            
            rec.qty_available = qty_available_obj.qty_available
    
    
    

