import json

from bs4 import BeautifulSoup

from odoo import models, fields, api, _
from odoo.tools.misc import format_date
from odoo.tools import get_lang
from odoo.exceptions import UserError

from datetime import timedelta
from collections import defaultdict


class GeneralLedgerCustomHandler(models.AbstractModel):
    _name = 'account.general.ledger.report.handler.tp.gl'
    _inherit = 'account.general.ledger.report.handler'

    def _report_expand_unfoldable_line_general_ledger(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        def init_load_more_progress(line_dict):
            return {
                column['column_group_key']: line_col.get('no_format', 0)
                for column, line_col in  zip(options['columns'], line_dict['columns'])
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
                account, init_balance_by_col_group = self._get_initial_balance_values(report, [model_id], options)[model_id]

            initial_balance_line = report._get_partner_and_general_ledger_initial_balance_line(options, line_dict_id, init_balance_by_col_group, account.currency_id)

            if initial_balance_line:
                lines.append(initial_balance_line)

                # For the first expansion of the line, the initial balance line gives the progress
                progress = init_load_more_progress(initial_balance_line)

        # Get move lines
        limit_to_load = report.load_more_limit + 1 if report.load_more_limit and not self._context.get('print_mode') else None
        has_more = False
        if unfold_all_batch_data:
            aml_results = unfold_all_batch_data['aml_values'][model_id]
        else:
            aml_results, has_more = self._get_aml_values(report, options, [model_id], offset=offset, limit=limit_to_load)
            aml_results = aml_results[model_id]

        next_progress = progress
        for aml_result in aml_results.values():
            new_line = self._get_aml_line(report, line_dict_id, options, aml_result, next_progress)
            lines.append(new_line)
            next_progress = init_load_more_progress(new_line)

        for line in lines:
            note = line['columns'][2]['no_format'] if 'no_format' in line['columns'][2] else False
            if note:
                soup = BeautifulSoup(note, 'html.parser')
                clean_string = soup.get_text()
                formatted_value = self.env['account.report'].format_value(clean_string,
                                                                          figure_type='none')
                col_class = 'o_account_report_line_ellipsis'
                line['columns'][2] = {
                    'name': formatted_value,
                    'no_format': clean_string,
                    'class': col_class,
                }

        return {
            'lines': lines,
            'offset_increment': report.load_more_limit,
            'has_more': has_more,
            'progress': json.dumps(next_progress),
        }

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
                            'amount_currency',
                            0.0),
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
        options['column_headers'][0][0]['name'] = f"Libro Auxiliar entre el: {date_from} y el {date_to}"
        # Falta Cheque
        options['columns'][0]['name'] = 'Fecha'
        options['columns'][1]['name'] = 'Nota'
        options['columns'][2]['name'] = 'Numero de Cheque'
        options['columns'][3]['name'] = 'Doc num'
        options['columns'][4]['name'] = 'Débito'
        options['columns'][5]['name'] = 'Crédito'
        options['columns'][6]['name'] = 'Saldo'

        return [(0, line) for line in lines]

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
                    move.narration                          AS narration,
                    move.ref                                AS check_number,
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
                LEFT JOIN account_payment ap                ON account_move_line.payment_id = ap.id
                LEFT JOIN account_payment_method apm        ON ap.payment_method_id = apm.id
                LEFT JOIN account_full_reconcile full_rec   ON full_rec.id = account_move_line.full_reconcile_id
                WHERE {where_clause} AND account_move_line.partner_id IS NOT NULL
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
                        formatted_value = report.format_value(col_value, currency=currency, figure_type=column['figure_type'])
                    else:
                        formatted_value = ''
                elif col_expr_label == 'date':
                    formatted_value = format_date(self.env, col_value)
                    col_class = 'date'
                elif col_expr_label == 'balance':
                    col_value += init_bal_by_col_group[column['column_group_key']]
                    formatted_value = report.format_value(col_value, figure_type=column['figure_type'], blank_if_zero=False)
                elif col_expr_label == 'communication' or col_expr_label == 'partner_name' or\
                        col_expr_label == 'narration' or col_expr_label == 'check_number':
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

        first_column_group_key = options['columns'][0]['column_group_key']
        if eval_dict[first_column_group_key]['payment_id']:
            caret_type = 'account.payment'
        else:
            caret_type = 'account.move.line'

        return {
            'id': report._get_generic_line_id('account.move.line', eval_dict[first_column_group_key]['id'], parent_line_id=parent_line_id),
            'caret_options': caret_type,
            'parent_id': parent_line_id,
            'name': eval_dict[first_column_group_key]['partner_name'],
            'columns': line_columns,
            'level': 2,
        }
