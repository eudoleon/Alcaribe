# -*- coding: utf-8 -*-

from odoo import models, fields

class XPosFiscalPrinter(models.Model):
    _name = "x.pos.fiscal.printer"
    _description = "Impresora fiscal"

    name = fields.Char("Nombre")
    serial = fields.Char("Serial")
    serial_port = fields.Char("Puerto serial")
    #campo seleccion con los flags de la impresora fiscal, 00, 30
    flag_21 = fields.Selection([('00', '00'), ('30', '30')], string="Flag 21", default='00', required=True)

    #seleccion de conexion, serial, usb, api
    connection_type = fields.Selection([('serial', 'Serial'), ('usb', 'USB'), ('usb_serial', 'USB Serial'),('file', 'Archivo'), ('api', 'API')],
                                       string="Tipo de conexión", default='usb_serial', required=True)

    #url de la api
    api_url = fields.Char("URL de la API")

