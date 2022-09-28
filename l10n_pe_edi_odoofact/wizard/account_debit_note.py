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

from odoo import models, fields, api

class AccountDebitNote(models.TransientModel):

    _inherit = 'account.debit.note'

    def _get_type_debit_note(self):
        return self.env.ref('l10n_pe_edi_catalog.l10n_pe_edi_cat10_02').id
    
    l10n_pe_edi_debit_type_id = fields.Many2one('l10n_pe_edi.catalog.10', string='Debit note type', help='Catalog 10: Type of Debit note', default=_get_type_debit_note)

    @api.model
    def default_get(self, fields):
        res = super(AccountDebitNote, self).default_get(fields)
        debit_journal = self.env['account.journal'].search([('l10n_latam_document_type_id','=',self.env.ref('l10n_pe_edi_odoofact.document_type08').id)],limit=1)
        if debit_journal:
            res['journal_id'] = debit_journal.id
        return res

    def _prepare_default_values(self, move):
        default_values = super(AccountDebitNote, self)._prepare_default_values(move)
        if self.l10n_pe_edi_debit_type_id:
            default_values['l10n_pe_edi_debit_type_id'] = self.l10n_pe_edi_debit_type_id and self.l10n_pe_edi_debit_type_id.id or False,
        default_values['l10n_latam_document_type_id'] = self.env.ref('l10n_pe_edi_odoofact.document_type08').id
        return default_values

    def create_debit(self):
        action = super(AccountDebitNote, self).create_debit()
        # Get debit data: Serie, number and date from the original Invoice
        invoice_id = self.env['account.move']
        # Individual
        if 'res_id' in action:
            invoice_id.browse(action['res_id']).get_reversal_origin_data()
        # Multiple
        if 'domain' in action:
            invoice_id.search(action['domain']).get_reversal_origin_data()
        return action
