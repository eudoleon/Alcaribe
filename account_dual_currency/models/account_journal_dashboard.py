import ast
from babel.dates import format_datetime, format_date
from collections import defaultdict
from datetime import datetime, timedelta
import json
import random

from odoo import models, api, _, fields
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.release import version
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.tools.misc import formatLang, format_date as odoo_format_date, get_lang

def group_by_journal(vals_list):
    res = defaultdict(list)
    for vals in vals_list:
        res[vals['journal_id']].append(vals)
    return res

class account_journal(models.Model):
    _inherit = "account.journal"

    def _fill_sale_purchase_dashboard_data(self, dashboard_data):
        """Populate all sale and purchase journal's data dict with relevant information for the kanban card."""
        sale_purchase_journals = self.filtered(lambda journal: journal.type in ('sale', 'purchase'))
        if not sale_purchase_journals:
            return
        field_list = [
            "account_move.journal_id",
            "(CASE WHEN account_move.move_type IN ('out_refund', 'in_refund') THEN -1 ELSE 1 END) * account_move.amount_total_usd AS amount_total",
            "(CASE WHEN account_move.move_type IN ('in_invoice', 'in_refund', 'in_receipt') THEN -1 ELSE 1 END) * account_move.amount_total_usd AS amount_total_company",
            "account_move.currency_id AS currency",
            "account_move.move_type",
            "account_move.invoice_date",
            "account_move.company_id",
        ]
        currency_id_dif = sale_purchase_journals[0].company_id.currency_id_dif
        query, params = sale_purchase_journals._get_open_bills_to_pay_query().select(*field_list)
        self.env.cr.execute(query, params)
        query_results_to_pay = group_by_journal(self.env.cr.dictfetchall())

        query, params = sale_purchase_journals._get_draft_bills_query().select(*field_list)
        self.env.cr.execute(query, params)
        query_results_drafts = group_by_journal(self.env.cr.dictfetchall())

        query, params = sale_purchase_journals._get_late_bills_query().select(*field_list)
        self.env.cr.execute(query, params)
        late_query_results = group_by_journal(self.env.cr.dictfetchall())

        to_check_vals = {
            vals['journal_id']: vals
            for vals in self.env['account.move'].read_group(
                domain=[('journal_id', 'in', sale_purchase_journals.ids), ('to_check', '=', True)],
                fields=['amount_total_signed'],
                groupby='journal_id',
            )
        }

        curr_cache = {}
        sale_purchase_journals._fill_dashboard_data_count(dashboard_data, 'account.move', 'entries_count', [])
        for journal in sale_purchase_journals:
            currency = journal.currency_id or journal.company_id.currency_id
            (number_waiting, sum_waiting) = self._count_results_and_sum_amounts(query_results_to_pay[journal.id], currency, curr_cache=curr_cache)
            (number_draft, sum_draft) = self._count_results_and_sum_amounts(query_results_drafts[journal.id], currency, curr_cache=curr_cache)
            (number_late, sum_late) = self._count_results_and_sum_amounts(late_query_results[journal.id], currency, curr_cache=curr_cache)
            to_check = to_check_vals.get(journal.id, {})
            dashboard_data[journal.id].update({
                'number_to_check': to_check.get('__count', 0),
                'to_check_balance': to_check.get('amount_total_signed', 0),
                'title': _('Bills to pay') if journal.type == 'purchase' else _('Invoices owed to you'),
                'number_draft': number_draft,
                'number_waiting': number_waiting,
                'number_late': number_late,
                'sum_draft': currency.format(sum_draft * currency_id_dif.inverse_rate),
                'sum_draft_usd': currency_id_dif.format(sum_draft),

                'sum_waiting': currency.format(sum_waiting * currency_id_dif.inverse_rate),
                'sum_waiting_usd': formatLang(self.env, currency_id_dif.round(sum_waiting) + 0.0,
                                              currency_obj=currency_id_dif),

                'sum_late': currency.format(sum_late * currency_id_dif.inverse_rate),
                'sum_late_usd': formatLang(self.env, currency_id_dif.round(sum_late) + 0.0,
                                           currency_obj=currency_id_dif),

                'has_sequence_holes': journal.has_sequence_holes,
                'is_sample_data': dashboard_data[journal.id]['entries_count'],
            })

    # def _fill_sale_purchase_dashboard_data(self, dashboard_data):
    #     """Populate all sale and purchase journal's data dict with relevant information for the kanban card."""
    #     sale_purchase_journals = self.filtered(lambda journal: journal.type in ('sale', 'purchase'))
    #     if not sale_purchase_journals:
    #         return
    #     field_list = [
    #         "account_move.journal_id",
    #         "(CASE WHEN account_move.move_type IN ('out_refund', 'in_refund') THEN -1 ELSE 1 END) * account_move.amount_total_usd AS amount_total",
    #         "account_move.amount_total_usd AS amount_total_company",
    #         "account_move.currency_id_dif AS currency",
    #         "account_move.move_type",
    #         "account_move.invoice_date",
    #         "account_move.company_id",
    #     ]
    #     currency_id_dif = self.company_id.currency_id_dif
    #     query, params = sale_purchase_journals._get_open_bills_to_pay_query().select(*field_list)
    #     self.env.cr.execute(query, params)
    #     query_results_to_pay = group_by_journal(self.env.cr.dictfetchall())
    #
    #     query, params = sale_purchase_journals._get_draft_bills_query().select(*field_list)
    #     self.env.cr.execute(query, params)
    #     query_results_drafts = group_by_journal(self.env.cr.dictfetchall())
    #
    #     query, params = sale_purchase_journals._get_late_bills_query().select(*field_list)
    #     self.env.cr.execute(query, params)
    #     late_query_results = group_by_journal(self.env.cr.dictfetchall())
    #
    #     to_check_vals = {
    #         vals['journal_id']: vals
    #         for vals in self.env['account.move'].read_group(
    #             domain=[('journal_id', 'in', sale_purchase_journals.ids), ('to_check', '=', True)],
    #             fields=['amount_total_usd'],
    #             groupby='journal_id',
    #         )
    #     }
    #
    #     curr_cache = {}
    #     sale_purchase_journals._fill_dashboard_data_count(dashboard_data, 'account.move', 'entries_count', [])
    #     for journal in sale_purchase_journals:
    #         currency = journal.currency_id or journal.company_id.currency_id
    #         (number_waiting, sum_waiting) = self._count_results_and_sum_amounts(query_results_to_pay[journal.id], currency, curr_cache=curr_cache)
    #         (number_draft, sum_draft) = self._count_results_and_sum_amounts(query_results_drafts[journal.id], currency, curr_cache=curr_cache)
    #         (number_late, sum_late) = self._count_results_and_sum_amounts(late_query_results[journal.id], currency, curr_cache=curr_cache)
    #         to_check = to_check_vals.get(journal.id, {})
    #         dashboard_data[journal.id].update({
    #             'number_to_check': to_check.get('__count', 0),
    #             'to_check_balance': to_check.get('amount_total_signed', 0),
    #             'title': _('Bills to pay') if journal.type == 'purchase' else _('Invoices owed to you'),
    #             'number_draft': number_draft,
    #             'number_waiting': number_waiting,
    #             'number_late': number_late,
    #             'sum_draft': currency.format(sum_draft * currency_id_dif.inverse_rate),
    #             'sum_draft_usd': formatLang(self.env, currency_id_dif.round(sum_draft) + 0.0, currency_obj=currency_id_dif),
    #             'sum_waiting': currency.format(sum_waiting * currency_id_dif.inverse_rate),
    #             'sum_waiting_usd': formatLang(self.env, currency_id_dif.round(sum_waiting) + 0.0, currency_obj=currency_id_dif),
    #
    #             'sum_late': currency.format(sum_late * currency_id_dif.inverse_rate),
    #             'sum_late_usd': formatLang(self.env, currency_id_dif.round(sum_late) + 0.0, currency_obj=currency_id_dif),
    #
    #             'has_sequence_holes': journal.has_sequence_holes,
    #             'is_sample_data': dashboard_data[journal.id]['entries_count'],
    #         })