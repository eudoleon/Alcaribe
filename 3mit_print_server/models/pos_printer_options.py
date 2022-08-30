# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime

class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"
    fiscal_print_code = fields.Char(string='Código en la impresora',default='01')
    fiscal_print_name = fields.Char(string='Nombre en la impresora',default='')

class pos_printer(models.TransientModel):
	
	_name = 'pos.printer.options'
	_description = 'Opciones de Impresora Fiscal'
	
	numFacturaInicio=fields.Integer('Nro de Factura Inicial')
	numFacturaFin=fields.Integer('Nro Factura Final')
	#
	reportZ_options = fields.Selection([
		('diario', 'Diario'),
		('numero', 'Por Número'),
		('fecha','Por Fecha')
	], string='Reporte Z', default='diario')
	numZInicio=fields.Integer('Número Inicial')
	numZFin=fields.Integer('Número Final')
	fechaZInicio=fields.Date('Fecha Inicial',default=datetime.today())
	fechaZFin=fields.Date('Fecha Final',default=datetime.today())

	#
	def _printer_host(self):
		active_id = self.env.context.get('active_id')
		if active_id:
			return self.env['pos.config'].browse(active_id).printer_host
		return False
	
	
	printer_host = fields.Char(default=lambda self: self._printer_host()) 


	
	
	