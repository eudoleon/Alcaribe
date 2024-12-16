# -*- coding: utf-8 -*-

from odoo import models, fields, api
import json

class inv_nota_credito(models.TransientModel):
    _name = 'invoice.print.notacredito'

    es_pago_en_divisa = fields.Boolean(string="¿Es Pago en Divisa?")


    numFactura = fields.Char('Número de Factura', default='', required=True)
    fechaFactura = fields.Date('Fecha de la Factura', required=True)
    serialImpresora = fields.Char('Serial de Impresora', required=True)
    printer_host = fields.Char('printer host', required=True, default='localhost:5000')

    @api.model
    def getTicket(self, *args):
        invoice = self.env['account.move'].browse(self.env.context.get('active_id', False))

        # Calcular la tasa de conversión
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
                'impuesto': line.tax_ids[0].amount if line.tax_ids else 0,
                'descuento': line.discount,
                'tipoDescuento': 'p'
            }
            items.append(item)

        ticket['items'] = items

        pagos = []
        pagos.append({
            'codigo': '20' if self.es_pago_en_divisa else '01',
            'nombre': 'EFECTIVO',
            'monto': self.amount_total * tasa,
        })
        ticket['pagos'] = pagos

        return {
            'ticket': json.dumps(ticket)  # Ajuste aquí, regresamos el JSON del ticket
        }

