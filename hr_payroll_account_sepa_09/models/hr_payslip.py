# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from uuid import uuid4

from odoo import models, fields


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    sepa_uetr = fields.Char(
        string='UETR',
        help='Unique end-to-end transaction reference',
    )

    def _get_payments_vals(self, journal_id):
        res = super()._get_payments_vals(journal_id)
        if journal_id.sepa_pain_version == 'pain.001.001.09':
            if not self.sepa_uetr:
                res['sepa_uetr'] = self.sepa_uetr = str(uuid4())
            else:
                res['sepa_uetr'] = self.sepa_uetr

        return res
