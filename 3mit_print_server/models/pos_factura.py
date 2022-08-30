# -*- coding: utf-8 -*-

from odoo import models, fields, api
import json

class pos_nota_credito(models.TransientModel):
	_name='pos.print.factura'
	
	# 
	def _default_config(self):
		active_id = self.env.context.get('active_id')
		if active_id:
			return self.env['pos.order'].browse(active_id).session_id.config_id
		return False
	
	config_id = fields.Many2one('pos.config', string='Point of Sale Configuration', default=_default_config)

	printer_host=fields.Char('printer host')

	@api.model
	def getTicket(self,*args):		
		order = self.env['pos.order'].browse(self.env.context.get('active_id', False))

		ticket=dict()
		
		ticket['backendRef']=order.name
		
		ticket['idFiscal']=order.partner_id.vat
		if 'rif' in order.partner_id and order.partner_id.rif:
			ticket['idFiscal']=order.partner_id.rif
		elif 'identification_id' in order.partner_id and order.partner_id.identification_id:
			ticket['idFiscal']=order.partner_id.identification_id

		ticket['razonSocial']=order.partner_id.display_name
		ticket['direccion']=order.partner_id.contact_address or order.partner_id.city
		ticket['telefono']=order.partner_id.phone or ""
		
		items=[]
		for line in order.lines:
			item=dict()

			item['nombre']=line.display_name
			item['cantidad']=abs(line.qty)
			item['precio']=line.price_unit
			taxes=line.tax_ids.read()
			if len(taxes)==0:
				item['impuesto']=0
			else:
				item['impuesto']=taxes[0]['amount']
			item['descuento']=line.discount
			item['tipoDescuento']='p'

			items.append(item)

		ticket['items']=items

		payments=[]
		for line in order.payment_ids:
			payment_method=line.payment_method_id
			dict_payment=payment_method.read()[0]
			
			item=dict()
			item['codigo']=dict_payment.get('fiscal_print_code') or ('20' if payment_method.dolar_active else '01')
			item['nombre']=dict_payment.get('fiscal_print_name') or payment_method.name
			item['monto']=line.amount

			payments.append(item)
		
		ticket['pagos']=payments

		return {
			'printer_host':order.session_id.config_id.printer_host,
			'ticket':json.dumps(ticket)
		}
