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

from odoo import models, fields, api, _

class EdiPickingNumber(models.Model):
    _name = 'l10n_pe_edi.picking.number'
    _description = 'Picking numbers'

    invoice_id = fields.Many2one('account.move', string="Invoice")
    name = fields.Char(string="Picking Serial and Number", help="Sintaxt serial TXXX-XXXX or 0XXX-XXXX")
    partner_id = fields.Many2one('res.partner', string="Client")
    type = fields.Selection([
        ('1','SENDER REFERRAL GUIDE'),
        ('2','CARRIER REFERRAL GUIDE')],
        string="Picking Type", default='1')
    
    @api.onchange('invoice_id')
    def _onchange_invoice_id(self):
        if self.invoice_id:
            self.partner_id = self.invoice_id.partner_id.commercial_partner_id.id