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

import time
import math
import re

from odoo.osv import expression
from odoo.tools.float_utils import float_round as round, float_compare
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, _, tools
from odoo.tests.common import Form

class AccountJournal(models.Model):
    _inherit = "account.journal"
    
    l10n_pe_edi_contingency = fields.Boolean('Contingency', help='Check this for contingency invoices')
    l10n_pe_edi_shop_id = fields.Many2one('l10n_pe_edi.shop', string='Shop')
    l10n_latam_document_type_id = fields.Many2one('l10n_latam.document.type', string='Electronic document type', help='Catalog 01: Type of electronic document', compute='_get_document_type', readonly=False, store=True)
    l10n_pe_edi_is_einvoice = fields.Boolean('Is E-invoice')
    l10n_pe_edi_send_to_client = fields.Boolean('Send to Client')

    @api.model
    def create(self, vals):
        res = super(AccountJournal, self).create(vals)
        # FIXED for apply only to sale journals
        if res.company_id.country_id.code == 'PE' and res.type == 'sale':
            res.sequence_override_regex = r'^(?P<prefix1>.*?)(?P<seq>\d*)(?P<suffix>\D*?)$'
        return res
    
    @api.depends('type')
    def _get_document_type(self):
        for journal in self:
            if journal.type == 'sale' and journal.company_id.country_id.code == "PE":
                journal.l10n_latam_document_type_id = self.env['l10n_latam.document.type'].search([('internal_type','=','invoice')], limit=1)
            else:
                journal.l10n_latam_document_type_id = False

    def _set_sequence_override_regex(self):
        if self.type == 'sale' and self.company_id.country_id.code == "PE":
            self.sequence_override_regex = r'^(?P<prefix1>.*?)(?P<seq>\d*)(?P<suffix>\D*?)$'
        else:
            self.sequence_override_regex = False

    @api.onchange('type', 'company_id')
    def _onchange_sequence_override_regex(self):
        ''' Replace the 'sequence_override_regex' for peruvian format
            'PREFIX-NUMBER'. Ex: 'F001-0000050'
        '''
        for journal in self:
            journal._set_sequence_override_regex()
            