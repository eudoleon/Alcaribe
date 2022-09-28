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

class ReportEinvoice(models.AbstractModel):
    _name = 'report.l10n_pe_edi_odoofact.report_einvoice'
    _description = 'Account report with payment lines'
    _inherit = 'report.account.report_invoice'

    @api.model
    def _get_report_values(self, docids, data=None):
        rslt = super()._get_report_values(docids, data)
        rslt['report_type'] = data.get('report_type') if data else ''
        return rslt
