# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
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

        tasa = 1
        if invoice.company_id.currency_id != invoice.currency_id:
            tasa = invoice.currency_id._get_conversion_rate(
                invoice.currency_id, invoice.company_id.currency_id,
                invoice.company_id, invoice.invoice_date
            )

        # Validación de pagos parciales
        if invoice.es_pago_parcial:
            suma = invoice.monto_parcial_1 + invoice.monto_parcial_2
            if round(suma, 2) != round(invoice.amount_total, 2):
                raise UserError("La suma de los pagos parciales no coincide con el total de la nota de crédito.")

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
            items.append({
                'nombre': line.name,
                'cantidad': line.quantity,
                'precio': line.price_unit * tasa,
                'impuesto': line.tax_ids[0].amount if line.tax_ids else 0,
                'descuento': line.discount,
                'tipoDescuento': 'p'
            })

        ticket['items'] = items

        # Pagos
        pagos = []
        if invoice.es_pago_parcial:
            pagos.append({
                'codigo': '20' if invoice.divisa_monto == 'monto_parcial_1' else '01',
                'nombre': 'EFECTIVO',
                'monto': invoice.monto_parcial_1 * tasa
            })

            codigo_monto_2 = '01' if invoice.retencion else '01'
            pagos.append({
                'codigo': codigo_monto_2,
                'nombre': 'EFECTIVO',
                'monto': invoice.monto_parcial_2 * tasa
            })
        else:
            monto_final = self.monto * tasa
            codigo_pago = '20' if self.es_pago_en_divisa else '01'

            pagos.append({
                'codigo': codigo_pago,
                'nombre': 'EFECTIVO',
                'monto': monto_final,
            })

        ticket['pagos'] = pagos

        return {
            'ticket': json.dumps(ticket)
        }
