# -*- coding: utf-8 -*-

from collections import defaultdict

from odoo import _, api, exceptions, fields, models
from odoo.tools import formatLang

VAT_DEFAULT = 'XXXXX'


class AccountTax(models.Model):
    _inherit = "account.tax"

    withholding_type = fields.Selection(
        selection=[
            ("iva", "VAT withholding"),
            ("islr", "ISLR withholding"),
        ],
        string="Type retention"
    )

    @api.model
    def _prepare_tax_totals(self, base_lines, currency, tax_lines=None):
        """ Compute the tax totals details for the business documents.
        :param base_lines:  A list of python dictionaries created using the '_convert_to_tax_base_line_dict' method.
        :param currency:    The currency set on the business document.
        :param tax_lines:   Optional list of python dictionaries created using the '_convert_to_tax_line_dict' method.
                            If specified, the taxes will be recomputed using them instead of recomputing the taxes on
                            the provided base lines.
        :return: A dictionary in the following form:
            {
                'amount_total':                 The total amount to be displayed on the document, including every total
                                                types.
                'amount_untaxed':               The untaxed amount to be displayed on the document.
                'formatted_amount_total':       Same as amount_total, but as a string formatted accordingly with
                                                partner's locale.
                'formatted_amount_untaxed':     Same as amount_untaxed, but as a string formatted accordingly with
                                                partner's locale.
                'groups_by_subtotals':          A dictionary formed liked {'subtotal': groups_data}
                                                Where total_type is a subtotal name defined on a tax group, or the
                                                default one: 'Untaxed Amount'.
                                                And groups_data is a list of dict in the following form:
                    {
                        'tax_group_name':                   The name of the tax groups this total is made for.
                        'tax_group_amount':                 The total tax amount in this tax group.
                        'tax_group_base_amount':            The base amount for this tax group.
                        'formatted_tax_group_amount':       Same as tax_group_amount, but as a string formatted accordingly
                                                            with partner's locale.
                        'formatted_tax_group_base_amount':  Same as tax_group_base_amount, but as a string formatted
                                                            accordingly with partner's locale.
                        'tax_group_id':                     The id of the tax group corresponding to this dict.
                    }
                'subtotals':                    A list of dictionaries in the following form, one for each subtotal in
                                                'groups_by_subtotals' keys.
                    {
                        'name':                             The name of the subtotal
                        'amount':                           The total amount for this subtotal, summing all the tax groups
                                                            belonging to preceding subtotals and the base amount
                        'formatted_amount':                 Same as amount, but as a string formatted accordingly with
                                                            partner's locale.
                    }
                'subtotals_order':              A list of keys of `groups_by_subtotals` defining the order in which it needs
                                                to be displayed
            }
        """

        # ==== Compute the taxes ====
        in_move = self._context.get('default_move_type', False)

        for item in base_lines:
            if 'record' in item and 'account.move.line' in str(item['record']):
                in_move = True

        to_process = []
        for base_line in base_lines:
            to_update_vals, tax_values_list = self._compute_taxes_for_single_line(base_line)
            to_process.append((base_line, to_update_vals, tax_values_list))

        def grouping_key_generator(base_line, tax_values):
            source_tax = tax_values['tax_repartition_line'].tax_id
            return {'tax_group': source_tax.tax_group_id}

        global_tax_details = self._aggregate_taxes(to_process, grouping_key_generator=grouping_key_generator)

        tax_group_vals_list = []
        for tax_detail in global_tax_details['tax_details'].values():
            tax_group_vals = {
                'tax_group': tax_detail['tax_group'],
                'base_amount': tax_detail['base_amount_currency'],
                'tax_amount': tax_detail['tax_amount_currency'],
            }

            # Handle a manual edition of tax lines.
            if tax_lines is not None:
                matched_tax_lines = [
                    x
                    for x in tax_lines
                    if x['tax_repartition_line'].tax_id.tax_group_id == tax_detail['tax_group']
                ]
                if matched_tax_lines:
                    tax_group_vals['tax_amount'] = sum(x['tax_amount'] for x in matched_tax_lines)

            tax_group_vals_list.append(tax_group_vals)

        if in_move != False:
            move_id = ''
            base_amount = 0
            for base in base_lines:
                move_id = base['record'].move_id

                for record in base['record']:
                    base_amount += record.price_unit

            if move_id and move_id.invoice_tax_id:
                new_tax_group_vals = {
                    'tax_group': move_id.invoice_tax_id.tax_group_id,
                    'base_amount': base_amount,
                    'tax_amount': move_id.invoice_tax_id.amount,
                }

                if not any(obj['tax_group'] == new_tax_group_vals['tax_group'] for obj in tax_group_vals_list):
                    tax_group_vals_list.append(new_tax_group_vals)

        tax_group_vals_list = sorted(tax_group_vals_list, key=lambda x: (x['tax_group'].sequence, x['tax_group'].id))

        # ==== Partition the tax group values by subtotals ====

        amount_untaxed = global_tax_details['base_amount_currency']
        amount_tax = 0.0
        withholding_islr_base = 0.0
        withholding_islr = 0.0
        withholding_iva = 0.0
        subtotal_order = {}
        groups_by_subtotal = defaultdict(list)

        for tax_group_vals in tax_group_vals_list:
            tax_group = tax_group_vals['tax_group']
            # print(tax_group)

            subtotal_title = tax_group.preceding_subtotal or _("Untaxed Amount")
            sequence = tax_group.sequence

            subtotal_order[subtotal_title] = min(subtotal_order.get(subtotal_title, float('inf')), sequence)

            if in_move != False:

                move_iva_records = self.env['account.tax'].search([('withholding_type', '=', 'iva'), ('tax_group_id', '=', tax_group.id), ('type_tax_use', '=', 'purchase')])
                move_islr_records = self.env['account.tax'].search([('withholding_type', '=', 'islr'), ('tax_group_id', '=', tax_group.id), ('type_tax_use', '=', 'purchase')])

                if move_iva_records and move_islr_records:
                    iva_amounts = []
                    islr_amounts = []
                    has_islr = False

                    for base in base_lines:
                        for l in base['record']:
                            # Acceder a la información de impuestos
                            for tax_id in l.tax_ids:
                                if tax_id.withholding_type == 'islr':
                                    has_islr = True
                                    continue

                    for base in base_lines:
                        for l in base['record']:
                            # Acceder a la información de impuestos
                            for tax_id in l.tax_ids:
                                name = tax_id.name
                                amount = l.price_unit * tax_id.amount / 100

                                # print(l.price_unit, l.move_id.invoice_tax_id.amount, tax_id.amount)
                                if ('IVA' in name or 'iva' in name) and move_id.invoice_tax_id:
                                    amount_currency = (amount * l.move_id.invoice_tax_id.amount / 100) * l.quantity
                                    withholding_iva += amount_currency
                                    iva_amounts.append(amount_currency)
                                if tax_id.withholding_type == 'islr':
                                    amount_currency = amount * l.quantity
                                    islr_amounts.append(amount_currency)

                    withholding_islr = sum(islr_amounts) + move_id.subtracting
                    withholding_islr_base = sum(islr_amounts)
                    total_tax_amount = sum(iva_amounts) + withholding_islr

                    if has_islr == False:
                        if move_id.id:
                            line_invoice_tax = self.env['account.move.line'].search([('move_id', '=', move_id.id), ('tax_line_id', '=', move_id.invoice_tax_id.id)])
                            rep_line = self.env['account.tax.repartition.line'].search([('invoice_tax_id', '=', move_id.invoice_tax_id.id), ('account_id', '!=', False)], limit=1)
                            total_amount_currency = move_id.currency_id._convert(total_tax_amount, move_id.company_currency_id, move_id.company_id, move_id.date)

                            if line_invoice_tax:
                                line_invoice_tax.write({
                                    'move_id': move_id.id,
                                    'tax_line_id': move_id.invoice_tax_id.id,
                                    'credit': total_amount_currency if total_amount_currency > 0 else total_amount_currency * -1,
                                    'balance': total_amount_currency,
                                    'amount_currency': total_tax_amount,
                                    'tax_base_amount': tax_group_vals['base_amount'],
                                    'display_type': 'tax',
                                    'name': move_id.invoice_tax_id.name,
                                    'move_name': move_id.name,
                                    'currency_id': move_id.currency_id.id,
                                    'sequence': 10000,
                                    'account_id': rep_line.account_id.id,
                                    'tax_group_id': move_id.invoice_tax_id.tax_group_id.id,
                                    'tax_repartition_line_id': rep_line.id,
                                })
                            else:
                                self.env['account.move.line'].create({
                                    'move_id': move_id.id,
                                    'tax_line_id': move_id.invoice_tax_id.id,
                                    'credit': total_amount_currency if total_amount_currency > 0 else total_amount_currency * -1,
                                    'balance': total_amount_currency,
                                    'amount_currency': total_tax_amount,
                                    'tax_base_amount': tax_group_vals['base_amount'],
                                    'display_type': 'tax',
                                    'name': move_id.invoice_tax_id.name,
                                    'move_name': move_id.name,
                                    'currency_id': move_id.currency_id.id,
                                    'sequence': 10000,
                                    'account_id': rep_line.account_id.id,
                                    'tax_group_id': move_id.invoice_tax_id.tax_group_id.id,
                                    'tax_repartition_line_id': rep_line.id,
                                })

                    groups_by_subtotal[subtotal_title].append({
                        'group_key': tax_group.id,
                        'tax_group_id': tax_group.id,
                        'tax_group_name': tax_group.name,
                        'tax_group_amount': total_tax_amount,
                        'tax_group_base_amount': tax_group_vals['base_amount'],
                        'formatted_tax_group_amount': formatLang(self.env, total_tax_amount, currency_obj=currency),
                        'formatted_tax_group_base_amount': formatLang(self.env, tax_group_vals['base_amount'], currency_obj=currency),
                    })
                elif move_iva_records and not move_islr_records:
                    iva_amounts = []

                    for base in base_lines:
                        for l in base['record']:
                            # Acceder a la información de impuestos
                            for tax_id in l.tax_ids:
                                name = tax_id.name
                                amount = l.price_unit * tax_id.amount / 100

                                if ('IVA' in name or 'iva' in name) and move_id.invoice_tax_id:
                                    amount_currency = (amount * l.move_id.invoice_tax_id.amount / 100) * l.quantity
                                    withholding_iva += amount_currency
                                    iva_amounts.append(amount_currency)

                    total_tax_amount = sum(iva_amounts)
                    line_invoice_tax = self.env['account.move.line'].search([('move_id', '=', move_id.id), ('tax_line_id', '=', move_id.invoice_tax_id.id)])
                    rep_line = self.env['account.tax.repartition.line'].search([('invoice_tax_id', '=', move_id.invoice_tax_id.id), ('account_id', '!=', False)], limit=1)

                    if move_id.id:
                        total_amount_currency = move_id.currency_id._convert(total_tax_amount, move_id.company_currency_id, move_id.company_id, move_id.date)

                        if line_invoice_tax:
                            line_invoice_tax.write({
                                'move_id': move_id.id,
                                'tax_line_id': move_id.invoice_tax_id.id,
                                'credit': total_amount_currency if total_amount_currency > 0 else total_amount_currency * -1,
                                'balance': total_amount_currency,
                                'amount_currency': total_tax_amount,
                                'tax_base_amount': tax_group_vals['base_amount'],
                                'display_type': 'tax',
                                'name': move_id.invoice_tax_id.name,
                                'move_name': move_id.name,
                                'currency_id': move_id.currency_id.id,
                                'sequence': 10000,
                                'account_id': rep_line.account_id.id,
                                'tax_group_id': move_id.invoice_tax_id.tax_group_id.id,
                                'tax_repartition_line_id': rep_line.id,
                            })
                        else:
                            self.env['account.move.line'].create({
                                'move_id': move_id.id,
                                'tax_line_id': move_id.invoice_tax_id.id,
                                'credit': total_amount_currency if total_amount_currency > 0 else total_amount_currency * -1,
                                'balance': total_amount_currency,
                                'amount_currency': total_tax_amount,
                                'tax_base_amount': tax_group_vals['base_amount'],
                                'display_type': 'tax',
                                'name': move_id.invoice_tax_id.name,
                                'move_name': move_id.name,
                                'currency_id': move_id.currency_id.id,
                                'sequence': 10000,
                                'account_id': rep_line.account_id.id,
                                'tax_group_id': move_id.invoice_tax_id.tax_group_id.id,
                                'tax_repartition_line_id': rep_line.id,
                            })

                    groups_by_subtotal[subtotal_title].append({
                        'group_key': tax_group.id,
                        'tax_group_id': tax_group.id,
                        'tax_group_name': tax_group.name,
                        'tax_group_amount': total_tax_amount,
                        'tax_group_base_amount': tax_group_vals['base_amount'],
                        'formatted_tax_group_amount': formatLang(self.env, total_tax_amount, currency_obj=currency),
                        'formatted_tax_group_base_amount': formatLang(self.env, tax_group_vals['base_amount'], currency_obj=currency),
                    })
                elif move_islr_records and not move_iva_records:
                    islr_amounts = []

                    for base in base_lines:
                        for l in base['record']:
                            # Acceder a la información de impuestos
                            for tax_id in l.tax_ids:
                                name = tax_id.name
                                amount = l.price_unit * tax_id.amount / 100

                                if tax_id.withholding_type == 'islr':
                                    amount_currency = amount * l.quantity
                                    islr_amounts.append(amount_currency)

                    withholding_islr = sum(islr_amounts) + move_id.subtracting
                    withholding_islr_base = sum(islr_amounts)
                    total_tax_amount = withholding_islr

                    groups_by_subtotal[subtotal_title].append({
                        'group_key': tax_group.id,
                        'tax_group_id': tax_group.id,
                        'tax_group_name': tax_group.name,
                        'tax_group_amount': total_tax_amount,
                        'tax_group_base_amount': tax_group_vals['base_amount'],
                        'formatted_tax_group_amount': formatLang(self.env, total_tax_amount, currency_obj=currency),
                        'formatted_tax_group_base_amount': formatLang(self.env, tax_group_vals['base_amount'], currency_obj=currency),
                    })
                else:
                    groups_by_subtotal[subtotal_title].append({
                        'group_key': tax_group.id,
                        'tax_group_id': tax_group.id,
                        'tax_group_name': tax_group.name,
                        'tax_group_amount': tax_group_vals['tax_amount'],
                        'tax_group_base_amount': tax_group_vals['base_amount'],
                        'formatted_tax_group_amount': formatLang(self.env, tax_group_vals['tax_amount'], currency_obj=currency),
                        'formatted_tax_group_base_amount': formatLang(self.env, tax_group_vals['base_amount'], currency_obj=currency),
                    })
            else:
                groups_by_subtotal[subtotal_title].append({
                    'group_key': tax_group.id,
                    'tax_group_id': tax_group.id,
                    'tax_group_name': tax_group.name,
                    'tax_group_amount': tax_group_vals['tax_amount'],
                    'tax_group_base_amount': tax_group_vals['base_amount'],
                    'formatted_tax_group_amount': formatLang(self.env, tax_group_vals['tax_amount'], currency_obj=currency),
                    'formatted_tax_group_base_amount': formatLang(self.env, tax_group_vals['base_amount'], currency_obj=currency),
                })

        # ==== Build the final result ====

        subtotals = []
        for subtotal_title in sorted(subtotal_order.keys(), key=lambda k: subtotal_order[k]):
            amount_total = amount_untaxed + amount_tax
            subtotals.append({
                'name': subtotal_title,
                'amount': amount_total,
                'formatted_amount': formatLang(self.env, amount_total, currency_obj=currency),
            })
            amount_tax += sum(x['tax_group_amount'] for x in groups_by_subtotal[subtotal_title])

        amount_total = amount_untaxed + amount_tax

        display_tax_base = (len(global_tax_details['tax_details']) == 1 and currency.compare_amounts(tax_group_vals_list[0]['base_amount'], amount_untaxed) != 0)\
            or len(global_tax_details['tax_details']) > 1

        if in_move != False:
            if move_id:
                # Asignar nuevos valores a los campos de la factura
                move_id.withholding_islr_base = withholding_islr_base
                move_id.withholding_islr = withholding_islr
                move_id.withholding_iva = withholding_iva

        return {
            'amount_untaxed': currency.round(amount_untaxed) if currency else amount_untaxed,
            'amount_total': currency.round(amount_total) if currency else amount_total,
            'formatted_amount_total': formatLang(self.env, amount_total, currency_obj=currency),
            'formatted_amount_untaxed': formatLang(self.env, amount_untaxed, currency_obj=currency),
            'groups_by_subtotal': groups_by_subtotal,
            'subtotals': subtotals,
            'subtotals_order': sorted(subtotal_order.keys(), key=lambda k: subtotal_order[k]),
            'display_tax_base': display_tax_base
        }
