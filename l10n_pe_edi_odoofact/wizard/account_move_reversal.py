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
from odoo.tools.translate import _

class AccountMoveReversal(models.TransientModel):
    """Credit Notes"""

    _inherit = "account.move.reversal"
    
    def _get_type_credit_note(self):
        return self.env.ref('l10n_pe_edi_catalog.l10n_pe_edi_cat09_01').id

    l10n_pe_edi_reversal_type_id = fields.Many2one(
        'l10n_pe_edi.catalog.09', string='Credit note type', help='Catalog 09: Type of Credit note', default=_get_type_credit_note)
    
    def reverse_moves(self):
        # Update the context to pass the l10n_pe_edi_reversal_type_id to reversal move
        l10n_pe_edi_reversal_type_id = self.l10n_pe_edi_reversal_type_id and self.l10n_pe_edi_reversal_type_id.id or False
        l10n_latam_document_type_id = self.env.ref('l10n_pe_edi_odoofact.document_type07').id
        action = super(AccountMoveReversal, self.with_context(l10n_pe_edi_reversal_type_id=l10n_pe_edi_reversal_type_id,
                                                            l10n_latam_document_type_id=l10n_latam_document_type_id)).reverse_moves()
        # Get reversal data: Serie, numbre and date from the original Invoice
        invoice_id = self.env['account.move']
        # Individual
        if 'res_id' in action:
            invoice_id.browse(action['res_id']).get_reversal_origin_data()
        # Multiple
        if 'domain' in action:
            invoice_id.search(action['domain']).get_reversal_origin_data()
        return action