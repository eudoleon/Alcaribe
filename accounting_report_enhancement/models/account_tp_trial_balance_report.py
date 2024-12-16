# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


import json
import re

from odoo import models, fields, api, _
from odoo.tools.misc import format_date
from odoo.tools import float_compare
from odoo.tools import get_lang
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import UserError
from datetime import timedelta, datetime
from collections import defaultdict


class GeneralLedgerCustomHandler(models.AbstractModel):
    _name = 'account.general.ledger.report.handler.tp'
    _inherit = 'account.general.ledger.report.handler'

    def _get_query_sums(self, report, options):
        """ Construct a query retrieving all the aggregated sums to build the report. It includes:
        - sums for all accounts.
        - sums for the initial balances.
        - sums for the unaffected earnings.
        - sums for the tax declaration.
        :return:                    (query, params)
        """
        options_by_column_group = report._split_options_per_column_group(options)

        params = []
        queries = []

        # Create the currency table.
        # As the currency table is the same whatever the comparisons, create it only once.
        ct_query = self.env['res.currency']._get_query_currency_table(options)

        # ============================================
        # 1) Get sums for all accounts.
        # ============================================
        for column_group_key, options_group in options_by_column_group.items():
            if not options.get('general_ledger_strict_range'):
                options_group = self._get_options_sum_balance(options_group)

            # Sum is computed including the initial balance of the accounts configured to do so, unless a special option key is used
            # (this is required for trial balance, which is based on general ledger)
            sum_date_scope = 'strict_range' if options_group.get('general_ledger_strict_range') else 'normal'

            query_domain = []

            if options.get('filter_search_bar'):
                query_domain.append(('account_id', 'ilike', options['filter_search_bar']))

            if options_group.get('include_current_year_in_unaff_earnings'):
                query_domain += [('account_id.include_initial_balance', '=', True)]

            tables, where_clause, where_params = report._query_get(options_group, sum_date_scope, domain=query_domain)
            params.append(column_group_key)
            params += where_params
            queries.append(f"""
                SELECT
                    account_move_line.account_id                            AS groupby,
                    'sum'                                                   AS key,
                    MAX(account_move_line.date)                             AS max_date,
                    %s                                                      AS column_group_key,
                    COALESCE(SUM(account_move_line.amount_currency), 0.0)   AS amount_currency,
                    SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit,
                    SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit,
                    SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
                FROM {tables}
                LEFT JOIN {ct_query} ON currency_table.company_id = account_move_line.company_id
                WHERE {where_clause} 
                GROUP BY account_move_line.account_id
            """)
            #AND account_move_line.partner_id IS NOT NULL
            # ============================================
            # 2) Get sums for the unaffected earnings.
            # ============================================
            if not options_group.get('general_ledger_strict_range'):
                unaff_earnings_domain = [('account_id.include_initial_balance', '=', False)]

                # The period domain is expressed as:
                # [
                #   ('date' <= fiscalyear['date_from'] - 1),
                #   ('account_id.include_initial_balance', '=', False),
                # ]

                new_options = self._get_options_unaffected_earnings(options_group)
                tables, where_clause, where_params = report._query_get(new_options, 'strict_range',
                                                                       domain=unaff_earnings_domain)
                params.append(column_group_key)
                params += where_params
                queries.append(f"""
                    SELECT
                        account_move_line.company_id                            AS groupby,
                        'unaffected_earnings'                                   AS key,
                        NULL                                                    AS max_date,
                        %s                                                      AS column_group_key,
                        COALESCE(SUM(account_move_line.amount_currency), 0.0)   AS amount_currency,
                        SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit,
                        SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit,
                        SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
                    FROM {tables}
                    LEFT JOIN {ct_query} ON currency_table.company_id = account_move_line.company_id
                    WHERE {where_clause} 
                    GROUP BY account_move_line.company_id
                """)

        return ' UNION ALL '.join(queries), params
        #AND account_move_line.partner_id IS NOT NULL se suprime al generar diferencia en el balance
    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals):
        lines = []
        date_from = fields.Date.from_string(options['date']['date_from'])
        date_to = fields.Date.from_string(options['date']['date_to'])
        company_currency = self.env.company.currency_id

        totals_by_column_group = defaultdict(lambda: {'debit': 0, 'credit': 0, 'balance': 0})
        for account, column_group_results in self._query_values(report, options):
            eval_dict = {}
            has_lines = False
            limit_to_load = report.load_more_limit + 1 if report.load_more_limit and not self._context.get(
                'print_mode') else None
            aml_results = self._get_aml_values(report, options, [account.id], offset=0, limit=limit_to_load)

            has_values = False

            for key, value in aml_results[0].items():
                if len(value) > 0:
                    for k1, v1 in value.items():
                        if len(v1) > 0:
                            for k2, v2 in v1.items():
                                if len(v2) > 0:
                                    date_line = v2.get('date')
                                    if date_from <= date_line <= date_to:
                                        has_values = True
                                        break

            if has_values:
                for column_group_key, results in column_group_results.items():
                    account_sum = results.get('sum', {})
                    account_un_earn = results.get('unaffected_earnings', {})

                    account_debit = account_sum.get('debit', 0.0) + account_un_earn.get('debit', 0.0)
                    account_credit = account_sum.get('credit', 0.0) + account_un_earn.get('credit', 0.0)
                    account_balance = account_sum.get('balance', 0.0) + account_un_earn.get('balance', 0.0)

                    eval_dict[column_group_key] = {
                        'amount_currency': account_sum.get('amount_currency', 0.0) + account_un_earn.get(
                            'amount_currency', 0.0),
                        'debit': account_debit,
                        'credit': account_credit,
                        'balance': account_balance,
                    }

                    max_date = account_sum.get('max_date')
                    has_lines = has_lines or (max_date and max_date >= date_from)

                    totals_by_column_group[column_group_key]['debit'] += account_debit
                    totals_by_column_group[column_group_key]['credit'] += account_credit
                    totals_by_column_group[column_group_key]['balance'] += account_balance

                lines.append(self._get_account_title_line(report, options, account, has_lines, eval_dict))

        # Report total line.
        for totals in totals_by_column_group.values():
            totals['balance'] = company_currency.round(totals['balance'])

        # Tax Declaration lines.
        journal_options = report._get_options_journals(options)
        if len(options['column_groups']) == 1 and len(journal_options) == 1 and journal_options[0]['type'] in (
                'sale', 'purchase'):
            lines += self._tax_declaration_lines(report, options, journal_options[0]['type'])

        # Total line
        lines.append(self._get_total_line(report, options, totals_by_column_group))

        return [(0, line) for line in lines]


class TrialBalanceCustomHandler(models.AbstractModel):
    _name = 'account.tp.trial.balance.report.handler'
    _inherit = 'account.trial.balance.report.handler'
    _description = 'Third Party Trial Balance Custom Handler'

    def _get_aml_line(self, report, parent_line_id, options, eval_dict, init_bal_by_col_group):
        line_columns = []
        for column in options['columns']:
            col_expr_label = column['expression_label']
            col_value = eval_dict[column['column_group_key']].get(col_expr_label)

            if col_value is None:
                line_columns.append({})
            else:
                col_class = 'number'

                if col_expr_label == 'amount_currency':
                    currency = self.env['res.currency'].browse(eval_dict[column['column_group_key']]['currency_id'])

                    if currency != self.env.company.currency_id:
                        formatted_value = report.format_value(col_value, currency=currency,
                                                              figure_type=column['figure_type'])
                    else:
                        formatted_value = ''
                elif col_expr_label == 'date':
                    formatted_value = format_date(self.env, col_value)
                    col_class = 'date'
                elif col_expr_label == 'balance':
                    col_value += init_bal_by_col_group[column['column_group_key']]
                    formatted_value = report.format_value(col_value, figure_type=column['figure_type'],
                                                          blank_if_zero=False)
                elif col_expr_label == 'communication' or col_expr_label == 'partner_name' \
                        or col_expr_label == 'partner_nit':
                    col_class = 'o_account_report_line_ellipsis'
                    formatted_value = report.format_value(col_value, figure_type=column['figure_type'])
                else:
                    formatted_value = report.format_value(col_value, figure_type=column['figure_type'])
                    if col_expr_label not in ('debit', 'credit'):
                        col_class = ''

                line_columns.append({
                    'name': formatted_value,
                    'no_format': col_value,
                    'class': col_class,
                })

        caret_type = 'account.move.line'

        line_id = []

        for key, value in eval_dict.items():
            if bool(value):
                first_column_group_key_id = key
                line_id = eval_dict[first_column_group_key_id]
                break
        account_name = (line_id.get("account_code", "") + " " + line_id.get("account_name", ""))
        partner_name = line_id.get("partner_id", "SIN  TERCERO")  
        combined_name = f"{account_name} - {partner_name}" 
        return {
            'id': report._get_generic_line_id('account.move.line', line_id['id'], parent_line_id=parent_line_id),
            'caret_options': caret_type,
            'parent_id': parent_line_id,
            'name': combined_name,
            'columns': line_columns,
            #'level': 2,
        }

    def _get_query_amls(self, report, options, expanded_account_ids, offset=0, limit=None):
        """ Construct a query retrieving the account.move.lines when expanding a report line with or without the load
        more.
        :param options:               The report options.
        :param expanded_account_ids:  The account.account ids corresponding to consider. If None, match every account.
        :param offset:                The offset of the query (used by the load more).
        :param limit:                 The limit of the query (used by the load more).
        :return:                      (query, params)
        """
        additional_domain = [('account_id', 'in', expanded_account_ids)] if expanded_account_ids is not None else None
        queries = []
        all_params = []
        lang = self.env.user.lang or get_lang(self.env).code
        journal_name = f"COALESCE(journal.name->>'{lang}', journal.name->>'en_US')" if \
            self.pool['account.journal'].name.translate else 'journal.name'
        account_name = f"COALESCE(account.name->>'{lang}', account.name->>'en_US')" if \
            self.pool['account.account'].name.translate else 'account.name'
        for column_group_key, group_options in report._split_options_per_column_group(options).items():
            # Get sums for the account move lines.
            # period: [('date' <= options['date_to']), ('date', '>=', options['date_from'])]
            tables, where_clause, where_params = report._query_get(group_options, domain=additional_domain,
                                                                   date_scope='strict_range')
            ct_query = self.env['res.currency']._get_query_currency_table(group_options)
            query = f'''
                (SELECT
                    account_move_line.id,
                    account_move_line.date,
                    account_move_line.date_maturity,
                    account_move_line.name,
                    account_move_line.ref,
                    account_move_line.company_id,
                    account_move_line.account_id,
                    account_move_line.payment_id,
                    account_move_line.partner_id,
                    account_move_line.currency_id,
                    account_move_line.amount_currency,
                    ROUND(account_move_line.debit * currency_table.rate, currency_table.precision)   AS debit,
                    ROUND(account_move_line.credit * currency_table.rate, currency_table.precision)  AS credit,
                    ROUND(account_move_line.balance * currency_table.rate, currency_table.precision) AS balance,
                    move.name                               AS move_name,
                    company.currency_id                     AS company_currency_id,
                    partner.name                            AS partner_name,
                    partner.vat                             AS partner_nit,
                    partner.id                              AS partner_id,
                    move.move_type                          AS move_type,
                    account.code                            AS account_code,
                    {account_name}                          AS account_name,
                    journal.code                            AS journal_code,
                    {journal_name}                          AS journal_name,
                    full_rec.name                           AS full_rec_name,
                    %s                                      AS column_group_key
                FROM {tables}
                JOIN account_move move                      ON move.id = account_move_line.move_id
                LEFT JOIN {ct_query}                        ON currency_table.company_id = account_move_line.company_id
                LEFT JOIN res_company company               ON company.id = account_move_line.company_id
                LEFT JOIN res_partner partner               ON partner.id = account_move_line.partner_id
                LEFT JOIN account_account account           ON account.id = account_move_line.account_id
                LEFT JOIN account_journal journal           ON journal.id = account_move_line.journal_id
                LEFT JOIN account_full_reconcile full_rec   ON full_rec.id = account_move_line.full_reconcile_id
                WHERE {where_clause} 
                ORDER BY account_move_line.date, account_move_line.id)
            '''
            # AND account_move_line.partner_id IS NOT NULL
            queries.append(query)
            all_params.append(column_group_key)
            all_params += where_params

        full_query = " UNION ALL ".join(queries)

        if offset:
            full_query += ' OFFSET %s '
            all_params.append(offset)
        if limit:
            full_query += ' LIMIT %s '
            all_params.append(limit)

        return (full_query, all_params)

    def _get_aml_values(self, report, options, expanded_account_ids, offset=0, limit=None):
        rslt = {account_id: {} for account_id in expanded_account_ids}
        aml_query, aml_params = self._get_query_amls(report, options, expanded_account_ids, offset=offset, limit=limit)
        self._cr.execute(aml_query, aml_params)
        aml_results_number = 0
        has_more = False
        for aml_result in self._cr.dictfetchall():
            aml_results_number += 1
            if aml_results_number == limit:
                has_more = True
                break

            if aml_result['ref']:
                aml_result['communication'] = f"{aml_result['ref']} - {aml_result['name']}"
            else:
                aml_result['communication'] = aml_result['name']

            # The same aml can return multiple results when using account_report_cash_basis module, if the receivable/payable
            # is reconciled with multiple payments. In this case, the date shown for the move lines actually corresponds to the
            # reconciliation date. In order to keep distinct lines in this case, we include date in the grouping key.
            aml_key = (aml_result['id'], aml_result['date'])

            account_result = rslt[aml_result['account_id']]
            if not aml_key in account_result:
                account_result[aml_key] = {col_group_key: {} for col_group_key in options['column_groups']}

            already_present_result = account_result[aml_key][aml_result['column_group_key']]
            if already_present_result:
                # In case the same move line gives multiple results at the same date, add them.
                # This does not happen in standard GL report, but could because of custom shadowing of account.move.line,
                # such as the one done in account_report_cash_basis (if the payable/receivable line is reconciled twice at the same date).
                already_present_result['debit'] += aml_result['debit']
                already_present_result['credit'] += aml_result['credit']
                already_present_result['balance'] += aml_result['balance']
                already_present_result['amount_currency'] += aml_result['amount_currency']
            else:
                account_result[aml_key][aml_result['column_group_key']] = aml_result

        return rslt, has_more

    def _get_options_initial_balance(self, options):
        """ Create options used to compute the initial balances.
        The initial balances depict the current balance of the accounts at the beginning of
        the selected period in the report.
        The resulting dates domain will be:
        [
            ('date' <= options['date_from'] - 1),
            '|',
            ('date' >= fiscalyear['date_from']),
            ('account_id.include_initial_balance', '=', True)
        ]
        :param options: The report options.
        :return:        A copy of the options.
        """
        new_options = options.copy()
        date_to = new_options['comparison']['periods'][-1]['date_from'] if new_options.get('comparison', {}).get(
            'periods') else new_options['date']['date_from']
        new_date_to = fields.Date.from_string(date_to) - timedelta(days=1)

        # Date from computation
        # We have two case:
        # 1) We are choosing a date that starts at the beginning of a fiscal year and we want the initial period to be
        # the previous fiscal year
        # 2) We are choosing a date that starts in the middle of a fiscal year and in that case we want the initial period
        # to be the beginning of the fiscal year
        date_from = fields.Date.from_string(new_options['date']['date_from'])
        current_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(date_from)

        if date_from == current_fiscalyear_dates['date_from']:
            # We want the previous fiscal year
            previous_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(date_from - timedelta(days=1))
            new_date_from = previous_fiscalyear_dates['date_from']
            include_current_year_in_unaff_earnings = True
        else:
            # We want the current fiscal year
            new_date_from = current_fiscalyear_dates['date_from']
            include_current_year_in_unaff_earnings = False

        new_options['date'] = {
            'mode': 'range',
            'date_from': fields.Date.to_string(new_date_from),
            'date_to': fields.Date.to_string(new_date_to),
        }
        new_options['include_current_year_in_unaff_earnings'] = include_current_year_in_unaff_earnings

        return new_options

    def _get_initial_balance_values(self, report, account_ids, options):
        """
        Get sums for the initial balance.
        """
        queries = []
        params = []
        for column_group_key, options_group in report._split_options_per_column_group(options).items():
            new_options = self._get_options_initial_balance(options_group)
            ct_query = self.env['res.currency']._get_query_currency_table(new_options)
            tables, where_clause, where_params = report._query_get(new_options, 'normal', domain=[
                ('account_id', 'in', account_ids),
                ('account_id.include_initial_balance', '=', True),
            ])
            params.append(column_group_key)
            params += where_params
            queries.append(f"""
                SELECT
                    account_move_line.account_id                                                          AS groupby,
                    'initial_balance'                                                                     AS key,
                    NULL                                                                                  AS max_date,
                    %s                                                                                    AS column_group_key,
                    COALESCE(SUM(account_move_line.amount_currency), 0.0)                                 AS amount_currency,
                    SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit,
                    SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit,
                    SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
                FROM {tables}
                LEFT JOIN {ct_query} ON currency_table.company_id = account_move_line.company_id
                WHERE {where_clause}
                GROUP BY account_move_line.account_id
            """)

        self._cr.execute(" UNION ALL ".join(queries), params)

        init_balance_by_col_group = {
            account_id: {column_group_key: {} for column_group_key in options['column_groups']}
            for account_id in account_ids
        }
        for result in self._cr.dictfetchall():
            init_balance_by_col_group[result['groupby']][result['column_group_key']] = result

        accounts = self.env['account.account'].browse(account_ids)
        return {
            account.id: (account, init_balance_by_col_group[account.id])
            for account in accounts
        }

    def _report_expand_unfoldable_line_general_ledger(self, line_dict_id, groupby, options, progress, offset,
                                                      unfold_all_batch_data=None):
        def init_load_more_progress(line_dict):
            return {
                column['column_group_key']: line_col.get('no_format', 0)
                for column, line_col in zip(options['columns'], line_dict['columns'])
                if column['expression_label'] == 'balance'
            }

        report = self.env.ref('account_reports.general_ledger_report')
        model, model_id = report._get_model_info_from_id(line_dict_id)

        if model != 'account.account':
            raise UserError(_("Wrong ID for general ledger line to expand: %s", line_dict_id))

        lines = []

        # Get initial balance
        if offset == 0:
            if unfold_all_batch_data:
                account, init_balance_by_col_group = unfold_all_batch_data['initial_balances'][model_id]
            else:
                account, init_balance_by_col_group = self._get_initial_balance_values(report, [model_id], options)[
                    model_id]

            initial_balance_line = report._get_partner_and_general_ledger_initial_balance_line(options, line_dict_id,
                                                                                               init_balance_by_col_group,
                                                                                               account.currency_id)

            if initial_balance_line:
                lines.append(initial_balance_line)

                # For the first expansion of the line, the initial balance line gives the progress
                progress = init_load_more_progress(initial_balance_line)

        # Get move lines
        limit_to_load = report.load_more_limit + 1 if report.load_more_limit and not self._context.get(
            'print_mode') else None
        has_more = False
        if unfold_all_batch_data:
            aml_results = unfold_all_batch_data['aml_values'][model_id]
        else:
            aml_results, has_more = self._get_aml_values(report, options, [model_id], offset=offset,
                                                         limit=limit_to_load)
            aml_results = aml_results[model_id]

        def _get_datas_from_id(line_id):
            account_move_line_obj = self.env['account.move.line']
            if 'account.group' in line_id:
                match = re.search(r'(~account\.account[^|]+\|[^|]+)', line_id)
                if match:
                    account_account_part = match.group(1)
                    line_id = f'~account.account{account_account_part[16:]}'
            new_line_id = line_id
            first_tilde = new_line_id.find("~")
            pipe = new_line_id.find("|")
            subtext = new_line_id[first_tilde + 1:pipe]
            account_id = int(subtext.split("~")[1])
            aml_id = int(new_line_id.split('~')[-1])
            partner_id = (account_move_line_obj.search([('id', '=', aml_id)])).partner_id.id
            return [account_id, aml_id, partner_id]

        next_progress = progress
        for aml_result in aml_results.values():
            new_line = self._get_aml_line(report, line_dict_id, options, aml_result, next_progress)
            lines.append(new_line)
            next_progress = init_load_more_progress(new_line)

        date_from = fields.Date.from_string(options['date']['date_from'])
        date_to = fields.Date.from_string(options['date']['date_to'])
        old_lines = lines
        new_lines = []
        grouped_results = []
        if options['comparison']['filter'] == 'no_comparison':
            for line in lines:
                if line['name'] not in grouped_results and 'initial' not in line['id']:
                    grouped_results.append(line['name'])
                    aml_id = _get_datas_from_id(line['id'])[1]
                    nit_val = line['columns'][0]['no_format'] if 'no_format' in line['columns'][0] else False
                    if not nit_val:
                        col_class = 'o_account_report_line_ellipsis'
                        domain = [('id', '=', aml_id)]
                        aml = self.env['account.move.line'].search(domain)
                        v_nit = aml.partner_id.name
                        if not nit_val:
                            formatted_value = self.env['account.report'].format_value(v_nit,
                                                                                      figure_type='none')
                            line['columns'][0] = {
                                'name': formatted_value,
                                'no_format': v_nit,
                                'class': col_class,
                            }
                    formatted_value = self.env['account.report'].format_value(0.00,
                                                                              figure_type='none')
                    line['columns'][1] = {
                        'name': formatted_value,
                        'no_format': 0.00,
                        'class': 'number',
                    }
                    formatted_value = self.env['account.report'].format_value(0.00,
                                                                              figure_type='none')
                    line['columns'][2] = {
                        'name': formatted_value,
                        'no_format': 0.00,
                        'class': 'number',
                    }
                    line['columns'][2]['no_format'] = 0.00
                    formatted_value = self.env['account.report'].format_value(0.00,
                                                                              figure_type='none')
                    line['columns'][3] = {
                        'name': formatted_value,
                        'no_format': 0.00,
                        'class': 'number',
                    }
                    formatted_value = self.env['account.report'].format_value(0.00,
                                                                              figure_type='none')
                    line['columns'][4] = {
                        'name': formatted_value,
                        'no_format': 0.00,
                        'class': 'number',
                    }
                    new_lines.append(line)

            for new_line in new_lines:
                init_balance = 0.00
                p_debit = 0.00
                p_credit = 0.00
                for line in old_lines:
                    if line['name'] == new_line['name']:
                        aml_id = _get_datas_from_id(line['id'])[1]
                        aml = self.env['account.move.line'].search([('id', '=', aml_id)])
                        if aml.date < date_from:
                            init_balance += aml.debit - aml.credit
                        if date_from <= aml.date <= date_to:
                            p_debit += aml.debit
                            p_credit += aml.credit

                formatted_value = self.env['account.report'].format_value(init_balance,
                                                                          figure_type='monetary',
                                                                          blank_if_zero=True)
                new_line['columns'][1] = {
                    'name': formatted_value,
                    'no_format': init_balance,
                    'class': 'number',
                }

                formatted_value = self.env['account.report'].format_value(p_debit,
                                                                          figure_type='monetary',
                                                                          blank_if_zero=True)
                new_line['columns'][2] = {
                    'name': formatted_value,
                    'no_format': p_debit,
                    'class': 'number',
                }

                formatted_value = self.env['account.report'].format_value(p_credit,
                                                                          figure_type='monetary',
                                                                          blank_if_zero=True)
                new_line['columns'][3] = {
                    'name': formatted_value,
                    'no_format': p_credit,
                    'class': 'number',
                }

                final_balance = init_balance + (p_debit - p_credit)

                formatted_value = self.env['account.report'].format_value(final_balance,
                                                                          figure_type='monetary',
                                                                          blank_if_zero=True)
                new_line['columns'][4] = {
                    'name': formatted_value,
                    'no_format': final_balance,
                    'class': 'number',
                }
        else:
            cant_comparison = options['comparison']['number_period']
            for line in lines:
                if line['name'] not in grouped_results and 'initial' not in line['id']:
                    grouped_results.append(line['name'])
                    aml_id = _get_datas_from_id(line['id'])[1]
                    nit_val = line['columns'][0]['no_format'] if 'no_format' in line['columns'][0] else False
                    if not nit_val:
                        col_class = 'o_account_report_line_ellipsis'
                        domain = [('id', '=', aml_id)]
                        aml = self.env['account.move.line'].search(domain)
                        v_nit = aml.partner_id.name or 'vacio'
                        if not nit_val:
                            formatted_value = self.env['account.report'].format_value(v_nit,
                                                                                      figure_type='none')
                            line['columns'][0] = {
                                'name': formatted_value,
                                'no_format': v_nit,
                                'class': col_class,
                            }
                    formatted_value = self.env['account.report'].format_value(0.00,
                                                                              figure_type='none')
                    line['columns'][1] = {
                        'name': formatted_value,
                        'no_format': 0.00,
                        'class': 'number',
                    }

                    index = 2
                    i = 0
                    for i in range(i, cant_comparison + 1):
                        formatted_value = self.env['account.report'].format_value(0.00,
                                                                                  figure_type='none')
                        line['columns'][index] = {
                            'name': formatted_value,
                            'no_format': 0.00,
                            'class': 'number',
                        }
                        formatted_value = self.env['account.report'].format_value(0.00,
                                                                                  figure_type='none')
                        line['columns'][index + 1] = {
                            'name': formatted_value,
                            'no_format': 0.00,
                            'class': 'number',
                        }
                        index = index + 1
                        index += 1
                        i += 1

                    formatted_value = self.env['account.report'].format_value(0.00,
                                                                              figure_type='none')
                    line['columns'][-1] = {
                        'name': formatted_value,
                        'no_format': 0.00,
                        'class': 'number',
                    }
                    new_lines.append(line)
            for new_line in new_lines:
                periods_vals = []
                p_debit = 0.00
                p_credit = 0.00
                init_balance = 0.00
                for line in old_lines:
                    date_from = fields.Date.from_string(options['date']['date_from'])
                    date_to = fields.Date.from_string(options['date']['date_to'])
                    if line['name'] == new_line['name']:
                        aml_id = _get_datas_from_id(line['id'])[1]
                        aml = self.env['account.move.line'].search([('id', '=', aml_id)])
                        init_p_date = fields.Date.from_string(options['comparison']['periods'][-1]['date_from'])
                        if aml.date < init_p_date:
                            init_balance += aml.debit - aml.credit
                        for p in options['comparison']['periods']:
                            init_pf_date = fields.Date.from_string(p['date_from'])
                            init_pt_date = fields.Date.from_string(p['date_to'])
                            if init_pf_date <= aml.date <= init_pt_date:
                                dic = {
                                    'name': p['string'],
                                    'debit': aml.debit,
                                    'credit': aml.credit
                                }
                                periods_vals.append(dic)
                        if date_from <= aml.date <= date_to:
                            p_debit += aml.debit
                            p_credit += aml.credit

                formatted_value = self.env['account.report'].format_value(init_balance,
                                                                          figure_type='monetary',
                                                                          blank_if_zero=True)
                new_line['columns'][1] = {
                    'name': formatted_value,
                    'no_format': init_balance,
                    'class': 'number',
                }

                inv_index = -1
                index = 2
                i = 0
                tp_debit = 0.00
                tp_credit = 0.00
                for i in range(i, cant_comparison):
                    name = options['comparison']['periods'][inv_index]['string']
                    for value in periods_vals:
                        if value['name'] == name:
                            tp_debit += value['debit']
                            tp_credit += value['credit']

                    formatted_value = self.env['account.report'].format_value(tp_debit,
                                                                              figure_type='monetary',
                                                                              blank_if_zero=True)
                    new_line['columns'][index] = {
                        'name': formatted_value,
                        'no_format': tp_debit,
                        'class': 'number',
                    }
                    formatted_value = self.env['account.report'].format_value(tp_credit,
                                                                              figure_type='monetary',
                                                                              blank_if_zero=True)

                    new_line['columns'][index + 1] = {
                        'name': formatted_value,
                        'no_format': tp_credit,
                        'class': 'number',
                    }

                    index = index + 1
                    index += 1
                    inv_index += -1
                    i += 1

                formatted_value = self.env['account.report'].format_value(p_debit,
                                                                          figure_type='monetary',
                                                                          blank_if_zero=True)
                new_line['columns'][index] = {
                    'name': formatted_value,
                    'no_format': p_debit,
                    'class': 'number',
                }

                formatted_value = self.env['account.report'].format_value(p_credit,
                                                                          figure_type='monetary',
                                                                          blank_if_zero=True)
                new_line['columns'][index + 1] = {
                    'name': formatted_value,
                    'no_format': p_credit,
                    'class': 'number',
                }

                all_debit = 0.00
                all_credit = 0.00
                for value in periods_vals:
                    all_debit += value['debit']
                    all_credit += value['credit']

                final_balance = init_balance + (p_debit - p_credit) + (all_debit - all_credit)

                formatted_value = self.env['account.report'].format_value(final_balance,
                                                                          figure_type='monetary',
                                                                          blank_if_zero=True)
                new_line['columns'][-1] = {
                    'name': formatted_value,
                    'no_format': final_balance,
                    'class': 'number',
                }

        return {
            'lines': new_lines,
            'offset_increment': report.load_more_limit,
            'has_more': has_more,
            'progress': json.dumps(next_progress),
        }

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals):
        def _update_column(line, column_key, new_value, blank_if_zero=True):
            line['columns'][column_key]['name'] = self.env['account.report'].format_value(new_value,
                                                                                          figure_type='monetary',
                                                                                          blank_if_zero=blank_if_zero)
            line['columns'][column_key]['no_format'] = new_value

        def _update_balance_columns(line, debit_column_key, credit_column_key, total_diff_values_key):
            debit_value = line["columns"][debit_column_key].get("no_format", 0)
            credit_value = line["columns"][credit_column_key].get("no_format", 0)

            if debit_value and credit_value:
                new_debit_value = 0.0
                new_credit_value = 0.0

                if float_compare(debit_value, credit_value,
                                 precision_digits=self.env.company.currency_id.decimal_places) == 1:
                    new_debit_value = debit_value - credit_value
                    total_diff_values[total_diff_values_key] += credit_value
                else:
                    new_credit_value = (debit_value - credit_value) * -1
                    total_diff_values[total_diff_values_key] += debit_value

                _update_column(line, debit_column_key, new_debit_value)
                _update_column(line, credit_column_key, new_credit_value)

        lines = [line[1] for line in
                 self.env['account.general.ledger.report.handler.tp']._dynamic_lines_generator(report, options,
                                                                                               all_column_groups_expression_totals)]

        total_diff_values = {
            'initial_balance': 0.0,
            'end_balance': 0.0,
        }

        for line in lines[:-1]:
            # Initial balance
            res_model = report._get_model_info_from_id(line['id'])[0]
            if res_model == 'account.account':
                _update_balance_columns(line, 2, 3, 'initial_balance')

                # End balance
                _update_balance_columns(line, -2, -1, 'end_balance')

            # line.pop('expand_function', None)
            line.pop('groupby', 'partner_id')
            line.update({
                # 'unfoldable': False,
                # 'unfolded': False,
                'class': 'o_account_searchable_line o_account_coa_column_contrast',
            })

            res_model = report._get_model_info_from_id(line['id'])[0]
            if res_model == 'account.account':
                # line['caret_options'] = 'trial_balance'
                line['caret_options'] = None

        # Total line
        if lines:
            total_line = lines[-1]
            _update_column(total_line, 2, total_line['columns'][2].get("no_format", 0) - total_diff_values['initial_balance'],
                           blank_if_zero=False)
            _update_column(total_line, 3, total_line['columns'][3].get("no_format", 0)  - total_diff_values['initial_balance'],
                           blank_if_zero=False)
            _update_column(total_line, -2, total_line['columns'][-2].get("no_format", 0) - total_diff_values['end_balance'],
                           blank_if_zero=False)
            _update_column(total_line, -1, total_line['columns'][-1].get("no_format", 0)  - total_diff_values['end_balance'],
                           blank_if_zero=False)

        date_from = fields.Date.from_string(options['date']['date_from'])
        date_to = fields.Date.from_string(options['date']['date_to'])
        if options['comparison']['filter'] == 'no_comparison':
            options['column_headers'][0][0]['name'] = 'Balance de Prueba entre el'
            options['column_headers'][0][1]['name'] = f'{date_from} y el {date_to}'
            del options['column_headers'][0][2]

            options['columns'][1]['name'] = 'Saldo Inicial'
            del options['columns'][2]
            del options['columns'][2]
            del options['columns'][2]
            del options['columns'][2]
            options['columns'][2]['name'] = 'Débito'
            options['columns'][3]['name'] = 'Crédito'
            del options['columns'][4]
            options['columns'][4]['name'] = 'Saldo Final'
            del options['columns'][5]
            del options['columns'][5]

            for line in lines:
                del line['columns'][2]
                del line['columns'][2]
                del line['columns'][2]
                del line['columns'][2]
                del line['columns'][4]
                del line['columns'][5]
                del line['columns'][5]
            return [(0, line) for line in lines]
        else:
            options['column_headers'][0][0]['name'] = 'Balance de Prueba, Comparación'
            del options['column_headers'][0][-1]
            cant_comparison = options['comparison']['number_period']
            options['columns'][1]['name'] = 'Saldo Inicial'
            del options['columns'][2]
            del options['columns'][2]
            index = 2
            i = 0
            del_index = []
            for i in range(i, cant_comparison + 1):
                if i <= cant_comparison:
                    del options['columns'][index]
                    del_index.append(index)
                    del options['columns'][index]
                    del_index.append(index)
                    options['columns'][index]['name'] = 'Débito'
                    options['columns'][index + 1]['name'] = 'Crédito'
                    index = index + 1
                    index += 1
                    i += 1
            del options['columns'][index]
            options['columns'][index]['name'] = 'Saldo Final'
            del options['columns'][-1]
            del options['columns'][-1]
            for line in lines:
                del line['columns'][2]
                del line['columns'][2]
                for d in del_index:
                    del line['columns'][d]
                del line['columns'][index]
                del line['columns'][-1]
                del line['columns'][-1]
            return [(0, line) for line in lines]
