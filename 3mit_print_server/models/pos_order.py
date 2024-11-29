# -*- coding: utf-8 -*-

from odoo import models, fields, api

class PosSession(models.Model):
    _inherit = "pos.session"

    def _pos_ui_models_to_load(self):
        result = super()._pos_ui_models_to_load()
        result += ['pos.order']
        return result

    def _loader_params_pos_order(self):
        return {
            'search_params': {
                'fields': ['rate_order'],
            }
        }

    def _get_pos_ui_pos_order(self, params):
        return self.env['pos.order'].search_read(**params['search_params'])

    def _loader_params_res_partner(self):
        res = super(PosSession, self)._loader_params_res_partner()
        fields = res.get('search_params').get('fields')
        fields.extend(["vat"])
        res['search_params']['fields'] = fields
        return res

class AccountMove(models.Model):
    _inherit = 'account.move'

    ticket_fiscal_pos = fields.Char(
        string='Ticket Fiscal POS', 
        related='pos_order_id.ticket_fiscal', 
        readonly=True,
        store=True  # Opcional, depende de si necesitas almacenar este valor en la base de datos para búsquedas o reportes
    )
    serial_impresora_pos = fields.Char(
        string='Serial Impresora POS', 
        related='pos_order_id.serial_fiscal', 
        readonly=True,
        store=True  # Opcional, depende de si necesitas almacenar este valor en la base de datos para búsquedas o reportes
    )

class PosOrder(models.Model):
    _inherit = 'pos.order'

    ticket_fiscal = fields.Char()
    serial_fiscal = fields.Char()
    fecha_fiscal = fields.Char()

    @api.depends('ticket_fiscal')
    def _compute_canPrintNC(self):
        self.canPrintNC = False
        self.canPrint = False

        if self.isRefund():
            if self.state in ['draft']:
                self.canPrintNC = False
                self.canPrint = False
                return

            if self.ticket_fiscal:
                self.canPrintNC = False
                self.canPrint = False
                return

            origin_name = self.origin_name(self.name)
            origen = self.env['pos.order'].search([('name', '=', origin_name)])

            if origen.ticket_fiscal:
                self.canPrintNC = True
                self.canPrint = False
        else:
            if self.state in ['draft']:
                self.canPrint = False
                self.canPrint = False
                return
            else:
                self.canPrintNC = False
                self.canPrint = True
                return

    canPrintNC = fields.Boolean(compute=_compute_canPrintNC)
    canPrint = fields.Boolean(compute=_compute_canPrintNC)

    def _compute_fiscal_editable(self):
        self.fiscal_editable = self.ticket_fiscal == False and not self.isRefund()

    fiscal_editable = fields.Boolean(compute=_compute_fiscal_editable)

    def _order_fields(self, ui_order):
        res = super(PosOrder, self)._order_fields(ui_order)
        res['ticket_fiscal'] = ui_order.get('ticket_fiscal', False)
        res['serial_fiscal'] = ui_order.get('serial_fiscal', False)
        res['fecha_fiscal'] = ui_order.get('fecha_fiscal', False)
        return res

    def setTicket(self, data):
        order = self
        if not order:
            order = self.env['pos.order'].search([('pos_reference', 'like', data.get('orderUID'))])

        order.ticket_fiscal = data.get('nroFiscal')
        order.serial_fiscal = data.get('serial')
        order.fecha_fiscal = data.get('fecha')
        return data

    def _prepare_invoice_vals(self):
        res = super(PosOrder, self)._prepare_invoice_vals()
        if self.igtf_amount >= 0:
            line = self._prepare_igtf_invoice_line()
            inv_lines = res.get('invoice_line_ids')
            inv_lines.append((0, None, line))
            res.update({
                'invoice_line_ids': inv_lines,
                'pos_order_id': self.id,
                'ticket_fiscal_pos': self.ticket_fiscal
            })
        return res

    def print_NC(self):
        origin_name = self.origin_name(self.name)
        order = self.env['pos.order'].search([('name', '=', origin_name)])
        fecha = order.fecha_fiscal
        return {
            'name': 'Nota de Crédito',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'pos.print.notacredito',
            'view_id': self.env.ref('3mit_print_server.view_print_nc').id,
            'target': 'new',
            'context': {
                'default_numFactura': order.ticket_fiscal,
                'default_serialImpresora': order.serial_fiscal,
                'default_fechaFactura': order.fecha_fiscal
            }
        }

    def print_factura(self):
        origin_name = self.origin_name(self.name)
        order = self.env['pos.order'].search([('name', '=', origin_name)])
        fecha = order.fecha_fiscal
        return {
            'name': 'Factura',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'pos.print.factura',
            'view_id': self.env.ref('3mit_print_server.view_print_factura').id,
            'target': 'new',
            'context': {
                'default_fechaFactura': fecha
            }
        }

    def create(self, values):
        m = values
        if m.get('amount_total', 0) < 0:
            m['ticket_fiscal'] = False
            m['serial_fiscal'] = False
            m['fecha_fiscal'] = False
        return super(PosOrder, self).create(m)

    def isRefund(self):
        ret = self.amount_total < 0
        return ret

    def origin_name(self, name):
        ret = name.replace('REFUND', '').replace('REEMBOLSO', '').rstrip()
        return ret

    def get_rate_order(self, pos_reference):
        var = self.env['pos.order'].search([('pos_reference', '=', pos_reference)])
        if var:
            return var.rate_order
        else:
            currency_id = self.env['res.currency'].search([('name', '=', 'VEF')])
            return currency_id.rate
