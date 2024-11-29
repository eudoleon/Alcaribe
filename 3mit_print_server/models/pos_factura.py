from odoo import models, fields, api
import json

class pos_factura(models.TransientModel):
    _name = 'pos.print.factura'

    def _default_config(self):
        active_id = self.env.context.get('active_id')
        if active_id:
            return self.env['pos.order'].browse(active_id).session_id.config_id
        return False

    config_id = fields.Many2one('pos.config', string='Point of Sale Configuration', default=_default_config)

    printer_host = fields.Char('printer host')

    @api.model
    def getTicket(self, *args):
        order = self.env['pos.order'].browse(self.env.context.get('active_id', False))

        ticket = dict()
        ticket['backendRef'] = order.name
        ticket['idFiscal'] = order.partner_id.vat
        if 'vat' in order.partner_id and order.partner_id.vat:
            ticket['idFiscal'] = order.partner_id.vat
        elif 'identification_id' in order.partner_id and order.partner_id.identification_id:
            ticket['idFiscal'] = order.partner_id.identification_id

        ticket['razonSocial'] = order.partner_id.display_name
        ticket['direccion'] = order.partner_id.contact_address or order.partner_id.city
        ticket['telefono'] = order.partner_id.phone or ""

        items = []
        for line in order.lines:
            item = dict()
            item['referencia_interna'] = line.product_id.default_code
            item['nombre'] = line.display_name
            item['cantidad'] = abs(line.qty)
            item['precio'] = abs(line.price_unit * order.rate_order)
            taxes = line.tax_ids.read()
            if len(taxes) == 0:
                item['impuesto'] = 0
            else:
                item['impuesto'] = abs(taxes[0]['amount'])

            item['descuento'] = abs(line.discount)
            item['comentario'] = line.customer_note or ""  # Añadir comentario aquí
            items.append(item)

        ticket['items'] = items

        payments = []
        for line in order.payment_ids:
            payment_method = line.payment_method_id
            item = {}
            item['codigo'] = payment_method.fiscal_print_code or '01'
            item['nombre'] = payment_method.fiscal_print_name or payment_method.name
            item['monto'] = line.amount * order.rate_order
            payments.append(item)

        ticket['pagos'] = payments

        ticket['comentarios'] = order.note or ""  # Añadir comentarios generales del pedido

        return {
            'printer_host': order.session_id.config_id.printer_host,
            'ticket': json.dumps(ticket)
        }