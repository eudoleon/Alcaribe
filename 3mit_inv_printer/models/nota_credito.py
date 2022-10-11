# -*- coding: utf-8 -*-

from odoo import models, fields, api
import json


class inv_nota_credito(models.TransientModel):
    _name = 'invoice.print.notacredito'

    #
    numFactura = fields.Char('Número de Factura', default='', required=True)
    fechaFactura = fields.Char('Fecha de la Factura', required=True)

    serialImpresora = fields.Char('Serial de Impresora', required=True)
    printer_host = fields.Char('printer host', required=True, default='localhost:5000')

    @api.model
    def getTicket(self, *args):
        invoice = self.env['account.move'].browse(self.env.context.get('active_id', False))

        tasa = 0
        # date = invoice.currency_bs_date or invoice.currency_id.date
        if invoice.company_id.currency_id == invoice.currency_id:
            tasa = 1
        else: ##VALIDAR TASA
            if tasa == 0:
                tasa = invoice.currency_id._get_conversion_rate(invoice.currency_id, invoice.company_id.currency_id,
                                                                invoice.company_id, invoice.invoice_date)

        cliente = invoice.partner_id
        ticket = dict()
        ticket['fechaFactura'] = args[0].get('fechaFactura')
        ticket['nroFactura'] = args[0].get('numFactura')
        ticket['serial'] = args[0].get('serialImpresora')
        ticket['backendRef'] = invoice.name

        # ticket['backendRef']=invoice.name
        ticket['idFiscal'] = cliente.vat

        ticket['razonSocial'] = cliente.name  # self.commercial_partner_id.commercial_company_name
        ticket['direccion'] = cliente.contact_address_complete  # self.commercial_partner_id.contact_address or self.commercial_partner_id.city
        ticket['telefono'] = cliente.phone  # self.commercial_partner_id.phone

        items = []
        for line in invoice.invoice_line_ids:
            item = dict()
            item['nombre'] = line.name  # line.name.splitlines()[0]
            item['cantidad'] = line.quantity
            item['precio'] = line.price_unit * tasa
            # taxes=line.tax_ids.read()
            taxes = line.tax_ids
            if len(taxes) == 0:
                item['impuesto'] = 0
            else:
                item['impuesto'] = taxes[0].amount

            items.append(item)

        ticket['items'] = items

        # Conversion a diccionario informacion de pagos
        str_payment_ids = invoice.invoice_payments_widget
        str_payment_ids = str_payment_ids.replace("'", "\"")
        payment_ids = json.loads(str_payment_ids)

        payments = []
        for line in payment_ids.get('content'):
            payment_id = self.env['account.payment'].search([('move_id', '=', line.get('move_id'))])

            payment_method = payment_id.payment_method_id
            currency_id = payment_id.currency_id
            dict_payment = payment_method.read()[0]
            tasa_payment = currency_id._get_conversion_rate(currency_id, invoice.company_id.currency_id,
                                                            invoice.company_id, invoice.invoice_date) if (
                        currency_id.symbol == '$' and currency_id.name == 'USD') else 1

            item = dict()
            # item['codigo'] = dict_payment.get('fiscal_print_code') or ('20' if payment_method.dolar_active else '01')
            item['codigo'] = dict_payment.get('fiscal_print_code') or (
                '20' if (currency_id.symbol == '$' and currency_id.name == 'USD') else '01')
            item['nombre'] = dict_payment.get('fiscal_print_name') or payment_method.name
            item['monto'] = payment_id.amount * tasa_payment if (currency_id.symbol == '$' and currency_id.name == 'USD') else payment_id.amount  # NOTA VALIDAR SI ES $ CONVERTIRLO EN BOLIVARES (EN ESPERA DE CAMPO TASA)

            payments.append(item)

        # result_payments = sorted(payments, key=lambda i: (i['codigo'], i['monto']))
        result_payments = sorted(payments, key=lambda i: (i['codigo'], i['monto']), reverse=True)

        ticket['pagos'] = result_payments

        return {
            'ticket': json.dumps(ticket)
        }
