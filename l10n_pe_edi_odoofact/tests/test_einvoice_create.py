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

from odoo.tests.common import TransactionCase, tagged

@tagged('-at_install', 'post_install')
class TestEinvoiceCreate(TransactionCase):

    def setUp(self, *args, **kwargs):
        super(TestEinvoiceCreate, self).setUp(*args, **kwargs)
        self.supplier = self.env['l10n_pe_edi.supplier'].browse(1)
        self.company = self.env['res.company'].browse(1)
        self.company.write({'l10n_pe_edi_ose_id': self.supplier.id})
        self.partner_ident_type = self.env['l10n_latam.identification.type'].search([('name','=',"NIF")], limit=1)
        self.partner = self.env['res.partner'].create({
            'company_type': 'company',
            'name': "OPeru",
            'type': "contacto",
            'l10n_latam_identification_type_id': self.partner_ident_type.id,
            'vat': "20602461328",
            'street': "Av. Reducto 1091, Of. 201",
            'email': "info@operu.pe"
        })
        self.invoice_document_type = self.env['l10n_latam.document.type'].search([('code','=',"01")], limit=1)
        self.move = self.env['account.move'].create({
            'partner_id': self.partner.id,
            'l10n_pe_edi_operation_type': "1",
            'l10n_latam_document_type_id': self.invoice_document_type.id,
        })
        
    # def test_button_available(self):
    #     """Make available button"""
    #     print("#########", self.company.l10n_pe_edi_ose_id.code)