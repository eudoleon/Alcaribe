    # -*- coding: utf-8 -*-
################################################################################
# Author:  Jesús Pozzo
# Copyleft: 2023-Present.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
#
#
################################################################################
from odoo import models, fields, api, _
import base64
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = "product.template"

    price_bs = fields.Float(string='Precio de venta BS' ,help = "Tasa por servicio",digits='Product Price', currency_field='currency_ref_id')
    currency_ref_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.ref('base.VEF'))
    tax_day  = fields.Float(string='Tasa del dia' ,compute = "_get_tax_day_bcv")


    def getRate(self):
        logging.info("=----------------getRate-------------")
        res_currency_id = self.env['res.currency'].search([('name','=','VEF'),('active','=',True)], limit=1)
        logging.info(res_currency_id)
        if res_currency_id and res_currency_id.rate_ids:
            rate_day = res_currency_id.rate_ids.sorted('name', reverse=True)[:1]
            return round(rate_day.company_rate , 3) 
        else :return 0.000

    def _get_tax_day_bcv(self):
        rate_day = self.getRate()
        if rate_day:
            self.tax_day = rate_day
        else:
            self.tax_day = 0
    

    """
        Actauliza el precio del producto 
    """
    def action_update_price(self):
        rate_day = self.getRate()
        for product in self:
            if rate_day <= 0:
                raise UserError("No se ha encontrado ninguna tasa en VEF registrada")
            if product.list_price <= 0:
               raise UserError("El campo 'Precio en dolar' es obligatorio para calcular el precio con la tasa del día.")
            product.price_bs  = product.list_price *  rate_day
    
    """
        Actauliza el precio de todos los producto , este metodo es utilizado en el Cron
    """
    def action_update_all_price(self,dolar_value):
        if dolar_value <= 0:
            _logger.info("No se ha encontrado ninguna tasa en VEF registrada")
            
        if self.list_price  <= 0:
            _logger.info("El campo 'Precio en dolar' es obligatorio para calcular el precio con la tasa del día.")
        self.price_bs  = self.list_price *  dolar_value

    def show_tax(self):
        res_currency_id = self.env['res.currency'].search([
            ('name','=','VEF'),
            ('active','=',True)
            ],limit =1)
        
        if res_currency_id:
            return {
                'type': 'ir.actions.act_window',
                'name': res_currency_id.name,
                'res_model': 'res.currency',
                'res_id': res_currency_id.id,
                'view_mode': 'form',
                'target': 'self',
                'context': {
                    'form_view_initial_mode': 'edit',
                }
            }
        else:
            raise UserError("LA moneda con código VEF no existe o no esta activa.")

    

    