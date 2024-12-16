# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.tools import format_date
from itertools import groupby
from collections import defaultdict

MAX_NAME_LENGTH = 50


class AssetReportCustomHandler(models.AbstractModel):
    _inherit = 'account.asset.report.handler'

    def _query_values(self, options, prefix_to_match=None, forced_account_id=None):
        "Get the data from the database"

        self.env['account.move.line'].check_access_rights('read')
        self.env['account.asset'].check_access_rights('read')
        currency_dif = options['currency_dif']
        move_filter = f"""move.state {"!= 'cancel'" if options.get('all_entries') else "= 'posted'"}"""

        if options.get('multi_company', False):
            company_ids = tuple(self.env.companies.ids)
        else:
            company_ids = tuple(self.env.company.ids)

        query_params = {
            'date_to': options['date']['date_to'],
            'date_from': options['date']['date_from'],
            'company_ids': company_ids,
        }

        prefix_query = ''
        if prefix_to_match:
            prefix_query = "AND asset.name ILIKE %(prefix_to_match)s"
            query_params['prefix_to_match'] = f"{prefix_to_match}%"

        account_query = ''
        if forced_account_id:
            account_query = "AND account.id = %(forced_account_id)s"
            query_params['forced_account_id'] = forced_account_id
        if currency_dif == self.env.company.currency_id.symbol:
            sql = f"""
                SELECT asset.id AS asset_id,
                       asset.parent_id AS parent_id,
                       asset.name AS asset_name,
                       asset.original_value AS asset_original_value,
                       asset.currency_id AS asset_currency_id,
                       MIN(move.date) AS asset_date,
                       asset.disposal_date AS asset_disposal_date,
                       asset.acquisition_date AS asset_acquisition_date,
                       asset.method AS asset_method,
                       asset.method_number AS asset_method_number,
                       asset.method_period AS asset_method_period,
                       asset.method_progress_factor AS asset_method_progress_factor,
                       asset.state AS asset_state,
                       account.code AS account_code,
                       account.name AS account_name,
                       account.id AS account_id,
                       account.company_id AS company_id,
                       COALESCE(SUM(move.depreciation_value) FILTER (WHERE move.date < %(date_from)s AND {move_filter}), 0) + COALESCE(asset.already_depreciated_amount_import, 0) AS depreciated_before,
                       COALESCE(SUM(move.depreciation_value) FILTER (WHERE move.date BETWEEN %(date_from)s AND %(date_to)s AND {move_filter}), 0) AS depreciated_during
                  FROM account_asset AS asset
             LEFT JOIN account_account AS account ON asset.account_asset_id = account.id
             LEFT JOIN account_move move ON move.asset_id = asset.id
             LEFT JOIN account_move reversal ON reversal.reversed_entry_id = move.id
                 WHERE asset.company_id in %(company_ids)s
                   AND (asset.acquisition_date <= %(date_to)s OR move.date <= %(date_to)s)
                   AND (asset.disposal_date >= %(date_from)s OR asset.disposal_date IS NULL)
                   AND asset.state not in ('model', 'draft', 'cancelled')
                   AND asset.asset_type = 'purchase'
                   AND asset.active = 't'
                   AND reversal.id IS NULL
                   {prefix_query}
                   {account_query}
              GROUP BY asset.id, account.id
              ORDER BY account.code, asset.acquisition_date;
            """
        else:
            sql = f"""
                            SELECT asset.id AS asset_id,
                                   asset.parent_id AS parent_id,
                                   asset.name AS asset_name,
                                   asset.original_value_ref AS asset_original_value,
                                   asset.currency_id AS asset_currency_id,
                                   MIN(move.date) AS asset_date,
                                   asset.disposal_date AS asset_disposal_date,
                                   asset.acquisition_date AS asset_acquisition_date,
                                   asset.method AS asset_method,
                                   asset.method_number AS asset_method_number,
                                   asset.method_period AS asset_method_period,
                                   asset.method_progress_factor AS asset_method_progress_factor,
                                   asset.state AS asset_state,
                                   account.code AS account_code,
                                   account.name AS account_name,
                                   account.id AS account_id,
                                   account.company_id AS company_id,
                                   COALESCE(SUM(move.depreciation_value_ref) FILTER (WHERE move.date < %(date_from)s AND {move_filter}), 0) + COALESCE(asset.already_depreciated_amount_import_ref, 0) AS depreciated_before,
                                   COALESCE(SUM(move.depreciation_value_ref) FILTER (WHERE move.date BETWEEN %(date_from)s AND %(date_to)s AND {move_filter}), 0) AS depreciated_during
                              FROM account_asset AS asset
                         LEFT JOIN account_account AS account ON asset.account_asset_id = account.id
                         LEFT JOIN account_move move ON move.asset_id = asset.id
                         LEFT JOIN account_move reversal ON reversal.reversed_entry_id = move.id
                             WHERE asset.company_id in %(company_ids)s
                               AND (asset.acquisition_date <= %(date_to)s OR move.date <= %(date_to)s)
                               AND (asset.disposal_date >= %(date_from)s OR asset.disposal_date IS NULL)
                               AND asset.state not in ('model', 'draft', 'cancelled')
                               AND asset.asset_type = 'purchase'
                               AND asset.active = 't'
                               AND reversal.id IS NULL
                               {prefix_query}
                               {account_query}
                          GROUP BY asset.id, account.id
                          ORDER BY account.code, asset.acquisition_date;
                        """

        self._cr.execute(sql, query_params)
        results = self._cr.dictfetchall()
        return results