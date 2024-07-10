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

        tasa = 0
        if invoice.company_id.currency_id == invoice.currency_id:
            tasa = 1
        else:  # VALIDAR TASA
            if tasa == 0:
                tasa = invoice.currency_id._get_conversion_rate(
                    invoice.currency_id, invoice.company_id.currency_id,
                    invoice.company_id, invoice.invoice_date
                )

        cliente = invoice.partner_id
        ticket = dict()
        ticket['fechaFactura'] = args[0].get('fechaFactura')
        ticket['nroFactura'] = args[0].get('numFactura')
        ticket['serial'] = args[0].get('serialImpresora')
        ticket['backendRef'] = invoice.name
        ticket['idFiscal'] = cliente.vat
        ticket['razonSocial'] = cliente.name
        ticket['direccion'] = cliente.contact_address_complete
        ticket['telefono'] = cliente.phone

        items = []
        for line in invoice.invoice_line_ids:
            item = dict()
            item['nombre'] = line.name
            item['cantidad'] = line.quantity
            item['precio'] = line.price_unit * tasa
            taxes = line.tax_ids
            item['impuesto'] = taxes[0].amount if taxes else 0
            items.append(item)

        ticket['items'] = items

        # Conversión a diccionario de información de pagos
        str_payment_ids = invoice.invoice_payments_widget
        str_payment_ids = str_payment_ids.replace("'", "\"")
        payment_ids = json.loads(str_payment_ids)

        payments = []
        for line in payment_ids.get('content'):
            payment_id = self.env['account.payment'].search([('move_id', '=', line.get('move_id'))])
            payment_method = payment_id.payment_method_id
            currency_id = payment_id.currency_id

            payment_method_read = payment_method.read()
            if payment_method_read:
                dict_payment = payment_method_read[0]
                fiscal_print_code = dict_payment.get('fiscal_print_code')
                fiscal_print_name = dict_payment.get('fiscal_print_name')
            else:
                fiscal_print_code = '01'
                fiscal_print_name = payment_method.name

            tasa_payment = currency_id._get_conversion_rate(
                currency_id, invoice.company_id.currency_id,
                invoice.company_id, invoice.invoice_date
            ) if (currency_id.symbol == '$' and currency_id.name == 'USD') else 1

            item = dict()
            item['codigo'] = fiscal_print_code or ('20' if (currency_id.symbol == '$' and currency_id.name == 'USD') else '01')
            item['nombre'] = fiscal_print_name or payment_method.name
            item['monto'] = payment_id.amount * tasa_payment if (currency_id.symbol == '$' and currency_id.name == 'USD') else payment_id.amount
            payments.append(item)

        result_payments = sorted(payments, key=lambda i: (i['codigo'], i['monto']), reverse=True)
        ticket['pagos'] = result_payments

        return {
            'ticket': json.dumps(ticket)
        }