# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import datetime
import io
import json
import logging
import math
import re
import base64
from ast import literal_eval
from collections import defaultdict
from functools import cmp_to_key

import markupsafe
from babel.dates import get_quarter_names
from dateutil.relativedelta import relativedelta

from odoo.addons.web.controllers.utils import clean_action
from odoo import models, fields, api, _, osv, _lt
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.tools import config, date_utils, get_lang, float_compare, float_is_zero
from odoo.tools.float_utils import float_round
from odoo.tools.misc import formatLang, format_date, xlsxwriter
from odoo.tools.safe_eval import expr_eval, safe_eval
from odoo.models import check_method_name

_logger = logging.getLogger(__name__)

ACCOUNT_CODES_ENGINE_SPLIT_REGEX = re.compile(r"(?=[+-])")

ACCOUNT_CODES_ENGINE_TERM_REGEX = re.compile(
    r"^(?P<sign>[+-]?)"\
    r"(?P<prefix>([A-Za-z\d.]*|tag\([\w.]+\))((?=\\)|(?<=[^CD])))"\
    r"(\\\((?P<excluded_prefixes>([A-Za-z\d.]+,)*[A-Za-z\d.]*)\))?"\
    r"(?P<balance_character>[DC]?)$"
)

ACCOUNT_CODES_ENGINE_TAG_ID_PREFIX_REGEX = re.compile(r"tag\(((?P<id>\d+)|(?P<ref>\w+\.\w+))\)")

# Performance optimisation: those engines always will receive None as their next_groupby, allowing more efficient batching.
NO_NEXT_GROUPBY_ENGINES = {'tax_tags', 'account_codes'}

LINE_ID_HIERARCHY_DELIMITER = '|'

class AccountReport(models.AbstractModel):
    _inherit = 'account.report'

    CURRENCY_DIF = None

    search_template = fields.Char(string="Search Template", required=True, compute='_compute_search_template',
                                  default='account_dual_currency.search_template_generic_currency_dif')

    def export_to_pdf(self, options):
        self.ensure_one()
        # As the assets are generated during the same transaction as the rendering of the
        # templates calling them, there is a scenario where the assets are unreachable: when
        # you make a request to read the assets while the transaction creating them is not done.
        # Indeed, when you make an asset request, the controller has to read the `ir.attachment`
        # table.
        # This scenario happens when you want to print a PDF report for the first time, as the
        # assets are not in cache and must be generated. To workaround this issue, we manually
        # commit the writes in the `ir.attachment` table. It is done thanks to a key in the context.
        if not config['test_enable']:
            self = self.with_context(commit_assetsbundle=True)

        base_url = self.env['ir.config_parameter'].sudo().get_param('report.url') or self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        rcontext = {
            'mode': 'print',
            'base_url': base_url,
            'company': self.env.company,
        }
        new_context = {
            **self._context,
            'currency_dif': options['currency_dif'],
            'currency_id_company_name': options['currency_id_company_name'],
        }
        self.env.context = new_context
        print_mode_self = self.with_context(print_mode=True)

        body_html = print_mode_self.get_html(options, print_mode_self._get_lines(options))
        body = self.env['ir.ui.view']._render_template(
            "account_reports.print_template",
            values=dict(rcontext, body_html=body_html),
        )
        footer = self.env['ir.actions.report']._render_template("web.internal_layout", values=rcontext)
        footer = self.env['ir.actions.report']._render_template("web.minimal_layout", values=dict(rcontext, subst=True, body=markupsafe.Markup(footer.decode())))

        landscape = False
        if len(options['columns']) * len(options['column_groups']) > 5:
            landscape = True

        file_content = self.env['ir.actions.report']._run_wkhtmltopdf(
            [body],
            footer=footer.decode(),
            landscape=landscape,
            specific_paperformat_args={
                'data-report-margin-top': 10,
                'data-report-header-spacing': 10
            }
        )

        return {
            'file_name': self.get_default_report_filename('pdf'),
            'file_content': file_content,
            'file_type': 'pdf',
        }

    def _compute_search_template(self):
        self.search_template = 'account_dual_currency.search_template_generic_currency_dif'


    def _get_options(self, previous_options=None):
        self.ensure_one()
        # Create default options.
        options = {'unfolded_lines': (previous_options or {}).get('unfolded_lines', [])}

        if (previous_options or {}).get('_running_export_test'):
            options['_running_export_test'] = True

        for initializer in self._get_options_initializers_in_sequence():
            initializer(options, previous_options=previous_options)

        # Sort the buttons list by sequence, for rendering
        options['buttons'] = sorted(options['buttons'], key=lambda x: x.get('sequence', 90))

        currency_id_company_name = 'Bs'
        currency_id_dif_name = 'USD'
        if self._context.get('allowed_company_ids'):
            company_id = self._context.get('allowed_company_ids')[0]
            company = self.env['res.company'].browse(company_id)
            if company:
                currency_id_company_name = company.currency_id.symbol
                currency_id_dif_name = company.currency_id_dif.symbol
        currency_dif = currency_id_company_name
        if previous_options:
            if "currency_dif" in previous_options:
                currency_dif = previous_options['currency_dif']
        options['currency_dif'] = currency_dif
        options['currency_id_company_name'] = currency_id_company_name
        options['currency_id_dif_name'] = currency_id_dif_name
        new_context = {
            **self._context,
            'currency_dif': currency_dif,
            'currency_id_company_name': currency_id_company_name,
        }
        self.env.context = new_context
        return options

    @api.model
    def format_value(self, value, currency=False, blank_if_zero=True, figure_type=None, digits=1):
        """ Formats a value for display in a report (not especially numerical). figure_type provides the type of formatting we want.
        """
        if figure_type == 'none':
            return value

        if value is None:
            return ''

        if figure_type == 'monetary':
            currency = currency or self.env.company.currency_id
            if self._context.get('currency_dif'):
                if self._context.get('currency_dif') == self._context.get('currency_id_company_name'):
                    currency = self.env.company.currency_id
                else:
                    currency = self.env.company.currency_id_dif
            digits = None
        elif figure_type == 'integer':
            currency = None
            digits = 0
        elif figure_type in ('date', 'datetime'):
            return format_date(self.env, value)
        else:
            currency = None

        if self.is_zero(value, currency=currency, figure_type=figure_type, digits=digits):
            if blank_if_zero:
                return ''
            # don't print -0.0 in reports
            value = abs(value)

        if self._context.get('no_format'):
            return value

        formatted_amount = formatLang(self.env, value, currency_obj=currency, digits=digits)

        if figure_type == 'percentage':
            return f"{formatted_amount}%"

        return formatted_amount


    def _compute_formula_batch_with_engine_domain(self, options, date_scope, formulas_dict, current_groupby, next_groupby, offset=0, limit=None):
        """ Report engine.

        Formulas made for this engine consist of a domain on account.move.line. Only those move lines will be used to compute the result.

        This engine supports a few subformulas, each returning a slighlty different result:
        - sum: the result will be sum of the matched move lines' balances

        - sum_if_pos: the result will be the same as sum only if it's positive; else, it will be 0

        - sum_if_neg: the result will be the same as sum only if it's negative; else, it will be 0

        - count_rows: the result will be the number of sublines this expression has. If the parent report line has no groupby,
                      then it will be the number of matching amls. If there is a groupby, it will be the number of distinct grouping
                      keys at the first level of this groupby (so, if groupby is 'partner_id, account_id', the number of partners).
        """
        currency_dif = options['currency_dif']
        def _format_result_depending_on_groupby(formula_rslt):
            if not current_groupby:
                if formula_rslt:
                    # There should be only one element in the list; we only return its totals (a dict) ; so that a list is only returned in case
                    # of a groupby being unfolded.
                    return formula_rslt[0][1]
                else:
                    # No result at all
                    return {
                        'sum': 0,
                        'sum_if_pos': 0,
                        'sum_if_neg': 0,
                        'count_rows': 0,
                        'has_sublines': False,
                    }
            return formula_rslt

        self._check_groupby_fields((next_groupby.split(',') if next_groupby else []) + ([current_groupby] if current_groupby else []))

        groupby_sql = f'account_move_line.{current_groupby}' if current_groupby else None
        ct_query = self.env['res.currency']._get_query_currency_table(options)

        rslt = {}

        for formula, expressions in formulas_dict.items():
            try:
                line_domain = literal_eval(formula)
            except (ValueError, SyntaxError):
                raise UserError(_("Invalid domain formula in expression %r of line %r: %s", expressions.label, expressions.report_line_id.name, formula))
            tables, where_clause, where_params = self._query_get(options, date_scope, domain=line_domain)

            tail_query, tail_params = self._get_engine_query_tail(offset, limit)
            if currency_dif == self.env.company.currency_id.symbol:
                query = f"""
                    SELECT
                        COALESCE(SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)), 0.0) AS sum,
                        COUNT(DISTINCT account_move_line.{next_groupby.split(',')[0] if next_groupby else 'id'}) AS count_rows
                        {f', {groupby_sql} AS grouping_key' if groupby_sql else ''}
                    FROM {tables}
                    JOIN {ct_query} ON currency_table.company_id = account_move_line.company_id
                    WHERE {where_clause}
                    {f' GROUP BY {groupby_sql}' if groupby_sql else ''}
                    {tail_query}
                """
            else:
                query = f"""
                                    SELECT
                                        COALESCE(SUM(ROUND(account_move_line.balance_usd * currency_table.rate, currency_table.precision)), 0.0) AS sum,
                                        COUNT(DISTINCT account_move_line.{next_groupby.split(',')[0] if next_groupby else 'id'}) AS count_rows
                                        {f', {groupby_sql} AS grouping_key' if groupby_sql else ''}
                                    FROM {tables}
                                    JOIN {ct_query} ON currency_table.company_id = account_move_line.company_id
                                    WHERE {where_clause}
                                    {f' GROUP BY {groupby_sql}' if groupby_sql else ''}
                                    {tail_query}
                                """

            # Fetch the results.
            formula_rslt = []
            self._cr.execute(query, where_params + tail_params)
            all_query_res = self._cr.dictfetchall()

            total_sum = 0
            for query_res in all_query_res:
                res_sum = query_res['sum']
                total_sum += res_sum
                totals = {
                    'sum': res_sum,
                    'sum_if_pos': 0,
                    'sum_if_neg': 0,
                    'count_rows': query_res['count_rows'],
                    'has_sublines': query_res['count_rows'] > 0,
                }
                formula_rslt.append((query_res.get('grouping_key', None), totals))

            # Handle sum_if_pos, -sum_if_pos, sum_if_neg and -sum_if_neg
            expressions_by_sign_policy = defaultdict(lambda: self.env['account.report.expression'])
            for expression in expressions:
                subformula_without_sign = expression.subformula.replace('-', '').strip()
                if subformula_without_sign in ('sum_if_pos', 'sum_if_neg'):
                    expressions_by_sign_policy[subformula_without_sign] += expression
                else:
                    expressions_by_sign_policy['no_sign_check'] += expression

            # Then we have to check the total of the line and only give results if its sign matches the desired policy.
            # This is important for groupby managements, for which we can't just check the sign query_res by query_res
            if expressions_by_sign_policy['sum_if_pos'] or expressions_by_sign_policy['sum_if_neg']:
                sign_policy_with_value = 'sum_if_pos' if self.env.company.currency_id.compare_amounts(total_sum, 0.0) >= 0 else 'sum_if_neg'
                # >= instead of > is intended; usability decision: 0 is considered positive

                formula_rslt_with_sign = [(grouping_key, {**totals, sign_policy_with_value: totals['sum']}) for grouping_key, totals in formula_rslt]

                for sign_policy in ('sum_if_pos', 'sum_if_neg'):
                    policy_expressions = expressions_by_sign_policy[sign_policy]

                    if policy_expressions:
                        if sign_policy == sign_policy_with_value:
                            rslt[(formula, policy_expressions)] = _format_result_depending_on_groupby(formula_rslt_with_sign)
                        else:
                            rslt[(formula, policy_expressions)] = _format_result_depending_on_groupby([])

            if expressions_by_sign_policy['no_sign_check']:
                rslt[(formula, expressions_by_sign_policy['no_sign_check'])] = _format_result_depending_on_groupby(formula_rslt)

        return rslt
    @api.model
    def _prepare_lines_for_cash_basis(self):
        """Prepare the cash_basis_temp_account_move_line substitue.

        This method should be used once before all the SQL queries using the
        table account_move_line for reports in cash basis.
        It will create a new table like the account_move_line table, but with
        amounts and the date relative to the cash basis.
        """
        self.env.cr.execute("SELECT 1 FROM information_schema.tables WHERE table_name='cash_basis_temp_account_move_line'")
        if self.env.cr.fetchone():
            return

        self.env.cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='account_move_line'")
        changed_fields = ['date', 'amount_currency', 'amount_residual', 'balance', 'debit', 'credit']
        unchanged_fields = list(set(f[0] for f in self.env.cr.fetchall()) - set(changed_fields))
        selected_journals = tuple(self.env.context.get('journal_ids', []))
        sql = """   -- Create a temporary table
                CREATE TEMPORARY TABLE IF NOT EXISTS cash_basis_temp_account_move_line () INHERITS (account_move_line) ON COMMIT DROP;

                INSERT INTO cash_basis_temp_account_move_line ({all_fields}) SELECT
                    {unchanged_fields},
                    "account_move_line".date,
                    "account_move_line".amount_currency,
                    "account_move_line".amount_residual,
                    "account_move_line".balance,
                    "account_move_line".debit,
                    "account_move_line".credit,
                    "account_move_line".amount_residual_usd,
                    "account_move_line".balance_usd,
                    "account_move_line".debit_usd,
                    "account_move_line".credit_usd
                FROM ONLY account_move_line
                WHERE (
                    "account_move_line".journal_id IN (SELECT id FROM account_journal WHERE type in ('cash', 'bank'))
                    OR "account_move_line".move_id NOT IN (
                        SELECT DISTINCT aml.move_id
                        FROM ONLY account_move_line aml
                        JOIN account_account account ON aml.account_id = account.id
                        WHERE account.account_type IN ('asset_receivable', 'liability_payable')
                    )
                )
                {where_journals};

                WITH payment_table AS (
                    SELECT
                        aml.move_id,
                        GREATEST(aml.date, aml2.date) AS date,
                        CASE WHEN (aml.balance = 0 OR sub_aml.total_per_account = 0)
                            THEN 0
                            ELSE part.amount / ABS(sub_aml.total_per_account)
                        END as matched_percentage
                    FROM account_partial_reconcile part
                    JOIN ONLY account_move_line aml ON aml.id = part.debit_move_id OR aml.id = part.credit_move_id
                    JOIN ONLY account_move_line aml2 ON
                        (aml2.id = part.credit_move_id OR aml2.id = part.debit_move_id)
                        AND aml.id != aml2.id
                    JOIN (
                        SELECT move_id, account_id, SUM(ABS(balance)) AS total_per_account
                        FROM ONLY account_move_line account_move_line
                        GROUP BY move_id, account_id
                    ) sub_aml ON (aml.account_id = sub_aml.account_id AND aml.move_id=sub_aml.move_id)
                    JOIN account_account account ON aml.account_id = account.id
                    WHERE account.account_type IN ('asset_receivable', 'liability_payable')
                )
                INSERT INTO cash_basis_temp_account_move_line ({all_fields}) SELECT
                    {unchanged_fields},
                    ref.date,
                    ref.matched_percentage * "account_move_line".amount_currency,
                    ref.matched_percentage * "account_move_line".amount_residual,
                    ref.matched_percentage * "account_move_line".balance,
                    ref.matched_percentage * "account_move_line".debit,
                    ref.matched_percentage * "account_move_line".credit,
                    ref.matched_percentage * "account_move_line".amount_residual_usd,
                    ref.matched_percentage * "account_move_line".balance_usd,
                    ref.matched_percentage * "account_move_line".debit_usd,
                    ref.matched_percentage * "account_move_line".credit_usd
                FROM payment_table ref
                JOIN ONLY account_move_line account_move_line ON "account_move_line".move_id = ref.move_id
                WHERE NOT (
                    "account_move_line".journal_id IN (SELECT id FROM account_journal WHERE type in ('cash', 'bank'))
                    OR "account_move_line".move_id NOT IN (
                        SELECT DISTINCT aml.move_id
                        FROM ONLY account_move_line aml
                        JOIN account_account account ON aml.account_id = account.id
                        WHERE account.account_type IN ('asset_receivable', 'liability_payable')
                    )
                )
                {where_journals};

                -- Create an composite index to avoid seq.scan
                CREATE INDEX IF NOT EXISTS cash_basis_temp_account_move_line_composite_idx on cash_basis_temp_account_move_line(date, journal_id, company_id, parent_state);
                -- Update statistics for correct planning
                ANALYZE cash_basis_temp_account_move_line;
            """.format(
            all_fields=', '.join(f'"{f}"' for f in (unchanged_fields + changed_fields)),
            unchanged_fields=', '.join([f'"account_move_line"."{f}"' for f in unchanged_fields]),
            where_journals=selected_journals and 'AND "account_move_line".journal_id IN %(journal_ids)s' or ''
        )
        params = {
            'journal_ids': selected_journals,
        }
        self.env.cr.execute(sql, params)