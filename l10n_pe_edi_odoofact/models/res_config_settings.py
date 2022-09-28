# -*- coding: utf-8 -*-
###############################################################################
#
#    Copyright (C) 2019-TODAY OPeru.
#    Author      :  Grupo Odoo S.A.C. (<http://www.operu.pe>)
#
#    This program is copyright property of the author mentioned above.
#    You can`t redistribute it and/or modify it.
#
###############################################################################

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_pe_edi_multishop = fields.Boolean('Multi-Shop', related='company_id.l10n_pe_edi_multishop', readonly=False)
    l10n_pe_edi_ose_id = fields.Many2one('l10n_pe_edi.supplier', string='PSE / OSE', related='company_id.l10n_pe_edi_ose_id', readonly=False)
    l10n_pe_edi_ose_code = fields.Char('Code of supplier', related='l10n_pe_edi_ose_id.code')
    l10n_pe_edi_ose_url = fields.Char('URL', related='company_id.l10n_pe_edi_ose_url', readonly=False)
    l10n_pe_edi_ose_token = fields.Char('Token', related='company_id.l10n_pe_edi_ose_token', readonly=False)
    l10n_pe_edi_send_invoice = fields.Boolean('Send Invoices to PSE/OSE', related='company_id.l10n_pe_edi_send_invoice', readonly=False)
    l10n_pe_edi_send_invoice_interval_unit = fields.Selection(related="company_id.l10n_pe_edi_send_invoice_interval_unit", readonly=False)
    l10n_pe_edi_send_invoice_next_execution_date = fields.Datetime(related="company_id.l10n_pe_edi_send_invoice_next_execution_date", readonly=False)
    l10n_pe_edi_company_partner_id = fields.Many2one(related="company_id.partner_id")
    deposit_default_product_id = fields.Many2one(domain="[('type', '=', 'service'),('l10n_pe_edi_is_for_advance','=',True)]")

    @api.onchange('l10n_pe_edi_send_invoice_interval_unit')
    def onchange_l10n_pe_edi_send_invoice_interval_unit(self):
        if self.company_id.l10n_pe_edi_send_invoice_next_execution_date:
            return
        if self.l10n_pe_edi_send_invoice_interval_unit == 'hourly':
            next_update = relativedelta(hours=+1)
        elif self.l10n_pe_edi_send_invoice_interval_unit == 'daily':
            next_update = relativedelta(days=+1)
        else:
            self.l10n_pe_edi_send_invoice_next_execution_date = False
            return
        self.l10n_pe_edi_send_invoice_next_execution_date = datetime.now() + next_update

    def update_l10n_pe_edi_invoice_manually(self):
        self.ensure_one()
        self.company_id.run_send_invoice()
