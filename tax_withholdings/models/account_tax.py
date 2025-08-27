# -*- coding: utf-8 -*-

from collections import defaultdict

from odoo import _, api, fields, models
from odoo.tools import formatLang

VAT_DEFAULT = 'XXXXX'


class AccountTax(models.Model):
    _inherit = "account.tax"

    withholding_type = fields.Selection(
        selection=[
            ("iva", "VAT withholding"),
        ],
        string="Type retention"
    )

    @api.model
    def _prepare_tax_totals(self, base_lines, currency, tax_lines=None):
        """Compute the tax totals details for business documents (only VAT logic)."""

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

        global_tax_details = self._aggregate_taxes(
            to_process, grouping_key_generator=grouping_key_generator
        )

        tax_group_vals_list = []
        for tax_detail in global_tax_details['tax_details'].values():
            tax_group_vals = {
                'tax_group': tax_detail['tax_group'],
                'base_amount': tax_detail['base_amount_currency'],
                'tax_amount': tax_detail['tax_amount_currency'],
            }

            # Handle manual edition of tax lines.
            if tax_lines is not None:
                matched_tax_lines = [
                    x
                    for x in tax_lines
                    if x['tax_repartition_line'].tax_id.tax_group_id == tax_detail['tax_group']
                ]
                if matched_tax_lines:
                    tax_group_vals['tax_amount'] = sum(x['tax_amount'] for x in matched_tax_lines)

            tax_group_vals_list.append(tax_group_vals)

        if in_move:
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

        tax_group_vals_list = sorted(
            tax_group_vals_list,
            key=lambda x: (x['tax_group'].sequence, x['tax_group'].id)
        )

        # ==== Partition the tax group values by subtotals ====
        amount_untaxed = global_tax_details['base_amount_currency']
        amount_tax = 0.0
        withholding_iva = 0.0
        subtotal_order = {}
        groups_by_subtotal = defaultdict(list)

        for tax_group_vals in tax_group_vals_list:
            tax_group = tax_group_vals['tax_group']
            subtotal_title = tax_group.preceding_subtotal or _("Untaxed Amount")
            sequence = tax_group.sequence

            subtotal_order[subtotal_title] = min(
                subtotal_order.get(subtotal_title, float('inf')), sequence
            )

            if in_move and move_id and move_id.invoice_tax_id:
                iva_amounts = []
                for base in base_lines:
                    for l in base['record']:
                        for tax_id in l.tax_ids:
                            name = tax_id.name
                            amount = l.price_unit * tax_id.amount / 100
                            if ('IVA' in name or 'iva' in name) and move_id.invoice_tax_id:
                                amount_currency = (
                                    (amount * l.move_id.invoice_tax_id.amount / 100) * l.quantity
                                )
                                withholding_iva += amount_currency
                                iva_amounts.append(amount_currency)

                total_tax_amount = sum(iva_amounts)

                rep_line = self.env['account.tax.repartition.line'].search([
                    ('invoice_tax_id', '=', move_id.invoice_tax_id.id),
                    ('account_id', '!=', False)
                ], limit=1)

                if move_id.id:
                    total_amount_currency = move_id.currency_id._convert(
                        total_tax_amount,
                        move_id.company_currency_id,
                        move_id.company_id,
                        move_id.date
                    )

                    line_invoice_tax = self.env['account.move.line'].search([
                        ('move_id', '=', move_id.id),
                        ('tax_line_id', '=', move_id.invoice_tax_id.id)
                    ])

                    vals = {
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
                        'account_id': rep_line.account_id.id if rep_line else False,
                        'tax_group_id': move_id.invoice_tax_id.tax_group_id.id,
                        'tax_repartition_line_id': rep_line.id if rep_line else False,
                    }

                    if line_invoice_tax:
                        line_invoice_tax.write(vals)
                    else:
                        self.env['account.move.line'].create(vals)

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

        if in_move and move_id:
            move_id.withholding_iva = withholding_iva

        return {
            'amount_untaxed': currency.round(amount_untaxed) if currency else amount_untaxed,
            'amount_total': currency.round(amount_total) if currency else amount_total,
            'formatted_amount_total': formatLang(self.env, amount_total, currency_obj=currency),
            'formatted_amount_untaxed': formatLang(self.env, amount_untaxed, currency_obj=currency),
            'groups_by_subtotal': groups_by_subtotal,
            'subtotals': subtotals,
            'subtotals_order': sorted(subtotal_order.keys(), key=lambda k: subtotal_order[k]),
            'display_tax_base': (
                (len(global_tax_details['tax_details']) == 1 and
                 currency.compare_amounts(tax_group_vals_list[0]['base_amount'], amount_untaxed) != 0)
                or len(global_tax_details['tax_details']) > 1
            )
        }
