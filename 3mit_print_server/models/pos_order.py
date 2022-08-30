# -*- coding: utf-8 -*-

from odoo import models, fields, api

class PosOrder(models.Model):
	_inherit='pos.order'

	ticket_fiscal=fields.Char()
	serial_fiscal=fields.Char()
	fecha_fiscal=fields.Char()

	@api.depends('ticket_fiscal')
	def _compute_canPrintNC(self):		
		
		self.canPrintNC=False

		if self.isRefund() :
			if self.state in ['draft']:
				self.canPrintNC=False
				return
				
			if self.ticket_fiscal:
				self.canPrintNC= False
				return
			
			origin_name=self.origin_name(self.name)
			origen=self.env['pos.order'].search([('name','=',origin_name)])
			
			if origen.ticket_fiscal :
				self.canPrintNC= True
		
	canPrintNC=fields.Boolean(compute=_compute_canPrintNC)

	def _compute_fiscal_editable(self):		
		self.fiscal_editable = self.ticket_fiscal==False and not self.isRefund()

	fiscal_editable=fields.Boolean(compute=_compute_fiscal_editable)

	def _order_fields(self, ui_order):
		res=super(PosOrder,self)._order_fields(ui_order)
		res['ticket_fiscal']=ui_order.get('ticket_fiscal',False)
		res['serial_fiscal']=ui_order.get('serial_fiscal',False)
		res['fecha_fiscal']=ui_order.get('fecha_fiscal',False)
		return res

	def setTicket(self,data):
		order=self
		if not order:
			order=self.env['pos.order'].search([('pos_reference','like',data.get('orderUID'))])

		order.ticket_fiscal=data.get('nroFiscal')
		order.serial_fiscal=data.get('serial')
		order.fecha_fiscal=data.get('fecha')

		
		if order.account_move : 
			order.account_move.write({
				'ticket_fiscal':order.ticket_fiscal,
				'serial_fiscal':order.serial_fiscal,
				'fecha_fiscal':order.fecha_fiscal
			})

		return data
	
	def print_NC(self):		
		origin_name=self.origin_name(self.name)
		order=self.env['pos.order'].search([('name','=',origin_name)])
		
		fecha=order.fecha_fiscal
		
		return {
			'name': 'Nota de Crédito',
			'type': 'ir.actions.act_window',
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'pos.print.notacredito',
			'view_id': self.env.ref('3mit_print_server.view_print_nc').id,
			'target': 'new',
			'context': {
				'default_numFactura': order.ticket_fiscal,
				'default_serialImpresora':order.serial_fiscal,
				'default_fechaFactura':fecha
        	}
		}

	def print_factura(self):		
		origin_name=self.origin_name(self.name)
		order=self.env['pos.order'].search([('name','=',origin_name)])
		
		fecha=order.fecha_fiscal
		
		return {
			'name': 'Factura',
			'type': 'ir.actions.act_window',
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'pos.print.factura',
			'view_id': self.env.ref('3mit_print_server.view_print_factura').id,
			'target': 'new',
			'context': {
				
				'default_fechaFactura':fecha
        	}
		}
		
	def create(self,values):
		m=values
		# evita copiar los datos del ticket (si este create es por un copy/duplicate/clone)
		if m.get('amount_total',0) < 0:
			m['ticket_fiscal']=False
			m['serial_fiscal']=False
			m['fecha_fiscal']=False

		return super(PosOrder, self).create(m)

	
	# determina si es una devolución
	def isRefund(self):
		#ret= sum([name.find(r) for r in ['REFUND','REEMBOLSO']]) > -1
		ret = self.amount_total < 0
		return ret
	# si self es una devolución, se obtiene el name de la orden
	def origin_name(self,name):
		ret= name.replace('REFUND','').replace('REEMBOLSO','').rstrip()
		return ret
