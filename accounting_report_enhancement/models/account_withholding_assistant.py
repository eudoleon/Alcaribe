# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from datetime import timedelta

from odoo import models, api, fields, Command, _
from odoo.addons.web.controllers.utils import clean_action
from odoo.exceptions import UserError, RedirectWarning
from odoo.osv import expression
from odoo.tools import json
from odoo.tools.misc import get_lang, format_date


class WAReportCustomHandler(models.AbstractModel):
    _name = 'account.withholding.assistant.report.handler'
    _inherit = 'account.generic.tax.report.handler.tax.account'
    _description = 'Withholding Assistant Report Custom Handler'

    def _get_initial_balance_values(self, report, account_ids, options):
        """
        Get sums for the initial balance.
        """
        queries = []
        params = []
        for column_group_key, options_group in report._split_options_per_column_group(options).items():
            new_options = self._get_options_initial_balance(options_group)
            ct_query = self.env['res.currency']._get_query_currency_table(new_options)
            domain = [('account_id', 'in', account_ids)]
            if new_options.get('include_current_year_in_unaff_earnings'):
                domain += [('account_id.include_initial_balance', '=', True)]
            tables, where_clause, where_params = report._query_get(new_options, 'normal', domain=domain)
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
                elif col_expr_label == 'communication' or col_expr_label == 'partner_name':
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

        aml_id = None
        move_name = None
        caret_type = None
        for column_group_dict in eval_dict.values():
            aml_id = column_group_dict.get('id', '')
            if aml_id:
                if column_group_dict.get('payment_id'):
                    caret_type = 'account.payment'
                else:
                    caret_type = 'account.move.line'
                move_name = column_group_dict['move_name']
                break

        return {
            'id': report._get_generic_line_id('account.move.line', aml_id, parent_line_id=parent_line_id),
            'caret_options': caret_type,
            'parent_id': parent_line_id,
            'name': move_name,
            'columns': line_columns,
            'level': 4,
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

        next_progress = progress
        for aml_result in aml_results.values():
            new_line = self._get_aml_line(report, line_dict_id, options, aml_result, next_progress)
            lines.append(new_line)
            next_progress = init_load_more_progress(new_line)

        def _get_move_line(line_id):
            text = line_id
            elements = text.split('|~')
            aml_id = None
            for element in elements:
                if 'account.move.line' in element:
                    aml_id = int(element.split('~')[1])
                    break
            return [aml_id, 'account.move.line']

        def _get_account_tax(line_id):
            text = line_id
            elements = text.split('|~')
            t_id = None
            for element in elements:
                if 'account.tax' in element:
                    t_id = int(element.split('~')[1])
                    break
            return [t_id, 'account.tax']

        if options['comparison']['filter'] == 'no_comparison':
            for line in lines:
                tax_id = _get_account_tax(line['id'])[0]
                model = _get_account_tax(line['id'])[1]
                line_tax = (self.env[model].search([('id', '=', tax_id)])).amount
                amount_type = (self.env[model].search([('id', '=', tax_id)])).amount_type
                if amount_type == 'percent':
                    line_tax = round(line_tax / 100, 4)
                    formatted_value = self.env['account.report'].format_value(line_tax,
                                                                              figure_type='none')
                    line['columns'][3] = {
                        'name': formatted_value,
                        'no_format': line_tax,
                        'class': 'number',
                    }
                else:
                    formatted_value = self.env['account.report'].format_value(line_tax,
                                                                              figure_type='none',
                                                                              blank_if_zero=True)
                    line['columns'][3] = {
                        'name': formatted_value,
                        'no_format': line_tax,
                        'class': 'number',
                    }

                aml_id = _get_move_line(line['id'])[0]
                model = _get_move_line(line['id'])[1]
                tax_base_amount = (self.env[model].search([('id', '=', aml_id)])).tax_base_amount

                formatted_value = self.env['account.report'].format_value(tax_base_amount,
                                                                          figure_type='monetary',
                                                                          blank_if_zero=True)

                line['columns'][4] = {
                    'name': formatted_value,
                    'no_format': tax_base_amount,
                    'class': 'number',
                }
                value = 0.00
                if 'sale' in line['id']:
                    value = (self.env[model].search([('id', '=', aml_id)])).credit
                    if (self.env[model].search([('id', '=', aml_id)])).debit != 0:
                        value = value - (self.env[model].search([('id', '=', aml_id)])).debit
                if 'purchase' in line['id']:
                    value = (self.env[model].search([('id', '=', aml_id)])).debit
                    if (self.env[model].search([('id', '=', aml_id)])).credit != 0:
                        value = value - (self.env[model].search([('id', '=', aml_id)])).credit

                formatted_value = self.env['account.report'].format_value(value,
                                                                          figure_type='monetary',
                                                                          blank_if_zero=True)

                line['columns'][2] = {
                    'name': formatted_value,
                    'no_format': value,
                    'class': 'number',
                }
        else:
            for line in lines:
                date_from = fields.Date.from_string(options['date']['date_from'])
                date_to = fields.Date.from_string(options['date']['date_to'])
                if len(line['columns'][0]) != 0 and date_from <= line['columns'][0]['no_format'] <= date_to:
                    tax_id = _get_account_tax(line['id'])[0]
                    model = _get_account_tax(line['id'])[1]
                    line_tax = (self.env[model].search([('id', '=', tax_id)])).amount
                    amount_type = (self.env[model].search([('id', '=', tax_id)])).amount_type
                    if amount_type == 'percent':
                        line_tax = round(line_tax / 100, 4)
                        formatted_value = self.env['account.report'].format_value(line_tax,
                                                                                  figure_type='none')
                        line['columns'][3] = {
                            'name': formatted_value,
                            'no_format': line_tax,
                            'class': 'number',
                        }
                    else:
                        formatted_value = self.env['account.report'].format_value(line_tax,
                                                                                  figure_type='none',
                                                                                  blank_if_zero=True)
                        line['columns'][3] = {
                            'name': formatted_value,
                            'no_format': line_tax,
                            'class': 'number',
                        }

                    aml_id = _get_move_line(line['id'])[0]
                    model = _get_move_line(line['id'])[1]
                    tax_base_amount = (self.env[model].search([('id', '=', aml_id)])).tax_base_amount

                    formatted_value = self.env['account.report'].format_value(tax_base_amount,
                                                                              figure_type='monetary',
                                                                              blank_if_zero=True)

                    line['columns'][4] = {
                        'name': formatted_value,
                        'no_format': tax_base_amount,
                        'class': 'number',
                    }
                    value = 0.00
                    if 'sale' in line['id']:
                        value = (self.env[model].search([('id', '=', aml_id)])).credit
                        if (self.env[model].search([('id', '=', aml_id)])).debit != 0:
                            value = value - (self.env[model].search([('id', '=', aml_id)])).debit
                    if 'purchase' in line['id']:
                        value = (self.env[model].search([('id', '=', aml_id)])).debit
                        if (self.env[model].search([('id', '=', aml_id)])).credit != 0:
                            value = value - (self.env[model].search([('id', '=', aml_id)])).credit

                    formatted_value = self.env['account.report'].format_value(value,
                                                                              figure_type='monetary',
                                                                              blank_if_zero=True)

                    line['columns'][2] = {
                        'name': formatted_value,
                        'no_format': value,
                        'class': 'number',
                    }
                else:
                    period = 0
                    index_date = 5
                    index_percent = 3
                    index_base = 4
                    index_value = 2
                    for p in options['comparison']['periods']:
                        date_from = fields.Date.from_string(p['date_from'])
                        date_to = fields.Date.from_string(p['date_to'])
                        if len(line['columns'][index_date]) != 0 and date_from <= line['columns'][index_date][
                            'no_format'] <= date_to:
                            period += 1
                            break
                        else:
                            period += 1
                            index_date += 5
                    if period != 0:
                        tax_id = _get_account_tax(line['id'])[0]
                        model = _get_account_tax(line['id'])[1]
                        line_tax = (self.env[model].search([('id', '=', tax_id)])).amount
                        amount_type = (self.env[model].search([('id', '=', tax_id)])).amount_type
                        if amount_type == 'percent':
                            line_tax = round(line_tax / 100, 4)
                            formatted_value = self.env['account.report'].format_value(line_tax,
                                                                                      figure_type='none')
                            line['columns'][index_percent + (period * 5)] = {
                                'name': formatted_value,
                                'no_format': line_tax,
                                'class': 'number',
                            }
                        else:
                            formatted_value = self.env['account.report'].format_value(line_tax,
                                                                                      figure_type='none',
                                                                                      blank_if_zero=True)
                            line['columns'][index_percent + (period * 5)] = {
                                'name': formatted_value,
                                'no_format': line_tax,
                                'class': 'number',
                            }

                        aml_id = _get_move_line(line['id'])[0]
                        model = _get_move_line(line['id'])[1]
                        tax_base_amount = (self.env[model].search([('id', '=', aml_id)])).tax_base_amount

                        formatted_value = self.env['account.report'].format_value(tax_base_amount,
                                                                                  figure_type='monetary',
                                                                                  blank_if_zero=True)

                        line['columns'][index_base + (period * 5)] = {
                            'name': formatted_value,
                            'no_format': tax_base_amount,
                            'class': 'number',
                        }
                        value = 0.00
                        if 'sale' in line['id']:
                            value = (self.env[model].search([('id', '=', aml_id)])).credit
                            if (self.env[model].search([('id', '=', aml_id)])).debit != 0:
                                value = value - (self.env[model].search([('id', '=', aml_id)])).debit
                        if 'purchase' in line['id']:
                            value = (self.env[model].search([('id', '=', aml_id)])).debit
                            if (self.env[model].search([('id', '=', aml_id)])).credit != 0:
                                value = value - (self.env[model].search([('id', '=', aml_id)])).credit

                        formatted_value = self.env['account.report'].format_value(value,
                                                                                  figure_type='monetary',
                                                                                  blank_if_zero=True)

                        line['columns'][index_value + (period * 5)] = {
                            'name': formatted_value,
                            'no_format': value,
                            'class': 'number',
                        }

        return {
            'lines': lines,
            'offset_increment': report.load_more_limit,
            'has_more': has_more,
            'progress': json.dumps(next_progress),
        }

    def _read_generic_tax_report_amounts(self, report, options_by_column_group, groupby_fields):
        """ Read the tax details to compute the tax amounts.

        :param options_list:    The list of report options, one for each period.
        :param groupby_fields:  A list of tuple (alias, field) representing the way the amounts must be grouped.
        :return:                A dictionary mapping each groupby key (e.g. a tax_id) to a sub dictionary containing:

            base_amount:    The tax base amount expressed in company's currency.
            tax_amount      The tax amount expressed in company's currency.
            children:       The children nodes following the same pattern as the current dictionary.
        """
        fetch_group_of_taxes = False

        select_clause_list = []
        groupby_query_list = []
        for alias, field in groupby_fields:
            select_clause_list.append(f'{alias}.{field} AS {alias}_{field}')
            groupby_query_list.append(f'{alias}.{field}')

            # Fetch both info from the originator tax and the child tax to manage the group of taxes.
            if alias == 'src_tax':
                select_clause_list.append(f'tax.{field} AS tax_{field}')
                groupby_query_list.append(f'tax.{field}')
                fetch_group_of_taxes = True

        select_clause_str = ','.join(select_clause_list)
        groupby_query_str = ','.join(groupby_query_list)

        # Fetch the group of taxes.
        # If all children taxes are 'none', all amounts are aggregated and only the group will appear on the report.
        # If some children taxes are not 'none', the children are displayed.
        group_of_taxes_to_expand = set()
        if fetch_group_of_taxes:
            group_of_taxes = self.env['account.tax'].with_context(active_test=False).search(
                [('amount_type', '=', 'group')])
            for group in group_of_taxes:
                if set(group.children_tax_ids.mapped('type_tax_use')) != {'none'}:
                    group_of_taxes_to_expand.add(group.id)

        res = {}
        for column_group_key, options in options_by_column_group.items():
            tables, where_clause, where_params = report._query_get(options, 'strict_range')
            tax_details_query, tax_details_params = self.env['account.move.line']._get_query_tax_details(tables,
                                                                                                         where_clause,
                                                                                                         where_params)

            # Avoid adding multiple times the same base amount sharing the same grouping_key.
            # It could happen when dealing with group of taxes for example.
            row_keys = set()

            self._cr.execute(f'''
                SELECT
                    {select_clause_str},
                    trl.refund_tax_id IS NOT NULL AS is_refund,
                    SUM(tdr.base_amount) AS base_amount,
                    SUM(tdr.tax_amount) AS tax_amount
                FROM ({tax_details_query}) AS tdr
                JOIN account_tax_repartition_line trl ON trl.id = tdr.tax_repartition_line_id
                JOIN account_tax tax ON tax.id = tdr.tax_id
                JOIN account_tax src_tax ON
                    src_tax.id = COALESCE(tdr.group_tax_id, tdr.tax_id)
                    AND src_tax.type_tax_use IN ('sale', 'purchase')
                JOIN account_account account ON account.id = trl.account_id 
                WHERE tdr.tax_exigible
                GROUP BY tdr.tax_repartition_line_id, trl.refund_tax_id, tdr.display_type, {groupby_query_str}
                ORDER BY src_tax.sequence, src_tax.id, tax.sequence, tax.id
            ''', tax_details_params)

            for row in self._cr.dictfetchall():
                node = res

                # tuple of values used to prevent adding multiple times the same base amount.
                cumulated_row_key = [row['is_refund']]

                for alias, field in groupby_fields:
                    grouping_key = f'{alias}_{field}'

                    # Manage group of taxes.
                    # In case the group of taxes is mixing multiple taxes having a type_tax_use != 'none', consider
                    # them instead of the group.
                    if grouping_key == 'src_tax_id' and row['src_tax_id'] in group_of_taxes_to_expand:
                        # Add the originator group to the grouping key, to make sure that its base amount is not
                        # treated twice, for hybrid cases where a tax is both used in a group and independently.
                        cumulated_row_key.append(row[grouping_key])

                        # Ensure the child tax is used instead of the group.
                        grouping_key = 'tax_id'

                    row_key = row[grouping_key]
                    cumulated_row_key.append(row_key)
                    cumulated_row_key_tuple = tuple(cumulated_row_key)

                    node.setdefault(row_key, {
                        'base_amount': {column_group_key: 0.0 for column_group_key in options['column_groups']},
                        'tax_amount': {column_group_key: 0.0 for column_group_key in options['column_groups']},
                        'children': {},
                    })
                    sub_node = node[row_key]

                    # Add amounts.
                    if cumulated_row_key_tuple not in row_keys:
                        sub_node['base_amount'][column_group_key] += row['base_amount']
                    sub_node['tax_amount'][column_group_key] += row['tax_amount']

                    node = sub_node['children']
                    row_keys.add(cumulated_row_key_tuple)

        return res

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals):
        res = self._get_dynamic_lines(report, options, 'tax_account')
        date_from = fields.Date.from_string(options['date']['date_from'])
        date_to = fields.Date.from_string(options['date']['date_to'])
        for line in res:
            if options['comparison']['filter'] == 'no_comparison':
                options['column_headers'][0][0][
                    'name'] = f"AYA - Auxiliar de Retenciones entre el: {date_from} y el {date_to}"
                if line[1]['level'] == 1:
                    Rebuild = [{'name': '', 'style': 'white-space:nowrap;'},
                               {'name': '', 'style': 'white-space:nowrap;'},
                               line[1]['columns'][1],
                               {'name': '', 'style': 'white-space:nowrap;'},
                               {'name': '', 'style': 'white-space:nowrap;'}]
                    line[1]['columns'] = []
                    line[1]['columns'] = Rebuild
                elif line[1]['level'] == 2:
                    Rebuild = [{'name': '', 'style': 'white-space:nowrap;'},
                               {'name': '', 'style': 'white-space:nowrap;'},
                               line[1]['columns'][1],
                               {'name': '', 'style': 'white-space:nowrap;'},
                               line[1]['columns'][0]]
                    line[1]['columns'] = []
                    line[1]['columns'] = Rebuild
                elif line[1]['level'] == 3:
                    line[1]['unfoldable'] = True
                    line[1]['unfolded'] = True
                    line[1]['expand_function'] = '_report_expand_unfoldable_line_general_ledger'
                    Rebuild = [{'name': '', 'style': 'white-space:nowrap;'},
                               {'name': '', 'style': 'white-space:nowrap;'},
                               line[1]['columns'][1],
                               {'name': '', 'style': 'white-space:nowrap;'},
                               line[1]['columns'][0]]
                    line[1]['columns'] = []
                    line[1]['columns'] = Rebuild
            else:
                cant_comparison = options['comparison']['number_period']
                index_value = 1
                index_base = 0
                i = 0
                Rebuild = []
                for i in range(i, cant_comparison + 1):
                    if i <= cant_comparison:
                        if line[1]['level'] == 1 or line[1]['level'] == 2:
                            Rebuild.append({'name': '', 'style': 'white-space:nowrap;'})
                            Rebuild.append({'name': '', 'style': 'white-space:nowrap;'})
                            Rebuild.append(line[1]['columns'][index_value])
                            Rebuild.append({'name': '', 'style': 'white-space:nowrap;'})
                            Rebuild.append({'name': '', 'style': 'white-space:nowrap;'})
                            index_value += 2
                            i += 1
                        elif line[1]['level'] == 3:
                            Rebuild.append({'name': '', 'style': 'white-space:nowrap;'})
                            Rebuild.append({'name': '', 'style': 'white-space:nowrap;'})
                            Rebuild.append(line[1]['columns'][index_value])
                            Rebuild.append({'name': '', 'style': 'white-space:nowrap;'})
                            Rebuild.append(line[1]['columns'][index_base])
                            index_value += 2
                            index_base += 2
                            i += 1
                if line[1]['level'] == 3:
                    line[1]['unfoldable'] = True
                    line[1]['unfolded'] = True
                    line[1]['expand_function'] = '_report_expand_unfoldable_line_general_ledger'
                line[1]['columns'] = []
                line[1]['columns'] = Rebuild

        return res


class WAReportCustomHandlerFilter1(models.AbstractModel):
    _name = 'account.withholding.assistant.rte_fuente.report.handler'
    _inherit = 'account.withholding.assistant.report.handler'

    def _read_generic_tax_report_amounts(self, report, options_by_column_group, groupby_fields):
        """ Read the tax details to compute the tax amounts.

        :param options_list:    The list of report options, one for each period.
        :param groupby_fields:  A list of tuple (alias, field) representing the way the amounts must be grouped.
        :return:                A dictionary mapping each groupby key (e.g. a tax_id) to a sub dictionary containing:

            base_amount:    The tax base amount expressed in company's currency.
            tax_amount      The tax amount expressed in company's currency.
            children:       The children nodes following the same pattern as the current dictionary.
        """
        fetch_group_of_taxes = False

        select_clause_list = []
        groupby_query_list = []
        for alias, field in groupby_fields:
            select_clause_list.append(f'{alias}.{field} AS {alias}_{field}')
            groupby_query_list.append(f'{alias}.{field}')

            # Fetch both info from the originator tax and the child tax to manage the group of taxes.
            if alias == 'src_tax':
                select_clause_list.append(f'tax.{field} AS tax_{field}')
                groupby_query_list.append(f'tax.{field}')
                fetch_group_of_taxes = True

        select_clause_str = ','.join(select_clause_list)
        groupby_query_str = ','.join(groupby_query_list)

        # Fetch the group of taxes.
        # If all children taxes are 'none', all amounts are aggregated and only the group will appear on the report.
        # If some children taxes are not 'none', the children are displayed.
        group_of_taxes_to_expand = set()
        if fetch_group_of_taxes:
            group_of_taxes = self.env['account.tax'].with_context(active_test=False).search(
                [('amount_type', '=', 'group')])
            for group in group_of_taxes:
                if set(group.children_tax_ids.mapped('type_tax_use')) != {'none'}:
                    group_of_taxes_to_expand.add(group.id)

        res = {}
        for column_group_key, options in options_by_column_group.items():
            tables, where_clause, where_params = report._query_get(options, 'strict_range')
            tax_details_query, tax_details_params = self.env['account.move.line']._get_query_tax_details(tables,
                                                                                                         where_clause,
                                                                                                         where_params)

            # Avoid adding multiple times the same base amount sharing the same grouping_key.
            # It could happen when dealing with group of taxes for example.
            row_keys = set()

            self._cr.execute(f'''
                SELECT
                    {select_clause_str},
                    trl.refund_tax_id IS NOT NULL AS is_refund,
                    SUM(tdr.base_amount) AS base_amount,
                    SUM(tdr.tax_amount) AS tax_amount
                FROM ({tax_details_query}) AS tdr
                JOIN account_tax_repartition_line trl ON trl.id = tdr.tax_repartition_line_id
                JOIN account_tax tax ON tax.id = tdr.tax_id
                JOIN account_tax src_tax ON
                    src_tax.id = COALESCE(tdr.group_tax_id, tdr.tax_id)
                    AND src_tax.type_tax_use IN ('sale', 'purchase')
                JOIN account_account account ON account.id = trl.account_id
                WHERE tdr.tax_exigible AND src_tax.tributes = '06'
                GROUP BY tdr.tax_repartition_line_id, trl.refund_tax_id, tdr.display_type, {groupby_query_str}
                ORDER BY src_tax.sequence, src_tax.id, tax.sequence, tax.id
            ''', tax_details_params)

            for row in self._cr.dictfetchall():
                node = res

                # tuple of values used to prevent adding multiple times the same base amount.
                cumulated_row_key = [row['is_refund']]

                for alias, field in groupby_fields:
                    grouping_key = f'{alias}_{field}'

                    # Manage group of taxes.
                    # In case the group of taxes is mixing multiple taxes having a type_tax_use != 'none', consider
                    # them instead of the group.
                    if grouping_key == 'src_tax_id' and row['src_tax_id'] in group_of_taxes_to_expand:
                        # Add the originator group to the grouping key, to make sure that its base amount is not
                        # treated twice, for hybrid cases where a tax is both used in a group and independently.
                        cumulated_row_key.append(row[grouping_key])

                        # Ensure the child tax is used instead of the group.
                        grouping_key = 'tax_id'

                    row_key = row[grouping_key]
                    cumulated_row_key.append(row_key)
                    cumulated_row_key_tuple = tuple(cumulated_row_key)

                    node.setdefault(row_key, {
                        'base_amount': {column_group_key: 0.0 for column_group_key in options['column_groups']},
                        'tax_amount': {column_group_key: 0.0 for column_group_key in options['column_groups']},
                        'children': {},
                    })
                    sub_node = node[row_key]

                    # Add amounts.
                    if cumulated_row_key_tuple not in row_keys:
                        sub_node['base_amount'][column_group_key] += row['base_amount']
                    sub_node['tax_amount'][column_group_key] += row['tax_amount']

                    node = sub_node['children']
                    row_keys.add(cumulated_row_key_tuple)

        return res


class WAReportCustomHandlerFilter2(models.AbstractModel):
    _name = 'account.withholding.assistant.rte_ica.report.handler'
    _inherit = 'account.withholding.assistant.report.handler'

    def _read_generic_tax_report_amounts(self, report, options_by_column_group, groupby_fields):
        """ Read the tax details to compute the tax amounts.

        :param options_list:    The list of report options, one for each period.
        :param groupby_fields:  A list of tuple (alias, field) representing the way the amounts must be grouped.
        :return:                A dictionary mapping each groupby key (e.g. a tax_id) to a sub dictionary containing:

            base_amount:    The tax base amount expressed in company's currency.
            tax_amount      The tax amount expressed in company's currency.
            children:       The children nodes following the same pattern as the current dictionary.
        """
        fetch_group_of_taxes = False

        select_clause_list = []
        groupby_query_list = []
        for alias, field in groupby_fields:
            select_clause_list.append(f'{alias}.{field} AS {alias}_{field}')
            groupby_query_list.append(f'{alias}.{field}')

            # Fetch both info from the originator tax and the child tax to manage the group of taxes.
            if alias == 'src_tax':
                select_clause_list.append(f'tax.{field} AS tax_{field}')
                groupby_query_list.append(f'tax.{field}')
                fetch_group_of_taxes = True

        select_clause_str = ','.join(select_clause_list)
        groupby_query_str = ','.join(groupby_query_list)

        # Fetch the group of taxes.
        # If all children taxes are 'none', all amounts are aggregated and only the group will appear on the report.
        # If some children taxes are not 'none', the children are displayed.
        group_of_taxes_to_expand = set()
        if fetch_group_of_taxes:
            group_of_taxes = self.env['account.tax'].with_context(active_test=False).search(
                [('amount_type', '=', 'group')])
            for group in group_of_taxes:
                if set(group.children_tax_ids.mapped('type_tax_use')) != {'none'}:
                    group_of_taxes_to_expand.add(group.id)

        res = {}
        for column_group_key, options in options_by_column_group.items():
            tables, where_clause, where_params = report._query_get(options, 'strict_range')
            tax_details_query, tax_details_params = self.env['account.move.line']._get_query_tax_details(tables,
                                                                                                         where_clause,
                                                                                                         where_params)

            # Avoid adding multiple times the same base amount sharing the same grouping_key.
            # It could happen when dealing with group of taxes for example.
            row_keys = set()

            self._cr.execute(f'''
                SELECT
                    {select_clause_str},
                    trl.refund_tax_id IS NOT NULL AS is_refund,
                    SUM(tdr.base_amount) AS base_amount,
                    SUM(tdr.tax_amount) AS tax_amount
                FROM ({tax_details_query}) AS tdr
                JOIN account_tax_repartition_line trl ON trl.id = tdr.tax_repartition_line_id
                JOIN account_tax tax ON tax.id = tdr.tax_id
                JOIN account_tax src_tax ON
                    src_tax.id = COALESCE(tdr.group_tax_id, tdr.tax_id)
                    AND src_tax.type_tax_use IN ('sale', 'purchase')
                JOIN account_account account ON account.id = trl.account_id
                WHERE tdr.tax_exigible AND src_tax.tributes = '07'
                GROUP BY tdr.tax_repartition_line_id, trl.refund_tax_id, tdr.display_type, {groupby_query_str}
                ORDER BY src_tax.sequence, src_tax.id, tax.sequence, tax.id
            ''', tax_details_params)

            for row in self._cr.dictfetchall():
                node = res

                # tuple of values used to prevent adding multiple times the same base amount.
                cumulated_row_key = [row['is_refund']]

                for alias, field in groupby_fields:
                    grouping_key = f'{alias}_{field}'

                    # Manage group of taxes.
                    # In case the group of taxes is mixing multiple taxes having a type_tax_use != 'none', consider
                    # them instead of the group.
                    if grouping_key == 'src_tax_id' and row['src_tax_id'] in group_of_taxes_to_expand:
                        # Add the originator group to the grouping key, to make sure that its base amount is not
                        # treated twice, for hybrid cases where a tax is both used in a group and independently.
                        cumulated_row_key.append(row[grouping_key])

                        # Ensure the child tax is used instead of the group.
                        grouping_key = 'tax_id'

                    row_key = row[grouping_key]
                    cumulated_row_key.append(row_key)
                    cumulated_row_key_tuple = tuple(cumulated_row_key)

                    node.setdefault(row_key, {
                        'base_amount': {column_group_key: 0.0 for column_group_key in options['column_groups']},
                        'tax_amount': {column_group_key: 0.0 for column_group_key in options['column_groups']},
                        'children': {},
                    })
                    sub_node = node[row_key]

                    # Add amounts.
                    if cumulated_row_key_tuple not in row_keys:
                        sub_node['base_amount'][column_group_key] += row['base_amount']
                    sub_node['tax_amount'][column_group_key] += row['tax_amount']

                    node = sub_node['children']
                    row_keys.add(cumulated_row_key_tuple)

        return res


class WAReportCustomHandlerFilter3(models.AbstractModel):
    _name = 'account.withholding.assistant.rte_iva.report.handler'
    _inherit = 'account.withholding.assistant.report.handler'

    def _read_generic_tax_report_amounts(self, report, options_by_column_group, groupby_fields):
        """ Read the tax details to compute the tax amounts.

        :param options_list:    The list of report options, one for each period.
        :param groupby_fields:  A list of tuple (alias, field) representing the way the amounts must be grouped.
        :return:                A dictionary mapping each groupby key (e.g. a tax_id) to a sub dictionary containing:

            base_amount:    The tax base amount expressed in company's currency.
            tax_amount      The tax amount expressed in company's currency.
            children:       The children nodes following the same pattern as the current dictionary.
        """
        fetch_group_of_taxes = False

        select_clause_list = []
        groupby_query_list = []
        for alias, field in groupby_fields:
            select_clause_list.append(f'{alias}.{field} AS {alias}_{field}')
            groupby_query_list.append(f'{alias}.{field}')

            # Fetch both info from the originator tax and the child tax to manage the group of taxes.
            if alias == 'src_tax':
                select_clause_list.append(f'tax.{field} AS tax_{field}')
                groupby_query_list.append(f'tax.{field}')
                fetch_group_of_taxes = True

        select_clause_str = ','.join(select_clause_list)
        groupby_query_str = ','.join(groupby_query_list)

        # Fetch the group of taxes.
        # If all children taxes are 'none', all amounts are aggregated and only the group will appear on the report.
        # If some children taxes are not 'none', the children are displayed.
        group_of_taxes_to_expand = set()
        if fetch_group_of_taxes:
            group_of_taxes = self.env['account.tax'].with_context(active_test=False).search(
                [('amount_type', '=', 'group')])
            for group in group_of_taxes:
                if set(group.children_tax_ids.mapped('type_tax_use')) != {'none'}:
                    group_of_taxes_to_expand.add(group.id)

        res = {}
        for column_group_key, options in options_by_column_group.items():
            tables, where_clause, where_params = report._query_get(options, 'strict_range')
            tax_details_query, tax_details_params = self.env['account.move.line']._get_query_tax_details(tables,
                                                                                                         where_clause,
                                                                                                         where_params)

            # Avoid adding multiple times the same base amount sharing the same grouping_key.
            # It could happen when dealing with group of taxes for example.
            row_keys = set()

            self._cr.execute(f'''
                SELECT
                    {select_clause_str},
                    trl.refund_tax_id IS NOT NULL AS is_refund,
                    SUM(tdr.base_amount) AS base_amount,
                    SUM(tdr.tax_amount) AS tax_amount
                FROM ({tax_details_query}) AS tdr
                JOIN account_tax_repartition_line trl ON trl.id = tdr.tax_repartition_line_id
                JOIN account_tax tax ON tax.id = tdr.tax_id
                JOIN account_tax src_tax ON
                    src_tax.id = COALESCE(tdr.group_tax_id, tdr.tax_id)
                    AND src_tax.type_tax_use IN ('sale', 'purchase')
                JOIN account_account account ON account.id = trl.account_id
                WHERE tdr.tax_exigible AND src_tax.tributes = '05'
                GROUP BY tdr.tax_repartition_line_id, trl.refund_tax_id, tdr.display_type, {groupby_query_str}
                ORDER BY src_tax.sequence, src_tax.id, tax.sequence, tax.id
            ''', tax_details_params)

            for row in self._cr.dictfetchall():
                node = res

                # tuple of values used to prevent adding multiple times the same base amount.
                cumulated_row_key = [row['is_refund']]

                for alias, field in groupby_fields:
                    grouping_key = f'{alias}_{field}'

                    # Manage group of taxes.
                    # In case the group of taxes is mixing multiple taxes having a type_tax_use != 'none', consider
                    # them instead of the group.
                    if grouping_key == 'src_tax_id' and row['src_tax_id'] in group_of_taxes_to_expand:
                        # Add the originator group to the grouping key, to make sure that its base amount is not
                        # treated twice, for hybrid cases where a tax is both used in a group and independently.
                        cumulated_row_key.append(row[grouping_key])

                        # Ensure the child tax is used instead of the group.
                        grouping_key = 'tax_id'

                    row_key = row[grouping_key]
                    cumulated_row_key.append(row_key)
                    cumulated_row_key_tuple = tuple(cumulated_row_key)

                    node.setdefault(row_key, {
                        'base_amount': {column_group_key: 0.0 for column_group_key in options['column_groups']},
                        'tax_amount': {column_group_key: 0.0 for column_group_key in options['column_groups']},
                        'children': {},
                    })
                    sub_node = node[row_key]

                    # Add amounts.
                    if cumulated_row_key_tuple not in row_keys:
                        sub_node['base_amount'][column_group_key] += row['base_amount']
                    sub_node['tax_amount'][column_group_key] += row['tax_amount']

                    node = sub_node['children']
                    row_keys.add(cumulated_row_key_tuple)

        return res
