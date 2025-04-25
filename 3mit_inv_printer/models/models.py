# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime
import json
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    serial_fiscal = fields.Char()
    fecha_fiscal = fields.Char()
    ticket_fiscal = fields.Char()
    es_pago_en_divisa = fields.Boolean(string="¿Es Pago en Divisa?")
    es_pago_parcial = fields.Boolean(string="¿Es Pago Parcial?")
    monto = fields.Float(string="Monto de Pago")
    monto_parcial_1 = fields.Float(string="Monto de Pago Parcial 1")
    monto_parcial_2 = fields.Float(string="Monto de Pago Parcial 2")
    divisa_monto = fields.Selection([
        ('monto_parcial_1', "Monto Parcial 1"),
        ('monto_parcial_2', "Monto Parcial 2")
    ], string="Monto en Divisa")
    retencion = fields.Boolean(string="¿Aplicar Retención?")

    @api.depends('ticket_fiscal')
    def _compute_canPrintFF(self):
        self.canPrintFF = True
        if self.move_type == 'out_invoice':
            if self.ticket_fiscal:
                self.canPrintFF = False
            else:
                if self.state == 'posted' and self.payment_state in ['reversed', 'in_payment']:
                    self.canPrintFF = True

    @api.depends('ticket_fiscal')
    def _compute_canPrintNC(self):
        self.canPrintNC = False
        if self.move_type == 'out_refund':
            if self.ticket_fiscal:
                self.canPrintNC = False
            else:
                origen = self.reversed_entry_id
                if origen.ticket_fiscal and self.state == 'posted' and self.payment_state in ['reversed', 'in_payment']:
                    self.canPrintNC = True

    canPrintFF = fields.Boolean(compute=_compute_canPrintFF)
    canPrintNC = fields.Boolean(compute=_compute_canPrintNC)

    def printFactura(self):
        # Validación para pagos parciales
        if self.es_pago_parcial:
            suma = self.monto_parcial_1 + self.monto_parcial_2
            if round(suma, 2) != round(self.amount_total, 2):
                raise UserError("La suma de los montos parciales no coincide con el monto total de la factura.")

        tasa = self.currency_id._get_conversion_rate(
            self.currency_id,
            self.company_id.currency_id,
            self.company_id,
            self.invoice_date
        ) if self.currency_id != self.company_id.currency_id else 1

        cliente = self.partner_id
        ticket = {
            'fechaFactura': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'backendRef': self.name,
            'idFiscal': cliente.vat,
            'razonSocial': cliente.name,
            'direccion': cliente.contact_address_complete,
            'telefono': cliente.phone,
            'items': [],
        }

        for line in self.invoice_line_ids:
            taxes = line.tax_ids
            ticket['items'].append({
                'nombre': line.name,
                'cantidad': line.quantity,
                'precio': line.price_unit * tasa,
                'impuesto': taxes[0].amount if taxes else 0,
                'descuento': line.discount,
                'tipoDescuento': 'p',
            })

        pagos = []
        if self.es_pago_parcial:
            pagos.append({
                'codigo': '20' if self.divisa_monto == 'monto_parcial_1' else '01',
                'nombre': 'EFECTIVO',
                'monto': self.monto_parcial_1 * tasa,
            })

            codigo_monto_2 = '01' if self.retencion else '01'
            pagos.append({
                'codigo': codigo_monto_2,
                'nombre': 'EFECTIVO',
                'monto': self.monto_parcial_2 * tasa,
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
            'res_model': 'account.move',
            'type': 'ir.actions.client',
            'tag': 'printFactura',
            'target': 'new',
            'context': {
                'data': ticket
            }
        }

    def print_NC(self):
        invoice = self.reversed_entry_id
        fecha = invoice.invoice_date
        return {
            'name': 'nota de crédito',
            'type': 'ir.actions.act_window',
            'res_model': 'invoice.print.notacredito',
            'view_mode': 'form',
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
        if info:
            self.write({
                'ticket_fiscal': info.get('nroFiscal'),
                'serial_fiscal': info.get('serial'),
                'fecha_fiscal': info.get('fecha')
            })
        return data

    @api.model_create_multi
    def create(self, values):
        for m in values:
            if m.get('move_type') == 'out_refund':
                m['ticket_fiscal'] = False
                m['serial_fiscal'] = False
                m['fecha_fiscal'] = False
        return super(AccountMove, self).create(values)