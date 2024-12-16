# -*- coding: utf-8 -*-
# parte de reportes con impuestos
from collections import defaultdict

from odoo import models, api, fields, Command, _
from odoo.addons.web.controllers.utils import clean_action
from odoo.exceptions import UserError, RedirectWarning
from odoo.osv import expression
from odoo.tools.misc import get_lang


class GenericTaxReportCustomHandler(models.AbstractModel):
    _inherit = 'account.generic.tax.report.handler'

    @api.model
    def _read_generic_tax_report_amounts_no_tax_details(self, report, options, options_by_column_group):
        # Fetch the group of taxes.
        # If all child taxes have a 'none' type_tax_use, all amounts are aggregated and only the group appears on the report.
        currency_dif = options['currency_dif']
        self._cr.execute(
            '''
                SELECT
                    group_tax.id,
                    group_tax.type_tax_use,
                    ARRAY_AGG(child_tax.id) AS child_tax_ids,
                    ARRAY_AGG(DISTINCT child_tax.type_tax_use) AS child_types
                FROM account_tax_filiation_rel group_tax_rel
                JOIN account_tax group_tax ON group_tax.id = group_tax_rel.parent_tax
                JOIN account_tax child_tax ON child_tax.id = group_tax_rel.child_tax
                WHERE group_tax.amount_type = 'group' AND group_tax.company_id IN %s
                GROUP BY group_tax.id
            ''',
            [tuple(comp['id'] for comp in options.get('multi_company', self.env.company))],
        )
        group_of_taxes_info = {}
        child_to_group_of_taxes = {}
        for row in self._cr.dictfetchall():
            row['to_expand'] = row['child_types'] != ['none']
            group_of_taxes_info[row['id']] = row
            for child_id in row['child_tax_ids']:
                child_to_group_of_taxes[child_id] = row['id']

        results = defaultdict(lambda: {  # key: type_tax_use
            'base_amount': {column_group_key: 0.0 for column_group_key in options['column_groups']},
            'tax_amount': {column_group_key: 0.0 for column_group_key in options['column_groups']},
            'children': defaultdict(lambda: {  # key: tax_id
                'base_amount': {column_group_key: 0.0 for column_group_key in options['column_groups']},
                'tax_amount': {column_group_key: 0.0 for column_group_key in options['column_groups']},
            }),
        })

        for column_group_key, options in options_by_column_group.items():
            tables, where_clause, where_params = report._query_get(options, 'strict_range')

            # Fetch the base amounts.
            if currency_dif == self.env.company.currency_id.symbol:
                self._cr.execute(f'''
                        SELECT
                            tax.id AS tax_id,
                            tax.type_tax_use AS tax_type_tax_use,
                            src_group_tax.id AS src_group_tax_id,
                            src_group_tax.type_tax_use AS src_group_tax_type_tax_use,
                            src_tax.id AS src_tax_id,
                            src_tax.type_tax_use AS src_tax_type_tax_use,
                            SUM(account_move_line.balance) AS base_amount
                        FROM {tables}
                        JOIN account_move_line_account_tax_rel tax_rel ON account_move_line.id = tax_rel.account_move_line_id
                        JOIN account_tax tax ON tax.id = tax_rel.account_tax_id
                        LEFT JOIN account_tax src_tax ON src_tax.id = account_move_line.tax_line_id
                        LEFT JOIN account_tax src_group_tax ON src_group_tax.id = account_move_line.group_tax_id
                        WHERE {where_clause}
                            AND (
                                /* CABA */
                                account_move_line__move_id.always_tax_exigible
                                OR account_move_line__move_id.tax_cash_basis_rec_id IS NOT NULL
                                OR tax.tax_exigibility != 'on_payment'
                            )
                            AND (
                                (
                                    /* Tax lines affecting the base of others. */
                                    account_move_line.tax_line_id IS NOT NULL
                                    AND (
                                        src_tax.type_tax_use IN ('sale', 'purchase')
                                        OR src_group_tax.type_tax_use IN ('sale', 'purchase')
                                    )
                                )
                                OR
                                (
                                    /* For regular base lines. */
                                    account_move_line.tax_line_id IS NULL
                                    AND tax.type_tax_use IN ('sale', 'purchase')
                                )
                            )
                        GROUP BY tax.id, src_group_tax.id, src_tax.id
                        ORDER BY src_group_tax.sequence, src_group_tax.id, src_tax.sequence, src_tax.id, tax.sequence, tax.id
                    ''', where_params)
            else:
                self._cr.execute(f'''
                                        SELECT
                                            tax.id AS tax_id,
                                            tax.type_tax_use AS tax_type_tax_use,
                                            src_group_tax.id AS src_group_tax_id,
                                            src_group_tax.type_tax_use AS src_group_tax_type_tax_use,
                                            src_tax.id AS src_tax_id,
                                            src_tax.type_tax_use AS src_tax_type_tax_use,
                                            SUM(account_move_line.balance_usd) AS base_amount
                                        FROM {tables}
                                        JOIN account_move_line_account_tax_rel tax_rel ON account_move_line.id = tax_rel.account_move_line_id
                                        JOIN account_tax tax ON tax.id = tax_rel.account_tax_id
                                        LEFT JOIN account_tax src_tax ON src_tax.id = account_move_line.tax_line_id
                                        LEFT JOIN account_tax src_group_tax ON src_group_tax.id = account_move_line.group_tax_id
                                        WHERE {where_clause}
                                            AND (
                                                /* CABA */
                                                account_move_line__move_id.always_tax_exigible
                                                OR account_move_line__move_id.tax_cash_basis_rec_id IS NOT NULL
                                                OR tax.tax_exigibility != 'on_payment'
                                            )
                                            AND (
                                                (
                                                    /* Tax lines affecting the base of others. */
                                                    account_move_line.tax_line_id IS NOT NULL
                                                    AND (
                                                        src_tax.type_tax_use IN ('sale', 'purchase')
                                                        OR src_group_tax.type_tax_use IN ('sale', 'purchase')
                                                    )
                                                )
                                                OR
                                                (
                                                    /* For regular base lines. */
                                                    account_move_line.tax_line_id IS NULL
                                                    AND tax.type_tax_use IN ('sale', 'purchase')
                                                )
                                            )
                                        GROUP BY tax.id, src_group_tax.id, src_tax.id
                                        ORDER BY src_group_tax.sequence, src_group_tax.id, src_tax.sequence, src_tax.id, tax.sequence, tax.id
                                    ''', where_params)

            group_of_taxes_with_extra_base_amount = set()
            for row in self._cr.dictfetchall():
                is_tax_line = bool(row['src_tax_id'])
                if is_tax_line:
                    if row['src_group_tax_id'] \
                            and not group_of_taxes_info[row['src_group_tax_id']]['to_expand'] \
                            and row['tax_id'] in group_of_taxes_info[row['src_group_tax_id']]['child_tax_ids']:
                        # Suppose a base of 1000 with a group of taxes 20% affect + 10%.
                        # The base of the group of taxes must be 1000, not 1200 because the group of taxes is not
                        # expanded. So the tax lines affecting the base of its own group of taxes are ignored.
                        pass
                    elif row['tax_type_tax_use'] == 'none' and child_to_group_of_taxes.get(row['tax_id']):
                        # The tax line is affecting the base of a 'none' tax belonging to a group of taxes.
                        # In that case, the amount is accounted as an extra base for that group. However, we need to
                        # account it only once.
                        # For example, suppose a tax 10% affect base of subsequent followed by a group of taxes
                        # 20% + 30%. On a base of 1000.0, the tax line for 10% will affect the base of 20% + 30%.
                        # However, this extra base must be accounted only once since the base of the group of taxes
                        # must be 1100.0 and not 1200.0.
                        group_tax_id = child_to_group_of_taxes[row['tax_id']]
                        if group_tax_id not in group_of_taxes_with_extra_base_amount:
                            group_tax_info = group_of_taxes_info[group_tax_id]
                            results[group_tax_info['type_tax_use']]['children'][group_tax_id]['base_amount'][
                                column_group_key] += row['base_amount']
                            group_of_taxes_with_extra_base_amount.add(group_tax_id)
                    else:
                        tax_type_tax_use = row['src_group_tax_type_tax_use'] or row['src_tax_type_tax_use']
                        results[tax_type_tax_use]['children'][row['tax_id']]['base_amount'][column_group_key] += row[
                            'base_amount']
                else:
                    if row['tax_id'] in group_of_taxes_info and group_of_taxes_info[row['tax_id']]['to_expand']:
                        # Expand the group of taxes since it contains at least one tax with a type != 'none'.
                        group_info = group_of_taxes_info[row['tax_id']]
                        for child_tax_id in group_info['child_tax_ids']:
                            results[group_info['type_tax_use']]['children'][child_tax_id]['base_amount'][
                                column_group_key] += row['base_amount']
                    else:
                        results[row['tax_type_tax_use']]['children'][row['tax_id']]['base_amount'][column_group_key] += \
                        row['base_amount']

            # Fetch the tax amounts.
            if currency_dif == self.env.company.currency_id.symbol:
                self._cr.execute(f'''
                        SELECT
                            tax.id AS tax_id,
                            tax.type_tax_use AS tax_type_tax_use,
                            group_tax.id AS group_tax_id,
                            group_tax.type_tax_use AS group_tax_type_tax_use,
                            SUM(account_move_line.balance) AS tax_amount
                        FROM {tables}
                        JOIN account_tax tax ON tax.id = account_move_line.tax_line_id
                        LEFT JOIN account_tax group_tax ON group_tax.id = account_move_line.group_tax_id
                        WHERE {where_clause}
                            AND (
                                /* CABA */
                                account_move_line__move_id.always_tax_exigible
                                OR account_move_line__move_id.tax_cash_basis_rec_id IS NOT NULL
                                OR tax.tax_exigibility != 'on_payment'
                            )
                            AND (
                                (group_tax.id IS NULL AND tax.type_tax_use IN ('sale', 'purchase'))
                                OR
                                (group_tax.id IS NOT NULL AND group_tax.type_tax_use IN ('sale', 'purchase'))
                            )
                        GROUP BY tax.id, group_tax.id
                    ''', where_params)
            else:
                self._cr.execute(f'''
                                        SELECT
                                            tax.id AS tax_id,
                                            tax.type_tax_use AS tax_type_tax_use,
                                            group_tax.id AS group_tax_id,
                                            group_tax.type_tax_use AS group_tax_type_tax_use,
                                            SUM(account_move_line.balance_usd) AS tax_amount
                                        FROM {tables}
                                        JOIN account_tax tax ON tax.id = account_move_line.tax_line_id
                                        LEFT JOIN account_tax group_tax ON group_tax.id = account_move_line.group_tax_id
                                        WHERE {where_clause}
                                            AND (
                                                /* CABA */
                                                account_move_line__move_id.always_tax_exigible
                                                OR account_move_line__move_id.tax_cash_basis_rec_id IS NOT NULL
                                                OR tax.tax_exigibility != 'on_payment'
                                            )
                                            AND (
                                                (group_tax.id IS NULL AND tax.type_tax_use IN ('sale', 'purchase'))
                                                OR
                                                (group_tax.id IS NOT NULL AND group_tax.type_tax_use IN ('sale', 'purchase'))
                                            )
                                        GROUP BY tax.id, group_tax.id
                                    ''', where_params)

            for row in self._cr.dictfetchall():
                # Manage group of taxes.
                # In case the group of taxes is mixing multiple taxes having a type_tax_use != 'none', consider
                # them instead of the group.
                tax_id = row['tax_id']
                if row['group_tax_id']:
                    tax_type_tax_use = row['group_tax_type_tax_use']
                    if not group_of_taxes_info[row['group_tax_id']]['to_expand']:
                        tax_id = row['group_tax_id']
                else:
                    tax_type_tax_use = row['group_tax_type_tax_use'] or row['tax_type_tax_use']

                results[tax_type_tax_use]['tax_amount'][column_group_key] += row['tax_amount']
                results[tax_type_tax_use]['children'][tax_id]['tax_amount'][column_group_key] += row['tax_amount']

        return results

    @api.model
    def _compute_vat_closing_entry(self, company, options):
        """Compute the VAT closing entry.

        This method returns the one2many commands to balance the tax accounts for the selected period, and
        a dictionnary that will help balance the different accounts set per tax group.
        """
        self = self.with_company(company)  # Needed to handle access to property fields correctly
        currency_dif = options['currency_dif']
        # first, for each tax group, gather the tax entries per tax and account
        self.env['account.tax'].flush_model(['name', 'tax_group_id'])
        self.env['account.tax.repartition.line'].flush_model(['use_in_tax_closing'])
        self.env['account.move.line'].flush_model(
            ['account_id', 'debit', 'credit', 'move_id', 'tax_line_id', 'date', 'company_id', 'display_type'])
        self.env['account.move'].flush_model(['state'])

        # Check whether it is multilingual, in order to get the translation from the JSON value if present
        lang = self.env.user.lang or get_lang(self.env).code
        tax_name = f"COALESCE(tax.name->>'{lang}', tax.name->>'en_US')" if \
            self.pool['account.tax'].name.translate else 'tax.name'
        if currency_dif == self.env.company.currency_id.symbol:
            sql = f"""
                    SELECT "account_move_line".tax_line_id as tax_id,
                            tax.tax_group_id as tax_group_id,
                            {tax_name} as tax_name,
                            "account_move_line".account_id,
                            COALESCE(SUM("account_move_line".balance), 0) as amount
                    FROM account_tax tax, account_tax_repartition_line repartition, %s
                    WHERE %s
                      AND tax.id = "account_move_line".tax_line_id
                      AND repartition.id = "account_move_line".tax_repartition_line_id
                      AND repartition.use_in_tax_closing
                    GROUP BY tax.tax_group_id, "account_move_line".tax_line_id, tax.name, "account_move_line".account_id
                """
        else:
            sql = f"""
                                SELECT "account_move_line".tax_line_id as tax_id,
                                        tax.tax_group_id as tax_group_id,
                                        {tax_name} as tax_name,
                                        "account_move_line".account_id,
                                        COALESCE(SUM("account_move_line".balance_usd), 0) as amount
                                FROM account_tax tax, account_tax_repartition_line repartition, %s
                                WHERE %s
                                  AND tax.id = "account_move_line".tax_line_id
                                  AND repartition.id = "account_move_line".tax_repartition_line_id
                                  AND repartition.use_in_tax_closing
                                GROUP BY tax.tax_group_id, "account_move_line".tax_line_id, tax.name, "account_move_line".account_id
                            """

        new_options = {
            **options,
            'all_entries': False,
            'date': dict(options['date']),
            'multi_company': [{'id': company.id, 'name': company.name}],
        }

        period_start, period_end = company._get_tax_closing_period_boundaries(
            fields.Date.from_string(options['date']['date_to']))
        new_options['date']['date_from'] = fields.Date.to_string(period_start)
        new_options['date']['date_to'] = fields.Date.to_string(period_end)

        tables, where_clause, where_params = self.env.ref('account.generic_tax_report')._query_get(
            new_options,
            'strict_range',
            domain=self._get_vat_closing_entry_additional_domain()
        )
        query = sql % (tables, where_clause)
        self.env.cr.execute(query, where_params)
        results = self.env.cr.dictfetchall()

        tax_group_ids = [r['tax_group_id'] for r in results]
        tax_groups = {}
        for tg, result in zip(self.env['account.tax.group'].browse(tax_group_ids), results):
            if tg not in tax_groups:
                tax_groups[tg] = {}
            if result.get('tax_id') not in tax_groups[tg]:
                tax_groups[tg][result.get('tax_id')] = []
            tax_groups[tg][result.get('tax_id')].append(
                (result.get('tax_name'), result.get('account_id'), result.get('amount')))

        # then loop on previous results to
        #    * add the lines that will balance their sum per account
        #    * make the total per tax group's account triplet
        # (if 2 tax groups share the same 3 accounts, they should consolidate in the vat closing entry)
        move_vals_lines = []
        tax_group_subtotal = {}
        currency = self.env.company.currency_id
        for tg, values in tax_groups.items():
            total = 0
            # ignore line that have no property defined on tax group
            if not tg.property_tax_receivable_account_id or not tg.property_tax_payable_account_id:
                continue
            for dummy, value in values.items():
                for v in value:
                    tax_name, account_id, amt = v
                    # Line to balance
                    move_vals_lines.append((0, 0, {'name': tax_name, 'debit': abs(amt) if amt < 0 else 0,
                                                   'credit': amt if amt > 0 else 0, 'account_id': account_id}))
                    total += amt

            if not currency.is_zero(total):
                # Add total to correct group
                key = (tg.property_advance_tax_payment_account_id.id or False, tg.property_tax_receivable_account_id.id,
                       tg.property_tax_payable_account_id.id)

                if tax_group_subtotal.get(key):
                    tax_group_subtotal[key] += total
                else:
                    tax_group_subtotal[key] = total

        # If the tax report is completely empty, we add two 0-valued lines, using the first in in and out
        # account id we find on the taxes.
        if len(move_vals_lines) == 0:
            rep_ln_in = self.env['account.tax.repartition.line'].search([
                ('account_id.deprecated', '=', False),
                ('repartition_type', '=', 'tax'),
                ('company_id', '=', company.id),
                ('invoice_tax_id.type_tax_use', '=', 'purchase')
            ], limit=1)
            rep_ln_out = self.env['account.tax.repartition.line'].search([
                ('account_id.deprecated', '=', False),
                ('repartition_type', '=', 'tax'),
                ('company_id', '=', company.id),
                ('invoice_tax_id.type_tax_use', '=', 'sale')
            ], limit=1)

            if rep_ln_out.account_id and rep_ln_in.account_id:
                move_vals_lines = [
                    Command.create({
                        'name': _('Tax Received Adjustment'),
                        'debit': 0,
                        'credit': 0.0,
                        'account_id': rep_ln_out.account_id.id
                    }),

                    Command.create({
                        'name': _('Tax Paid Adjustment'),
                        'debit': 0.0,
                        'credit': 0,
                        'account_id': rep_ln_in.account_id.id
                    })
                ]

        return move_vals_lines, tax_group_subtotal

    @api.model
    def _add_tax_group_closing_items(self, tax_group_subtotal, end_date, options):
        """Transform the parameter tax_group_subtotal dictionnary into one2many commands.

        Used to balance the tax group accounts for the creation of the vat closing entry.
        """
        currency_dif = options['currency_dif']
        def _add_line(account, name, company_currency):
            self.env.cr.execute(sql_account, (account, end_date))
            result = self.env.cr.dictfetchone()
            advance_balance = result.get('balance') or 0
            # Deduct/Add advance payment
            if not company_currency.is_zero(advance_balance):
                line_ids_vals.append((0, 0, {
                    'name': name,
                    'debit': abs(advance_balance) if advance_balance < 0 else 0,
                    'credit': abs(advance_balance) if advance_balance > 0 else 0,
                    'account_id': account
                }))
            return advance_balance

        currency = self.env.company.currency_id
        if currency_dif == self.env.company.currency_id.symbol:
            sql_account = '''
                    SELECT SUM(aml.balance) AS balance
                    FROM account_move_line aml
                    LEFT JOIN account_move move ON move.id = aml.move_id
                    WHERE aml.account_id = %s
                      AND aml.date <= %s
                      AND move.state = 'posted'
                '''
        else:
            sql_account = '''
                            SELECT SUM(aml.balance_usd) AS balance
                            FROM account_move_line aml
                            LEFT JOIN account_move move ON move.id = aml.move_id
                            WHERE aml.account_id = %s
                              AND aml.date <= %s
                              AND move.state = 'posted'
                        '''
        line_ids_vals = []
        # keep track of already balanced account, as one can be used in several tax group
        account_already_balanced = []
        for key, value in tax_group_subtotal.items():
            total = value
            # Search if any advance payment done for that configuration
            if key[0] and key[0] not in account_already_balanced:
                total += _add_line(key[0], _('Balance tax advance payment account'), currency)
                account_already_balanced.append(key[0])
            if key[1] and key[1] not in account_already_balanced:
                total += _add_line(key[1], _('Balance tax current account (receivable)'), currency)
                account_already_balanced.append(key[1])
            if key[2] and key[2] not in account_already_balanced:
                total += _add_line(key[2], _('Balance tax current account (payable)'), currency)
                account_already_balanced.append(key[2])
            # Balance on the receivable/payable tax account
            if not currency.is_zero(total):
                line_ids_vals.append(Command.create({
                    'name': _('Payable tax amount') if total < 0 else _('Receivable tax amount'),
                    'debit': total if total > 0 else 0,
                    'credit': abs(total) if total < 0 else 0,
                    'account_id': key[2] if total < 0 else key[1]
                }))
        return line_ids_vals

    def _generate_tax_closing_entries(self, report, options, closing_moves=None, companies=None):
        """Generates and/or updates VAT closing entries.

        This method computes the content of the tax closing in the following way:
        - Search on all tax lines in the given period, group them by tax_group (each tax group might have its own
        tax receivable/payable account).
        - Create a move line that balances each tax account and add the difference in the correct receivable/payable
        account. Also take into account amounts already paid via advance tax payment account.

        The tax closing is done so that an individual move is created per available VAT number: so, one for each
        foreign vat fiscal position (each with fiscal_position_id set to this fiscal position), and one for the domestic
        position (with fiscal_position_id = None). The moves created by this function hence depends on the content of the
        options dictionary, and what fiscal positions are accepted by it.

        :param options: the tax report options dict to use to make the closing.
        :param closing_moves: If provided, closing moves to update the content from.
                              They need to be compatible with the provided options (if they have a fiscal_position_id, for example).
        :param companies: optional params, the companies given will be used instead of taking all the companies impacting
                          the report.
        :return: The closing moves.
        """
        if companies is None:
            options_company_ids = [company_opt['id'] for company_opt in options.get('multi_company', [])]
            companies = self.env['res.company'].browse(options_company_ids) if options_company_ids else self.env.company
        end_date = fields.Date.from_string(options['date']['date_to'])

        closing_moves_by_company = defaultdict(lambda: self.env['account.move'])
        if closing_moves:
            for move in closing_moves.filtered(lambda x: x.state == 'draft'):
                closing_moves_by_company[move.company_id] |= move
        else:
            closing_moves = self.env['account.move']
            for company in companies:
                include_domestic, fiscal_positions = self._get_fpos_info_for_tax_closing(company, report, options)
                company_closing_moves = company._get_and_update_tax_closing_moves(end_date, fiscal_positions=fiscal_positions, include_domestic=include_domestic)
                closing_moves_by_company[company] = company_closing_moves
                closing_moves += company_closing_moves

        for company, company_closing_moves in closing_moves_by_company.items():

            # First gather the countries for which the closing is being done
            countries = self.env['res.country']
            for move in company_closing_moves:
                if move.fiscal_position_id.foreign_vat:
                    countries |= move.fiscal_position_id.country_id
                else:
                    countries |= company.account_fiscal_country_id

            # Check the tax groups from the company for any misconfiguration in these countries
            if self.env['account.tax.group']._check_misconfigured_tax_groups(company, countries):
                self._redirect_to_misconfigured_tax_groups(company, countries)

            if company.tax_lock_date and company.tax_lock_date >= end_date:
                raise UserError(_("This period is already closed for company %s", company.name))

            for move in company_closing_moves:
                # get tax entries by tax_group for the period defined in options
                move_options = {**options, 'fiscal_position': move.fiscal_position_id.id if move.fiscal_position_id else 'domestic'}
                line_ids_vals, tax_group_subtotal = self._compute_vat_closing_entry(company, move_options)

                line_ids_vals += self._add_tax_group_closing_items(tax_group_subtotal, end_date, options)

                if move.line_ids:
                    line_ids_vals += [Command.delete(aml.id) for aml in move.line_ids]

                move_vals = {}
                if line_ids_vals:
                    move_vals['line_ids'] = line_ids_vals

                move_vals['tax_report_control_error'] = bool(move_options.get('tax_report_control_error'))

                move.write(move_vals)

        return closing_moves