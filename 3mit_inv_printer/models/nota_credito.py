# -*- coding: utf-8 -*-
from odoo import models, fields, api
import json

class InvoicePrintNotaCredito(models.TransientModel):
    _name = 'invoice.print.notacredito'

    numFactura = fields.Char('Número de Factura', default='', required=True)
    fechaFactura = fields.Char('Fecha de la Factura', required=True)
    serialImpresora = fields.Char('Serial de Impresora', required=True)
    printer_host = fields.Char('Printer Host', required=True, default='localhost:5000')

    @api.model
    def default_get(self, fields):
        res = super(InvoicePrintNotaCredito, self).default_get(fields)
        active_id = self.env.context.get('default_numFactura') or self.env.context.get('active_id')
        if active_id:
            invoice = self.env['account.move'].browse(active_id)
            res.update({
                'numFactura': invoice.ticket_fiscal or '',
                'fechaFactura': invoice.fecha_fiscal or '',
                'serialImpresora': invoice.serial_fiscal or '',
            })
        return res

    @api.model
    def getTicket(self, *args):
        invoice = self.env['account.move'].browse(self.env.context.get('active_id', False))

        tasa = 1
        if invoice.company_id.currency_id != invoice.currency_id:
            tasa = invoice.currency_id._get_conversion_rate(
                invoice.currency_id, invoice.company_id.currency_id,
                invoice.company_id, invoice.invoice_date
            )

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
        payment = {
            'codigo': '01',
            'nombre': 'EFECTIVO 1',  # Nombre predeterminado del método de pago
            'monto': invoice.amount_total_signed,  # Ajustado para usar el monto firmado
        }
        payments.append(payment)
        ticket['pagos'] = payments

        return {
            'ticket': json.dumps(ticket)
        }
