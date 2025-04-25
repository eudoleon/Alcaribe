# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime

class printer_options_model(models.TransientModel):
    _name = 'printer.options'
    _description = 'Opciones de Impresora Fiscal'
    
    numFacturaInicio = fields.Integer('Nro de Factura Inicial')
    numFacturaFin = fields.Integer('Nro Factura Final')
    
    reportZ_options = fields.Selection([
        ('diario', 'Diario'),
        ('numero', 'Por Número'),
        ('fecha', 'Por Fecha')
    ], string='Reporte Z', default='diario')
    
    numZInicio = fields.Integer('Número Inicial')
    numZFin = fields.Integer('Número Final')
    
    fechaZInicio = fields.Date('Fecha Inicial', default=fields.Date.context_today)
    fechaZFin = fields.Date('Fecha Final', default=fields.Date.context_today)

    printer_host = fields.Char(default='localhost:5000')

    def _compute_printer_host(self):
        for record in self:
            record.printer_host = 'localhost:5000'

