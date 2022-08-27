import logging
from odoo import api, fields, models, _
from ast import literal_eval

_logger = logging.getLogger(__name__)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    send_alert = fields.Boolean("Envío de email por falta de stock")
    alert_email_template_id = fields.Many2one('mail.template', string='Alert Email Template',
                                            domain="[('model', '=', 'sale.order')]",
                                            help="Email enviado cuando no hay existencias al momento de la venta.")
    user_ids = fields.Many2many('res.users', string='Alertar a')

# ==================================
#   SET_VALUES(SELF)
# ==================================
    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        
        template_id = self.alert_email_template_id and self.alert_email_template_id.id or False
        ids_user = self.user_ids and self.user_ids.ids or False
                    
        self.env['ir.config_parameter'].sudo().set_param('sale_stock_alert.send_alert', self.send_alert)
        self.env['ir.config_parameter'].sudo().set_param('sale_stock_alert.alert_email_template_id', int(template_id))
        self.env['ir.config_parameter'].set_param('sale_stock_alert.user_ids', self.user_ids.ids)
        return res

# ==================================
#   GET_VALUES(SELF)
# ==================================
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        
        ids_user = self.env['ir.config_parameter'].get_param('sale_stock_alert.user_ids')
                
        lines = False
        if ids_user:
            lines = [(6, 0, literal_eval(ids_user))]
        
        res.update(
            send_alert = self.env['ir.config_parameter'].get_param('sale_stock_alert.send_alert'),
            alert_email_template_id = int(self.env['ir.config_parameter'].get_param('sale_stock_alert.alert_email_template_id')),
            user_ids = lines, #[(6, 0, lines)],
        )
        return res