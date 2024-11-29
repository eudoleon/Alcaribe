    # -*- coding: utf-8 -*-
################################################################################
# Author: ICIVA || Jesús Pozzo
# Copyleft: 2023-Present.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
#
#
################################################################################
from odoo import models, fields, api, _
import base64
from odoo.exceptions import UserError

import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime

_logger = logging.getLogger(__name__)

class ResCurrency(models.Model):
    _inherit = "res.currency"
    act_productos  = fields.Boolean(string='Actualizar Productos')
    server_tax  = fields.Selection([('bcv', 'Banco Central De Venezuela'),] , string='Servidor',default ="bcv")
    
    def sud_check_today_rate(self):
        today = datetime.now().date().strftime('%Y-%m-%d')
        rate = self.rate_ids.filtered(lambda r: r.name.strftime('%Y-%m-%d') == today)
        return rate if rate else False

    
    """
        Este metodo Actualiza los precios de los productos de acuerdo a la ultima tasa registrada.
    """

    def action_update_prices(self):
        if not self.rate_ids:
            raise UserError("Debe agregar una Tasa Para poder actualizar los precios.")
        rate_day = round(self.rate_ids.sorted('name', reverse=True)[:1].company_rate,3)
        product_tmp_ids = self.env['product.template'].search([])
        for product_tmp in product_tmp_ids:
            product_tmp.action_update_all_price(rate_day)
        mensaje = """
                    <br></br>
                    <span>los precios de los productos fueron actualizado con la tasa BCV.</span>
        """
        channel = self.env['mail.channel'].search([('name','=','Tasa de Cambio')])
        if channel:
            subtye = self.env.ref('mail.mt_comment')
            channel.message_post(body= mensaje, message_type='comment')

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Acción completada',
                'message': 'La acción ha sido ejecutada exitosamente. Tasa {}'.format(rate_day),
                'sticky': False,
            }
        }
         

    """
        Toma la tasa oficial de la pagina BCV y lo agrega , se realiza el search porque se agrego en el cron y no crear un nuevo metodo.
    """
    def action_get_tax_BCV(self):

        currency = self.env['res.currency'].search([('name','=','USD')],limit = 1)
            
        if currency:
            if not currency.server_tax :
                raise UserError(f"Seleccione Servidor para el calculo de la tasa del dia.")
    
            if currency.server_tax == 'bcv':
                url = "https://www.bcv.org.ve/tasas-informativas-sistema-bancario"
                response = requests.get(url, verify=False)
                logging.info(response.status_code)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, "html.parser")
                    dolar_element = soup.find("div", {"id": "dolar"})
                    dolar_value = float(dolar_element.text.strip().replace('USD', '').replace('\n', '').replace(' ', '').replace(',', '.'))
                    today_rate = self.sud_check_today_rate()
                    logging.info(today_rate)
                    if today_rate:
                        today_rate.company_rate = round(dolar_value,2)
                    else:
                        self.rate_ids = [(0,0,{
                            'name':datetime.now().date(),
                            'company_rate':round(dolar_value,2),
                            'currency_id':currency.id
                        })]
                    mensaje = "<h4>Actualizacion de Tasa BCV : {}</h4>".format(round(dolar_value,3))
                    #Al actualizar la tasa , actualiza el precio de todos los productos.
                  

                    channel = self.env['mail.channel'].search([('name','=','Tasa de Cambio')])
                    if channel:
                        subtye = self.env.ref('mail.mt_comment')
                        channel.message_post(body= mensaje, message_type='comment')
                    
                else:
                    raise UserError(f"Error al realizar la solicitud: {response.status_code}")
    

    """
        Pila Con esto debe ser momentanio y entener bien la logica ,ya que no permite agregar la tasa manual cuando funciona
        con el servicio de agregar la tasa automatica con bcv.    
    """
    class InheritCurrencyRate(models.Model):
        _inherit = "res.currency.rate"
        @api.onchange('company_rate')
        def _onchange_rate_warning(self):
            latest_rate = self._get_latest_rate()
            if latest_rate:
                diff = (latest_rate.rate - self.rate) / latest_rate.rate
                # logging.info(diff)
                # if abs(diff) > 0.2:
                #     return {
                #         'warning': {
                #             'title': _("Warning for %s", self.currency_id.name),
                #             'message': _(
                #                 "The new rate is quite far from the previous rate.\n"
                #                 "Incorrect currency rates may cause critical problems, make sure the rate is correct !"
                #             )
                #         }
                #     }