# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api
from ast import literal_eval

_logger = logging.getLogger(__name__)

class SaleStockAlert(models.Model):
    _inherit = "sale.order"

# =====================================================================
#   ACTION_CONFIRM(SELF)
#   Método que revisa Stock por cada línea dentro del pedido de venta
# =====================================================================
    def action_confirm(self):
        is_send_email = False
#   Se obtiene el registro de Pedido de Venta
        for sale_order in self:
#   Obtener las líneas dentro de la orden de venta        
            for sale_order_line in sale_order.order_line:
#   Validar que el la líneas del pedido sean consumibles o almacenables
                if sale_order_line.product_id.type in ['product', 'consu']:
#   Obtiene el producto dentro de la línea del pedido de venta
#   Se obtiene la cantidad disponible
                    product = sale_order_line.product_id
                    available_qty = product.virtual_available
                    sale_qty = sale_order_line.product_uom_qty
                    if available_qty < sale_qty:
                        is_send_email = True
#       Confirma la orden y cambia el estatus            
        res = super(SaleStockAlert,self).action_confirm()
        #Validar que la orden de venta esté en estatus "sale" o "done"        
        if sale_order.state == 'sale' or sale_order.state == 'done':
            if is_send_email:
                self.send_email_template()
        
        return res

# =====================================================================
#   SEND_EMAIL_TEMPLATE(SELF)
# =====================================================================    
    def send_email_template(self):
        #Checa si la bandera para el envío de alertas está encendido en los Ajustes del módulo
        send_alert = self.env['ir.config_parameter'].get_param('sale_stock_alert.send_alert')
        alert_email_template_id = int(self.env['ir.config_parameter'].get_param('sale_stock_alert.alert_email_template_id'))
        
        mail_template = self.env['mail.template'].browse(alert_email_template_id)
        # Find the e-mail template
        template = self.env.ref('sale_stock_alert.email_template_stock_alert')
        body = template.body_html
        if send_alert and mail_template:
            email_to = self.get_email_to()           
            if email_to:
                mail_template.write({'email_to': email_to}) #'toh@tohsoluciones.com'})
                mail_template.send_mail(self.id, force_send=True)

# =====================================================================
#   GET_EMAIL_TO(SELF)
# =====================================================================        
    def get_email_to(self):
        ids_user = self.env['ir.config_parameter'].get_param('sale_stock_alert.user_ids')
        lines = False
        if ids_user:
            lines = literal_eval(ids_user)
        if lines:
            email_list = [
                usr.partner_id.email for usr in self.env['res.users'].browse(lines) if usr.partner_id.email]
            return ",".join(email_list)
        else:
            return False