# -*- coding: utf-8 -*-
# Journal Report

from odoo import models, _
from odoo.tools import format_date, date_utils, get_lang
from collections import defaultdict
from odoo.exceptions import UserError

import json
import datetime


class JournalReportCustomHandler(models.AbstractModel):
    _inherit = 'account.journal.report.handler'

    def _get_journal_initial_balance(self, options, journal_id, date_month=False):
        queries = []
        params = []
        currency_dif = options['currency_dif']
        report = self.env.ref('account_reports.journal_report')
        for column_group_key, options_group in report._split_options_per_column_group(options).items():
            new_options = self.env['account.general.ledger.report.handler']._get_options_initial_balance(options_group)  # Same options as the general ledger
            tables, where_clause, where_params = report._query_get(new_options, 'normal', domain=[('journal_id', '=', journal_id)])
            params.append(column_group_key)
            params += where_params
            if currency_dif == self.env.company.currency_id.symbol:
                queries.append(f"""
                    SELECT
                        %s AS column_group_key,
                        sum("account_move_line".balance) as balance
                    FROM {tables}
                    JOIN account_journal journal ON journal.id = "account_move_line".journal_id AND "account_move_line".account_id = journal.default_account_id
                    WHERE {where_clause}
                    GROUP BY journal.id
                """)
            else:
                queries.append(f"""
                    SELECT
                        %s AS column_group_key,
                        sum("account_move_line".balance_usd) as balance
                    FROM {tables}
                    JOIN account_journal journal ON journal.id = "account_move_line".journal_id AND "account_move_line".account_id = journal.default_account_id
                    WHERE {where_clause}
                    GROUP BY journal.id
                """)

        self._cr.execute(" UNION ALL ".join(queries), params)

        init_balance_by_col_group = {column_group_key: 0.0 for column_group_key in options['column_groups']}
        for result in self._cr.dictfetchall():
            init_balance_by_col_group[result['column_group_key']] = result['balance']

        return init_balance_by_col_group

    def _query_aml(self, options, offset=0, journal=False):
        params = []
        queries = []
        currency_dif = options['currency_dif']
        lang = self.env.user.lang or get_lang(self.env).code
        acc_name = f"COALESCE(acc.name->>'{lang}', acc.name->>'en_US')" if \
            self.pool['account.account'].name.translate else 'acc.name'
        j_name = f"COALESCE(j.name->>'{lang}', j.name->>'en_US')" if \
            self.pool['account.journal'].name.translate else 'j.name'
        tax_name = f"COALESCE(tax.name->>'{lang}', tax.name->>'en_US')" if \
            self.pool['account.tax'].name.translate else 'tax.name'
        tag_name = f"COALESCE(tag.name->>'{lang}', tag.name->>'en_US')" if \
            self.pool['account.account.tag'].name.translate else 'tag.name'
        report = self.env.ref('account_reports.journal_report')
        for column_group_key, options_group in report._split_options_per_column_group(options).items():
            # Override any forced options: We want the ones given in the options
            options_group['date'] = options['date']
            tables, where_clause, where_params = report._query_get(options_group, 'strict_range', domain=[('journal_id', '=', journal.id)])
            sort_by_date = options_group.get('sort_by_date')
            params.append(column_group_key)
            params += where_params
            params += [report.load_more_limit + 1, offset]
            if currency_dif == self.env.company.currency_id.symbol:
                queries.append(f"""
                    SELECT
                        %s AS column_group_key,
                        "account_move_line".id as move_line_id,
                        "account_move_line".name,
                        "account_move_line".amount_currency,
                        "account_move_line".tax_base_amount,
                        "account_move_line".currency_id as move_line_currency,
                        "account_move_line".amount_currency,
                        am.id as move_id,
                        am.name as move_name,
                        am.journal_id,
                        am.date,
                        am.currency_id as move_currency,
                        am.amount_total_in_currency_signed as amount_currency_total,
                        am.currency_id != cp.currency_id as is_multicurrency,
                        p.name as partner_name,
                        acc.code as account_code,
                        {acc_name} as account_name,
                        acc.account_type as account_type,
                        COALESCE("account_move_line".debit, 0) as debit,
                        COALESCE("account_move_line".credit, 0) as credit,
                        COALESCE("account_move_line".balance, 0) as balance,
                        {j_name} as journal_name,
                        j.code as journal_code,
                        j.type as journal_type,
                        j.currency_id as journal_currency,
                        journal_curr.name as journal_currency_name,
                        cp.currency_id as company_currency,
                        CASE WHEN j.type = 'sale' THEN am.payment_reference WHEN j.type = 'purchase' THEN am.ref ELSE '' END as reference,
                        array_remove(array_agg(DISTINCT {tax_name}), NULL) as taxes,
                        array_remove(array_agg(DISTINCT {tag_name}), NULL) as tax_grids
                    FROM {tables}
                    JOIN account_move am ON am.id = "account_move_line".move_id
                    JOIN account_account acc ON acc.id = "account_move_line".account_id
                    LEFT JOIN res_partner p ON p.id = "account_move_line".partner_id
                    JOIN account_journal j ON j.id = am.journal_id
                    JOIN res_company cp ON cp.id = am.company_id
                    LEFT JOIN account_move_line_account_tax_rel aml_at_rel ON aml_at_rel.account_move_line_id = "account_move_line".id
                    LEFT JOIN account_tax parent_tax ON parent_tax.id = aml_at_rel.account_tax_id and parent_tax.amount_type = 'group'
                    LEFT JOIN account_tax_filiation_rel tax_filiation_rel ON tax_filiation_rel.parent_tax = parent_tax.id
                    LEFT JOIN account_tax tax ON (tax.id = aml_at_rel.account_tax_id and tax.amount_type != 'group') or tax.id = tax_filiation_rel.child_tax
                    LEFT JOIN account_account_tag_account_move_line_rel tag_rel ON tag_rel.account_move_line_id = "account_move_line".id
                    LEFT JOIN account_account_tag tag on tag_rel.account_account_tag_id = tag.id
                    LEFT JOIN res_currency journal_curr on journal_curr.id = j.currency_id
                    WHERE {where_clause}
                    GROUP BY "account_move_line".id, am.id, p.id, acc.id, j.id, cp.id, journal_curr.id
                    ORDER BY j.id, CASE when am.name = '/' then 1 else 0 end,
                    {" am.date, am.name," if sort_by_date else " am.name , am.date,"}
                    CASE acc.account_type
                        WHEN 'liability_payable' THEN 1
                        WHEN 'asset_receivable' THEN 1
                        WHEN 'liability_credit_card' THEN 5
                        WHEN 'asset_cash' THEN 5
                        ELSE 2
                   END,
                   "account_move_line".tax_line_id NULLS FIRST
                   LIMIT %s
                   OFFSET %s
                """)
            else:
                queries.append(f"""
                                    SELECT
                                        %s AS column_group_key,
                                        "account_move_line".id as move_line_id,
                                        "account_move_line".name,
                                        "account_move_line".amount_currency,
                                        "account_move_line".tax_base_amount,
                                        "account_move_line".currency_id as move_line_currency,
                                        "account_move_line".amount_currency,
                                        am.id as move_id,
                                        am.name as move_name,
                                        am.journal_id,
                                        am.date,
                                        am.currency_id as move_currency,
                                        0 as amount_currency_total,
                                        am.currency_id != cp.currency_id as is_multicurrency,
                                        p.name as partner_name,
                                        acc.code as account_code,
                                        {acc_name} as account_name,
                                        acc.account_type as account_type,
                                        COALESCE("account_move_line".debit_usd, 0) as debit,
                                        COALESCE("account_move_line".credit_usd, 0) as credit,
                                        COALESCE("account_move_line".balance_usd, 0) as balance,
                                        {j_name} as journal_name,
                                        j.code as journal_code,
                                        j.type as journal_type,
                                        j.currency_id as journal_currency,
                                        journal_curr.name as journal_currency_name,
                                        cp.currency_id as company_currency,
                                        CASE WHEN j.type = 'sale' THEN am.payment_reference WHEN j.type = 'purchase' THEN am.ref ELSE '' END as reference,
                                        array_remove(array_agg(DISTINCT {tax_name}), NULL) as taxes,
                                        array_remove(array_agg(DISTINCT {tag_name}), NULL) as tax_grids
                                    FROM {tables}
                                    JOIN account_move am ON am.id = "account_move_line".move_id
                                    JOIN account_account acc ON acc.id = "account_move_line".account_id
                                    LEFT JOIN res_partner p ON p.id = "account_move_line".partner_id
                                    JOIN account_journal j ON j.id = am.journal_id
                                    JOIN res_company cp ON cp.id = am.company_id
                                    LEFT JOIN account_move_line_account_tax_rel aml_at_rel ON aml_at_rel.account_move_line_id = "account_move_line".id
                                    LEFT JOIN account_tax parent_tax ON parent_tax.id = aml_at_rel.account_tax_id and parent_tax.amount_type = 'group'
                                    LEFT JOIN account_tax_filiation_rel tax_filiation_rel ON tax_filiation_rel.parent_tax = parent_tax.id
                                    LEFT JOIN account_tax tax ON (tax.id = aml_at_rel.account_tax_id and tax.amount_type != 'group') or tax.id = tax_filiation_rel.child_tax
                                    LEFT JOIN account_account_tag_account_move_line_rel tag_rel ON tag_rel.account_move_line_id = "account_move_line".id
                                    LEFT JOIN account_account_tag tag on tag_rel.account_account_tag_id = tag.id
                                    LEFT JOIN res_currency journal_curr on journal_curr.id = j.currency_id
                                    WHERE {where_clause}
                                    GROUP BY "account_move_line".id, am.id, p.id, acc.id, j.id, cp.id, journal_curr.id
                                    ORDER BY j.id, CASE when am.name = '/' then 1 else 0 end,
                                    {" am.date, am.name," if sort_by_date else " am.name , am.date,"}
                                    CASE acc.account_type
                                        WHEN 'liability_payable' THEN 1
                                        WHEN 'asset_receivable' THEN 1
                                        WHEN 'liability_credit_card' THEN 5
                                        WHEN 'asset_cash' THEN 5
                                        ELSE 2
                                   END,
                                   "account_move_line".tax_line_id NULLS FIRST
                                   LIMIT %s
                                   OFFSET %s
                                """)

        # 1.2.Fetch data from DB
        rslt = {}
        self._cr.execute('(' + ') UNION ALL ('.join(queries) + ')', params)
        for aml_result in self._cr.dictfetchall():
            rslt.setdefault(aml_result['move_line_id'], {col_group_key: {} for col_group_key in options['column_groups']})
            rslt[aml_result['move_line_id']][aml_result['column_group_key']] = aml_result

        return rslt

    def _get_tax_grids_summary(self, options, data):
        """
        Fetches the details of all grids that have been used in the provided journal.
        The result is grouped by the country in which the tag exists in case of multivat environment.
        Returns a dictionary with the following structure:
        {
            Country : {
                tag_name: {+, -, impact},
                tag_name: {+, -, impact},
                tag_name: {+, -, impact},
                ...
            },
            Country : [
                tag_name: {+, -, impact},
                tag_name: {+, -, impact},
                tag_name: {+, -, impact},
                ...
            ],
            ...
        }
        """
        report = self.env.ref('account_reports.journal_report')
        currency_dif = options['currency_dif']
        # Use the same option as we use to get the tax details, but this time to generate the query used to fetch the
        # grid information
        tax_report_options = self._get_generic_tax_report_options(options, data)
        tables, where_clause, where_params = report._query_get(tax_report_options, 'strict_range')
        lang = self.env.user.lang or get_lang(self.env).code
        country_name = f"COALESCE(country.name->>'{lang}', country.name->>'en_US')"
        tag_name = f"COALESCE(tag.name->>'{lang}', tag.name->>'en_US')" if \
            self.pool['account.account.tag'].name.translate else 'tag.name'
        if currency_dif == self.env.company.currency_id.symbol:
            query = f"""
                WITH tag_info (country_name, tag_id, tag_name, tag_sign, balance) as (
                    SELECT
                        {country_name} AS country_name,
                        tag.id,
                        {tag_name} AS name,
                        CASE WHEN tag.tax_negate IS TRUE THEN '-' ELSE '+' END,
                        SUM(COALESCE("account_move_line".balance, 0)
                            * CASE WHEN "account_move_line".tax_tag_invert THEN -1 ELSE 1 END
                            ) AS balance
                    FROM account_account_tag tag
                    JOIN account_account_tag_account_move_line_rel rel ON tag.id = rel.account_account_tag_id
                    JOIN res_country country on country.id = tag.country_id
                    , {tables}
                    WHERE {where_clause}
                      AND applicability = 'taxes'
                      AND "account_move_line".id = rel.account_move_line_id
                    GROUP BY country_name, tag.id
                )
                SELECT
                    country_name,
                    tag_id,
                    REGEXP_REPLACE(tag_name, '^[+-]', '') AS name, -- Remove the sign from the grid name
                    balance,
                    tag_sign AS sign
                FROM tag_info
                ORDER BY country_name, name
            """
        else:
            query = f"""
                            WITH tag_info (country_name, tag_id, tag_name, tag_sign, balance) as (
                                SELECT
                                    {country_name} AS country_name,
                                    tag.id,
                                    {tag_name} AS name,
                                    CASE WHEN tag.tax_negate IS TRUE THEN '-' ELSE '+' END,
                                    SUM(COALESCE("account_move_line".balance_usd, 0)
                                        * CASE WHEN "account_move_line".tax_tag_invert THEN -1 ELSE 1 END
                                        ) AS balance
                                FROM account_account_tag tag
                                JOIN account_account_tag_account_move_line_rel rel ON tag.id = rel.account_account_tag_id
                                JOIN res_country country on country.id = tag.country_id
                                , {tables}
                                WHERE {where_clause}
                                  AND applicability = 'taxes'
                                  AND "account_move_line".id = rel.account_move_line_id
                                GROUP BY country_name, tag.id
                            )
                            SELECT
                                country_name,
                                tag_id,
                                REGEXP_REPLACE(tag_name, '^[+-]', '') AS name, -- Remove the sign from the grid name
                                balance,
                                tag_sign AS sign
                            FROM tag_info
                            ORDER BY country_name, name
                        """

        self._cr.execute(query, where_params)
        query_res = self.env.cr.fetchall()

        res = defaultdict(lambda: defaultdict(dict))
        opposite = {'+': '-', '-': '+'}
        for country_name, tag_id, name, balance, sign in query_res:
            res[country_name][name]['tag_id'] = tag_id
            res[country_name][name][sign] = report.format_value(balance, blank_if_zero=False, figure_type='monetary')
            # We need them formatted, to ensure they are displayed correctly in the report. (E.g. 0.0, not 0)
            if not opposite[sign] in res[country_name][name]:
                res[country_name][name][opposite[sign]] = report.format_value(0, blank_if_zero=False, figure_type='monetary')
            res[country_name][name][sign + '_no_format'] = balance
            res[country_name][name]['impact'] = report.format_value(res[country_name][name].get('+_no_format', 0) - res[country_name][name].get('-_no_format', 0), blank_if_zero=False, figure_type='monetary')

        return res