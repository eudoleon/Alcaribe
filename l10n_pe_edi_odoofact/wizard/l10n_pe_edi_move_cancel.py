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

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

class L10nPeEdiMoveCancel(models.TransientModel):
    _name = 'l10n_pe_edi.move.cancel'
    _description = 'Send invoice cancel'
    
    description = fields.Char('Reason')
    
    def send_invoice_cancel(self):
        #getting invoice_ids selected
        active_ids = self.env.context.get('active_ids',[])
        for move in active_ids:
            #calling method "invoice_send_cancel" sending invoice
            self.env['account.move'].browse(move).with_context(reason=self.description).action_document_send_cancel()
