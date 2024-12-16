#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import report
from collections import defaultdict
from odoo import api, SUPERUSER_ID, _

def _salaries_account_journal_pre_init(cr):
    """
        This pre-init hook will check if there is existing "SLR" journal and modify it to keep the code "SLR" free,
        so that we can add an "SLR" journal in the post init hook
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    companies = env['res.company'].search([])

    env.cr.execute("""SELECT company_id, code, id FROM account_journal WHERE company_id in %s AND code LIKE %s""", [tuple(companies.ids), 'SLR%'])
    slr_journals_per_company = defaultdict(dict)
    for company_id, code, journal_id in env.cr.fetchall():
        slr_journals_per_company[company_id].update({code: journal_id})

    if slr_journals_per_company:
        to_change = list()
        for company_id, slr_journals in slr_journals_per_company.items():
            copy_code = f"SLR{next(i for i in range(len(slr_journals) + 1) if f'SLR{i}' not in slr_journals.keys())}"
            to_change.append((copy_code, slr_journals.get('SLR'), company_id))

        for copy_code, journal, company_id in to_change:
            env.cr.execute("""UPDATE account_journal SET code = %s WHERE id = %s AND company_id = %s""", [copy_code, journal, company_id])


def _salaries_account_journal_post_init(cr, registry):
    """
        This post init hook check if a journal SLR exist only if the company has a chart_template_id, and if not create one that will be used.
        Also in the data we created some structure, but in some company they don't have the journals set, so we add it.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    companies_dict = {}
    # Creation of a dict where the keys are companies
    for company in env['res.company'].search([]):
        companies_dict[company] = None

    journals = env['account.journal'].search([('code', '=', 'SLR')])
    for journal in journals:
        # We add the journal as the value of the company
        companies_dict[journal.company_id] = journal

    hr_payroll_struct = env['hr.payroll.structure'].search([])
    journals_to_create = []
    for company, journal in companies_dict.items():
        if not company.chart_template_id:
            continue
        # Since the data are put on the current company, for multi company we create a new journal if it's not there already.
        if not journal:
            journals_to_create.append({
                'name': _("Salaries"),
                'code': 'SLR',
                'type': 'general',
                'company_id': company.id,
            })
    journals = env['account.journal'].create(journals_to_create)
    for journal in journals:
        env.company = journal.company_id
        hr_payroll_struct.journal_id = journal.id
