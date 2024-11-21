from odoo import models, fields, api
from datetime import datetime


class AccountMove(models.Model):
    _inherit = 'account.move'

    serial_fiscal = fields.Char()
    fecha_fiscal = fields.Char()
    ticket_fiscal = fields.Char()
    es_pago_en_divisa = fields.Boolean(string="¿Es Pago en Divisa?")

    @api.depends('ticket_fiscal', 'state', 'payment_state')
    def _compute_canPrintFF(self):
        for record in self:
            record.canPrintFF = False
            if record.move_type == 'out_invoice' and record.state == 'posted' and not record.ticket_fiscal:
                record.canPrintFF = True

    @api.depends('ticket_fiscal', 'state', 'payment_state', 'reversed_entry_id')
    def _compute_canPrintNC(self):
        for record in self:
            record.canPrintNC = False
            if record.move_type == 'out_refund' and record.state == 'posted' and not record.ticket_fiscal:
                if record.reversed_entry_id and record.reversed_entry_id.ticket_fiscal:
                    record.canPrintNC = True

    canPrintFF = fields.Boolean(compute=_compute_canPrintFF)
    canPrintNC = fields.Boolean(compute=_compute_canPrintNC)

    def printFactura(self):
        # Calcula la tasa
        tasa = self.currency_id._get_conversion_rate(
            self.currency_id, 
            self.company_id.currency_id, 
            self.company_id, 
            self.invoice_date
        ) if self.currency_id != self.company_id.currency_id else 1

        cliente = self.partner_id
        ticket = {
            'fechaFactura': datetime.now().strftime('%Y-%m-%d %H:%S'),
            'backendRef': self.name,
            'idFiscal': cliente.vat or "",
            'razonSocial': cliente.name,
            'direccion': cliente.contact_address_complete,
            'telefono': cliente.phone or "",
            'items': [],
        }

        # Construir los ítems de la factura
        for line in self.invoice_line_ids:
            taxes = line.tax_ids[:1]  # Toma solo el primer impuesto
            item = {
                'nombre': line.name,
                'cantidad': line.quantity,
                'precio': line.price_unit * tasa,
                'impuesto': taxes.amount if taxes else 0,
                'descuento': line.discount,
                'tipoDescuento': 'p',
            }
            ticket['items'].append(item)

        # Calcula el monto basado en el total de la factura y la tasa
        pagos = []
        pagos.append({
            'codigo': '20' if self.es_pago_en_divisa else '01',
            'nombre': 'EFECTIVO',
            'monto': self.amount_total * tasa,  # Usando el total de la factura multiplicado por la tasa
        })
        ticket['pagos'] = pagos

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
        info = data.get('data', {})
        self.write({
            'ticket_fiscal': info.get('nroFiscal'),
            'serial_fiscal': info.get('serial'),
            'fecha_fiscal': info.get('fecha'),
        })
        return data

    @api.model_create_multi
    def create(self, values):
        for m in values:
            if m.get('move_type') == 'out_refund':
                m.update({
                    'ticket_fiscal': False,
                    'serial_fiscal': False,
                    'fecha_fiscal': False,
                })
        return super(AccountMove, self).create(values)
