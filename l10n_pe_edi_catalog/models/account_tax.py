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
    _inherit = 'account.tax'

    l10n_pe_edi_tax_code = fields.Selection(selection_add=[('3000', 'IR - Rent Tax')])

class AccountTaxTemplate(models.Model):
    _inherit = 'account.tax.template'

    l10n_pe_edi_tax_code = fields.Selection(selection_add=[('3000', 'IR - Rent Tax')])