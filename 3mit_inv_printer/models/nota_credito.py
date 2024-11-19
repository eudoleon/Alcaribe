# -*- coding: utf-8 -*-

from odoo import models, fields, api
import json

class inv_nota_credito(models.TransientModel):
    _name = 'invoice.print.notacredito'

    numFactura = fields.Char('Número de Factura', default='', required=True)
    fechaFactura = fields.Char('Fecha de la Factura', required=True)

    serialImpresora = fields.Char('Serial de Impresora', required=True)
    printer_host = fields.Char('printer host', required=True, default='localhost:5000')

    @api.model
    def getTicket(self, *args):
        invoice = self.env['account.move'].browse(self.env.context.get('active_id', False))

        # Calcula la tasa
        tasa = self.currency_id._get_conversion_rate(
            self.currency_id, 
            self.company_id.currency_id, 
            self.company_id, 
            self.invoice_date
        ) if self.currency_id != self.company_id.currency_id else 1

        cliente = invoice.partner_id
        ticket = {
            'fechaFactura': args[0].get('fechaFactura'),
            'nroFactura': args[0].get('numFactura'),
            'serial': args[0].get('serialImpresora'),
            'backendRef': invoice.name,
            'idFiscal': cliente.vat,
            'razonSocial': cliente.name,
            'direccion': cliente.contact_address_complete,
            'telefono': cliente.phone
        }

        items = []
        for line in invoice.invoice_line_ids:
            item = {
                'nombre': line.name,
                'cantidad': line.quantity,
                'precio': line.price_unit * tasa,
                'impuesto': line.tax_ids[0].amount if line.tax_ids else 0
            }
            items.append(item)

        ticket['items'] = items

        # Verificar si existen pagos asociados a la factura
        payments = []
        payment = dict()
        payment['codigo'] = '01'
        payment['nombre'] = 'EFECTIVO 1'  # Nombre predeterminado del método de pago
        payment['monto'] = 'monto': self.amount_total * tasa,

        payments.append(payment)
        ticket['pagos'] = payments

        return {
            'ticket': json.dumps(ticket)
        }
