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

from odoo import fields, models

class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_pe_edi_isc_type = fields.Many2one('l10n_pe_edi.catalog.08', string="Type of ISC")

class AccountTaxTemplate(models.Model):
    _inherit = "account.tax.template"

    l10n_pe_edi_isc_type = fields.Many2one('l10n_pe_edi.catalog.08', string="Type of ISC")

    def _get_tax_vals(self, company, tax_template_to_tax):
        val = super()._get_tax_vals(company, tax_template_to_tax)
        val.update({
            'l10n_pe_edi_isc_type': self.l10n_pe_edi_isc_type.id,
        })
        return val
