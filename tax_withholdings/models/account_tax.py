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
            tax_group_vals_list.append(tax_group_vals)

        if in_move:
            move_id = ''
            for base in base_lines:
                move_id = base['record'].move_id

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

            # IVA normal → positivo
            groups_by_subtotal[subtotal_title].append({
                'group_key': f"{tax_group.id}_iva",
                'tax_group_id': tax_group.id,
                'tax_group_name': f"{tax_group.name} (IVA)",
                'tax_group_amount': tax_group_vals['tax_amount'],
                'tax_group_base_amount': tax_group_vals['base_amount'],
                'formatted_tax_group_amount': formatLang(self.env, tax_group_vals['tax_amount'], currency_obj=currency),
                'formatted_tax_group_base_amount': formatLang(self.env, tax_group_vals['base_amount'], currency_obj=currency),
            })

            # Retención IVA → negativo
            if in_move and move_id and move_id.invoice_tax_id:
                if 'iva' in tax_group.name.lower():
                    withholding_iva = -abs(tax_group_vals['tax_amount'])

                    groups_by_subtotal[subtotal_title].append({
                        'group_key': f"{tax_group.id}_ret_iva",
                        'tax_group_id': tax_group.id,
                        'tax_group_name': f"{tax_group.name} (Retención IVA)",
                        'tax_group_amount': withholding_iva,
                        'tax_group_base_amount': tax_group_vals['base_amount'],
                        'formatted_tax_group_amount': formatLang(self.env, withholding_iva, currency_obj=currency),
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
            # ⚡ Retención siempre negativa
            move_id.withholding_iva = -abs(withholding_iva)

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
