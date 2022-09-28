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

import json, requests
import urllib3
from datetime import datetime, date, timedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError, RedirectWarning

class EdiShop(models.Model):
    _name = 'l10n_pe_edi.shop'
    _description = 'EDI PE Shop'
    _check_company_auto = True
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name', required=True)
    code = fields.Char('SUNAT Code', size=4, required=True, help='Code from SUNAT')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, index=1, required=True)
    journal_ids = fields.One2many('account.journal','l10n_pe_edi_shop_id', string='Journals', help='Select the shop from the journal configuration')
    l10n_pe_edi_ose_url = fields.Char('URL', tracking=True)
    l10n_pe_edi_ose_token = fields.Char('Token', tracking=True)    
    l10n_pe_edi_ose_code = fields.Char('Code of PSE / OSE supplier', related='company_id.l10n_pe_edi_ose_id.code')
    l10n_pe_edi_ose_id = fields.Many2one('l10n_pe_edi.supplier', related='company_id.l10n_pe_edi_ose_id', string='PSE / OSE Supplier')   
    partner_id = fields.Many2one('res.partner','Address', tracking=True)
    send_email = fields.Boolean(string='Send invoice by Email',help='Send email automatically when the invoice is sent', tracking=True) 