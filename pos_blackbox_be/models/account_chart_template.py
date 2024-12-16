# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    def _load(self, sale_tax_rate, purchase_tax_rate, company):
        super(AccountChartTemplate, self)._load(sale_tax_rate, purchase_tax_rate, company)
        if self == self.env.ref('l10n_be.l10nbe_chart_template'):
            work_in = self.env.ref('pos_blackbox_be.product_product_work_in')
            work_out = self.env.ref('pos_blackbox_be.product_product_work_out')
            taxes = self.env['account.tax'].sudo().with_context(active_test=False).search([('amount', '=', 0.0), ('type_tax_use', '=', 'sale'), ('name', '=', '0%'), ('company_id', '=', company.id)])
            if not taxes.active:
                taxes.active = True
            work_in.with_context(install_mode=True).with_company(company.id).write({'taxes_id': [(4, taxes.id)]})
            work_out.with_context(install_mode=True).with_company(company.id).write({'taxes_id': [(4, taxes.id)]})
