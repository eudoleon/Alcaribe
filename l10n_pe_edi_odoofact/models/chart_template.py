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


from odoo.exceptions import AccessError
from odoo import api, fields, models, _
from odoo import SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)

class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"
    
    def _prepare_all_journals(self, acc_template_ref, company, journals_dict=None):
        '''
        Prepare the journal for the Debit note for peruvian companies
        '''
        journal_data = super(AccountChartTemplate, self)._prepare_all_journals(acc_template_ref, company, journals_dict)
        if company.country_id.code == "PE":
            for journal in journal_data:
                if journal['type'] == 'sale':
                    # Assign shop for Sales journal
                    journal.update({
                        'l10n_pe_edi_is_einvoice': True,
                        'l10n_pe_edi_shop_id': company.l10n_pe_edi_shop_ids and company.l10n_pe_edi_shop_ids[0].id or False
                    })
                    # Create new journal for Debit note
                    new_journal = dict(journal)
                    new_journal.update({
                        'name': _('Debit note'), 
                        'code': _('DEB'),
                        'l10n_pe_edi_is_einvoice': True, 
                        'l10n_latam_document_type_id': self.env.ref('l10n_pe_edi_odoofact.document_type08').id,
                        'l10n_pe_edi_shop_id': company.l10n_pe_edi_shop_ids and company.l10n_pe_edi_shop_ids[0].id or False,
                        'sequence': 6,
                    })
            journal_data.append(new_journal)
        return journal_data

    @api.model
    def generate_shop(self, company):
        """
        This method is used for creating shop.
        :param company_id: company to generate shop for.
        :returns: True
        """
        self.env['l10n_pe_edi.shop'].create({
            'name': '%s (%s)' % (company.name, _('Shop')),
            'code': '0000',
            'company_id': company.id,
            'partner_id': company.partner_id.id,
        })
        return True
    
    def _load_template(self, company, code_digits=None, account_ref=None, taxes_ref=None):
        """ Generate all the objects from the templates
        New: Generate the Shop
        """
        # Create Shop - Only done for root chart template
        if not self.parent_id:
            self.generate_shop(company)

        account_ref, taxes_ref = super(AccountChartTemplate, self)._load_template(company, code_digits, account_ref, taxes_ref)

        return account_ref, taxes_ref
