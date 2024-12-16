# -*- coding: utf-8 -*-

from odoo import fields, models
 
class ResConfigSettings(models.TransientModel):
      _inherit = 'res.config.settings'
 
      pos_vpos = fields.Boolean(related="pos_config_id.vpos",readonly=False)
      pos_vpos_restApi = fields.Char(related="pos_config_id.vpos_restApi" , readonly=False)
 
      def set_values(self):
             super().set_values()
             payment_methods = self.env['pos.payment.method']
             if not self.pos_vpos:
                    payment_methods |= payment_methods.search([('use_payment_terminal', '=', 'vpos')])
                    payment_methods.write({'use_payment_terminal': self.pos_vpos})