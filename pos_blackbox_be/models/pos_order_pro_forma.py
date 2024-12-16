# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from dateutil import parser
from datetime import datetime


class PosOrderLineProFormaBe(models.Model):
    _name = 'pos.order_line_pro_forma_be'  # needs to be a new class
    _inherit = 'pos.order.line'
    _description = 'Order line of a pro forma order'

    order_id = fields.Many2one('pos.order_pro_forma_be')

    @api.model
    def create(self, values):
        # the pos.order.line create method consider 'order_id' is a pos.order
        # override to bypass it and generate a name
        if values.get('order_id') and not values.get('name'):
            name = self.env['pos.order_pro_forma_be'].browse(values['order_id']).name
            values['name'] = "%s-%s" % (name, values.get('id'))
        return super(PosOrderLineProFormaBe, self).create(values)


class PosOrderProFormaBe(models.Model):
    _name = 'pos.order_pro_forma_be'
    _description = 'Model for pro forma order'

    name = fields.Char('Order Ref', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.users'].browse(self.env.uid).company_id.id, readonly=True)
    date_order = fields.Datetime('Order Date', readonly=True)
    create_date = fields.Datetime(string="Pro Forma Creation")
    user_id = fields.Many2one('res.users', 'Salesman', help="Person who uses the cash register. It can be a reliever, a student or an interim employee.", readonly=True)
    lines = fields.One2many('pos.order_line_pro_forma_be', 'order_id', 'Order Lines', readonly=True, copy=True)
    pos_reference = fields.Char('Receipt Ref', readonly=True)
    session_id = fields.Many2one('pos.session', 'Session', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Customer', readonly=True)
    config_id = fields.Many2one('pos.config', related='session_id.config_id', readonly=True)
    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist', readonly=True)
    fiscal_position_id = fields.Many2one('account.fiscal.position', 'Fiscal Position', readonly=True)
    table_id = fields.Many2one('restaurant.table', 'Table', readonly=True)
    currency_id = fields.Many2one(related='session_id.currency_id')
    employee_id = fields.Many2one('hr.employee')
    amount_total = fields.Float(readonly=True)

    blackbox_date = fields.Char("Fiscal Data Module date", help="Date returned by the Fiscal Data Module.", readonly=True)
    blackbox_time = fields.Char("Fiscal Data Module time", help="Time returned by the Fiscal Data Module.", readonly=True)
    blackbox_pos_receipt_time = fields.Datetime("Receipt time", readonly=True)
    blackbox_ticket_counters = fields.Char("Fiscal Data Module ticket counters", help="Ticket counter returned by the Fiscal Data Module (format: counter / total event type)", readonly=True)
    blackbox_unique_fdm_production_number = fields.Char("Fiscal Data Module ID", help="Unique ID of the blackbox that handled this order", readonly=True)
    blackbox_vsc_identification_number = fields.Char("VAT Signing Card ID", help="Unique ID of the VAT signing card that handled this order", readonly=True)
    blackbox_signature = fields.Char("Electronic signature", help="Electronic signature returned by the Fiscal Data Module", readonly=True)
    blackbox_tax_category_a = fields.Monetary(readonly=True, string='Total tax for category A',
                                              help="This is the total amount of the 21% tax")
    blackbox_tax_category_b = fields.Monetary(readonly=True, string='Total tax for category B',
                                              help="This is the total amount of the 12% tax")
    blackbox_tax_category_c = fields.Monetary(readonly=True, string='Total tax for category C',
                                              help="This is the total amount of the 6% tax")
    blackbox_tax_category_d = fields.Monetary(readonly=True, string='Total tax for category D',
                                              help="This is the total amount of the 0% tax")
    receipt_type = fields.Char(readonly=True)

    plu_hash = fields.Char(help="Eight last characters of PLU hash", readonly=True)
    pos_version = fields.Char(help="Version of Odoo that created the order", readonly=True)

    def _create_log_description(self):
        lines = "Lignes de commande: "
        if self.lines:
            lines += "\n* " + "\n* ".join([
                "%s x %s: %s" % (l.qty, l.product_id.name, l.price_subtotal_incl)
                for l in self.lines
            ])
        description = """
        {title}
        Date: {create_date}
        Ref: {pos_reference}
        Cashier: {cashier_name}
        {lines}
        Total: {total}
        Compteur Ticket: {ticket_counters}
        Hash: {hash}
        POS Version: {pos_version}
        FDM ID: {fdm_id}
        POS ID: {config_name}
        FDM Identifier: {fdmIdentifier}
        """.format(
            title="PRO FORMA SALES" if self.amount_total >= 0 else "PRO FORMA REFUNDS",
            create_date=self.create_date,
            cashier_name=self.employee_id.name or self.user_id.name,
            lines=lines,
            total=self.amount_total,
            pos_reference=self.pos_reference,
            hash=self.plu_hash,
            pos_version=self.pos_version,
            ticket_counters=self.blackbox_ticket_counters,
            fdm_id=self.blackbox_unique_fdm_production_number,
            config_name=self.config_id.name,
            fdmIdentifier=self.config_id.certified_blackbox_identifier
        )
        return description

    def _get_values(self, ui_order):
        date = ui_order.get('blackbox_date')
        time = ui_order.get('blackbox_time')

        return {
            'user_id': ui_order['user_id'] or False,
            'session_id': ui_order['pos_session_id'],
            'pos_reference': ui_order['name'],
            'lines': [self.env['pos.order_line_pro_forma_be']._order_line_fields(l, ui_order['pos_session_id']) for l in ui_order['lines']] if ui_order['lines'] else False,
            'partner_id': ui_order['partner_id'] or False,
            'date_order': parser.parse(ui_order['creation_date']).strftime("%Y-%m-%d %H:%M:%S"),
            'amount_total': ui_order.get('amount_total'),
            'fiscal_position_id': ui_order['fiscal_position_id'],
            'blackbox_date': ui_order.get('blackbox_date'),
            'blackbox_time': ui_order.get('blackbox_time'),
            'blackbox_ticket_counters': ui_order.get('blackbox_ticket_counters'),
            'blackbox_unique_fdm_production_number': ui_order.get('blackbox_unique_fdm_production_number'),
            'blackbox_vsc_identification_number': ui_order.get('blackbox_vsc_identification_number'),
            'blackbox_signature': ui_order.get('blackbox_signature'),
            'blackbox_tax_category_a': ui_order.get('blackbox_tax_category_a'),
            'blackbox_tax_category_b': ui_order.get('blackbox_tax_category_b'),
            'blackbox_tax_category_c': ui_order.get('blackbox_tax_category_c'),
            'blackbox_tax_category_d': ui_order.get('blackbox_tax_category_d'),
            'plu_hash': ui_order.get('blackbox_plu_hash'),
            'pos_version': ui_order.get('blackbox_pos_version'),
            'table_id': ui_order.get('table_id'),
            'employee_id': ui_order.get('employee_id'),
            'blackbox_pos_receipt_time': datetime.strptime(date + ' ' + time, '%d-%m-%Y %H:%M:%S') if date else False,
            'pricelist_id': ui_order['pricelist_id'],
        }

    @api.model
    def _create_from_ui(self, orders):
        for ui_order in orders:
            values = self._get_values(ui_order)
            # set name based on the sequence specified on the config
            session = self.env['pos.session'].browse(values['session_id'])
            values['name'] = session.config_id.sequence_id._next()

            order = self.create(values)
            description = order._create_log_description()
            self.env["pos_blackbox_be.log"].sudo().create(description, "create", self._name, order.pos_reference)
