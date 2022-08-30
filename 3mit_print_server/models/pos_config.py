# -*- coding: utf-8 -*-

from odoo import models, fields, api

class pos_printer(models.Model):
    _inherit='pos.config'

    printer_host=fields.Char('Host',help='host:port')
    printer_port=fields.Char('Puerto Serial',help='Puerto Serial al que se conectó la Impresora')
    printer_serial=fields.Char('Serial MH',help='Número Serial de la Impresora')
