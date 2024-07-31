# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime
import json


class AccountMove(models.Model):
    _inherit = 'account.move'

    serial_fiscal = fields.Char()
    fecha_fiscal = fields.Char()
    ticket_fiscal = fields.Char()

    #
    @api.depends('ticket_fiscal')
    def _compute_canPrintFF(self):
        self.canPrintFF = False
        if self.move_type == 'out_invoice':
            if self.ticket_fiscal:
                self.canPrintFF = False
            else:
                if self.state == 'posted' and self.payment_state in ['reversed', 'in_payment', 'paid']:
                    self.canPrintFF = True

    @api.depends('ticket_fiscal')
    def _compute_canPrintNC(self):
        self.canPrintNC = False
        if self.move_type == 'out_refund':
            if self.ticket_fiscal:
                self.canPrintNC = False
            else:
                origen = self.reversed_entry_id

                if origen.ticket_fiscal and self.state == 'posted' and self.payment_state in ['reversed', 'in_payment', 'paid']:
                    self.canPrintNC = True

    canPrintFF = fields.Boolean(compute=_compute_canPrintFF)
    canPrintNC = fields.Boolean(compute=_compute_canPrintNC)

    def printFactura(self):

        tasa = 0#self.currency_bs_rate
        # date = self.currency_bs_date or self.currency_id.date
        if self.company_id.currency_id == self.currency_id:
            tasa = 1
        else:
            if tasa == 0:
                tasa = self.currency_id._get_conversion_rate(self.currency_id, self.company_id.currency_id,
                                                             self.company_id, self.invoice_date)


        cliente = self.partner_id
        ticket = dict()
        ticket['fechaFactura'] = datetime.now().strftime('%Y-%m-%d %H:%S')

        ticket['backendRef'] = self.name
        ticket['idFiscal'] = cliente.vat #cliente.rif or cliente.identification_id

        ticket['razonSocial'] = cliente.name  # self.commercial_partner_id.commercial_company_name
        ticket['direccion']=cliente.contact_address_complete # self.commercial_partner_id.contact_address or self.commercial_partner_id.city
        ticket['telefono'] = cliente.phone  # self.commercial_partner_id.phone

        items = []
        for line in self.invoice_line_ids:
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
            item['descuento'] = line.discount
            item['tipoDescuento'] = 'p'

            items.append(item)

        ticket['items'] = items

        # Conversion a diccionario informacion de pagos
        str_payment_ids = self.invoice_payments_widget
        str_payment_ids = str_payment_ids.replace("'", "\"")
        payment_ids = json.loads(str_payment_ids)

        payments = []
        for line in payment_ids.get('content'):
            payment_id = self.env['account.payment'].search([('move_id', '=', line.get('move_id'))])

            payment_method = payment_id.payment_method_id
            currency_id = payment_id.currency_id
            dict_payment = payment_method.read()[0]
            tasa_payment = currency_id._get_conversion_rate(currency_id, self.company_id.currency_id,
                                self.company_id, self.invoice_date) if (currency_id.symbol == '$' and currency_id.name == 'USD') else 1

            item = dict()
            # item['codigo'] = dict_payment.get('fiscal_print_code') or ('20' if payment_method.dolar_active else '01')
            item['codigo'] = dict_payment.get('fiscal_print_code') or (
                '20' if (currency_id.symbol == '$' and currency_id.name == 'USD') else '01')
            item['nombre'] = dict_payment.get('fiscal_print_name') or payment_method.name
            item['monto'] = payment_id.amount * tasa_payment if (currency_id.symbol == '$' and currency_id.name == 'USD') else payment_id.amount

            payments.append(item)

        # result_payments = sorted(payments, key=lambda i: (i['codigo'], i['monto']))
        result_payments = sorted(payments, key=lambda i: (i['codigo'], i['monto']), reverse=True)

        ticket['pagos'] = result_payments

        return {
            'res_model': 'account.move',
            'type': 'ir.actions.client',
            'tag': 'printFactura',
            'target': 'new',
            'data': ticket
        }

    def print_NC(self):
        invoice = self.reversed_entry_id
        fecha = invoice.fecha_fiscal
        return {
            'name': 'nota de crédito',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'invoice.print.notacredito',
            'view_id': self.env.ref('3mit_inv_printer.view_print_nc').id,
            'target': 'new',
            'context': {
                'default_numFactura': invoice.ticket_fiscal,
                'default_serialImpresora': invoice.serial_fiscal,
                'default_fechaFactura': fecha
            }
        }

    def setTicket(self, data):
        info = data.get('data')
        self.write({
            'ticket_fiscal': info.get('nroFiscal'),
            'serial_fiscal': info.get('serial'),
            'fecha_fiscal': info.get('fecha')
        })
        return data

    @api.model_create_multi
    def create(self, values):
        # out_refund es una copia, entonces aquí se inicializan valores de impresora fiscal
        for m in values:
            if m.get('move_type') == 'out_refund':
                m['ticket_fiscal'] = False
                m['serial_fiscal'] = False
                m['fecha_fiscal'] = False

        return super(AccountMove, self).create(values)
