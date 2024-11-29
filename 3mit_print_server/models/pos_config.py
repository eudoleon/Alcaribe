# -*- coding: utf-8 -*-

from odoo import models, fields, api

class pos_printer(models.Model):
    _inherit='pos.config'

    printer_host=fields.Char('Host Custom',help='host:port')
    printer_port=fields.Char('Puerto Serial custom',help='Puerto Serial al que se conectó la Impresora')
    printer_serial=fields.Char('Serial MH custom',help='Número Serial de la Impresora')



class pos_printerConfig(models.TransientModel):
    _inherit='res.config.settings'

    printer_host=fields.Char(related='pos_config_id.printer_host',readonly=False,help='host:port')
    printer_port=fields.Char(related='pos_config_id.printer_port',readonly=False,help='Puerto Serial al que se conectó la Impresora')
    printer_serial=fields.Char(related='pos_config_id.printer_serial',readonly=False,help='Número Serial de la Impresora')
