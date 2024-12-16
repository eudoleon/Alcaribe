# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools.translate import _
from datetime import datetime


class PosOrder(models.Model):
    _inherit = 'pos.order'

    blackbox_date = fields.Char("Fiscal Data Module date", help="Date returned by the Fiscal Data Module.",
                                readonly=True)
    blackbox_time = fields.Char("Fiscal Data Module time", help="Time returned by the Fiscal Data Module.",
                                readonly=True)
    blackbox_pos_receipt_time = fields.Datetime("Receipt time", readonly=True)
    blackbox_ticket_counters = fields.Char("Fiscal Data Module ticket counters",
                                           help="Ticket counter returned by the Fiscal Data Module (format: counter / total event type)",
                                           readonly=True)
    blackbox_unique_fdm_production_number = fields.Char("Fiscal Data Module ID",
                                                        help="Unique ID of the blackbox that handled this order",
                                                        readonly=True)
    blackbox_vsc_identification_number = fields.Char("VAT Signing Card ID",
                                                     help="Unique ID of the VAT signing card that handled this order",
                                                     readonly=True)
    blackbox_signature = fields.Char("Electronic signature",
                                     help="Electronic signature returned by the Fiscal Data Module", readonly=True)
    blackbox_tax_category_a = fields.Monetary(readonly=True, string='Total tax for category A',
                                              help="This is the total amount of the 21% tax")
    blackbox_tax_category_b = fields.Monetary(readonly=True, string='Total tax for category B',
                                              help="This is the total amount of the 12% tax")
    blackbox_tax_category_c = fields.Monetary(readonly=True, string='Total tax for category C',
                                              help="This is the total amount of the 6% tax")
    blackbox_tax_category_d = fields.Monetary(readonly=True, string='Total tax for category D',
                                              help="This is the total amount of the 0% tax")
    receipt_type = fields.Char(readonly=True)
    plu_hash = fields.Char(help="Eight last characters of PLU hash")
    pos_version = fields.Char(help="Version of Odoo that created the order")

    def _create_log_description(self):
        currency = self.currency_id
        lines = "Order lines: "
        if self.lines:
            lines += "\n* " + "\n* ".join([
                "%s x %s: %s" % (l.qty, l.product_id.name, l.price_subtotal_incl) + (" (disc: %s" % l.discount + "%)" if l.discount else "")
                for l in self.lines
            ])
        description = """
        {title}
        Date: {create_date}
        Ref: {pos_reference}
        Cashier: {cashier_name}
        {lines}
        Total: {total}
        Rounding: {rounding_applied}
        Ticket Counter: {ticket_counters}
        Hash: {hash}
        POS Version: {pos_version}
        FDM ID: {fdm_id}
        POS ID: {config_name}
        FDM Identifier: {fdmIdentifier}
        """.format(
            title="NORMAL SALES" if currency.round(self.amount_paid) >= 0 else "NORMAL REFUNDS",
            create_date=self.create_date,
            cashier_name=self.employee_id.name or self.user_id.name,
            lines=lines,
            total=currency.round(self.amount_paid),
            pos_reference=self.pos_reference,
            hash=self.plu_hash,
            pos_version=self.pos_version,
            ticket_counters=self.blackbox_ticket_counters,
            fdm_id=self.blackbox_unique_fdm_production_number,
            config_name=self.config_id.name,
            fdmIdentifier=self.config_id.certified_blackbox_identifier,
            rounding_applied=currency.round(self.amount_total - self.amount_paid)
        )
        return description

    @api.ondelete(at_uninstall=False)
    def unlink_if_blackboxed(self):
        for order in self:
            if order.config_id.iface_fiscal_data_module:
                raise UserError(_('Deleting of registered orders is not allowed.'))

    def write(self, values):
        for order in self:
            if order.config_id.iface_fiscal_data_module and order.state != 'draft':
                white_listed_fields = ['state', 'account_move', 'picking_id', 'invoice_id']

                for field in values:
                    if field not in white_listed_fields:
                        raise UserError(_("Modifying registered orders is not allowed."))

            if values.get('state') == 'paid':
                description = self._create_log_description()
                self.env["pos_blackbox_be.log"].sudo().create(description, "create", self._name, order.pos_reference)

        return super(PosOrder, self).write(values)

    @api.model
    def _order_fields(self, ui_order):
        fields = super(PosOrder, self)._order_fields(ui_order)

        config_id = self.env['pos.session'].browse(fields['session_id']).config_id
        if config_id.certified_blackbox_identifier:
            date = ui_order.get('blackbox_date')
            time = ui_order.get('blackbox_time')

            fields.update({
                'blackbox_date': date,
                'blackbox_time': time,
                'blackbox_pos_receipt_time': datetime.strptime(date + ' ' + time, '%d-%m-%Y %H:%M:%S') if date else False,
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
            })

        return fields

    @api.model
    def create_from_ui(self, orders, draft=False):
        pro_forma_orders = [order['data'] for order in orders if order['data'].get('receipt_type') in ["PS", "PR"]]
        regular_orders = [order for order in orders if order['data'].get('receipt_type') not in ["PS", "PR"]]
        self.env['pos.order_pro_forma_be']._create_from_ui(pro_forma_orders)
        return super(PosOrder, self).create_from_ui(regular_orders, draft)


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    vat_letter = fields.Selection([('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')], help="The VAT letter is related to the amount of the tax. A=21%, B=12%, C=6% and D=0%.")

    def write(self, values):
        if values.get('vat_letter'):
            raise UserError(_("Can't modify fields related to the Fiscal Data Module."))

        return super(PosOrderLine, self).write(values)
