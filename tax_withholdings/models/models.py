# -*- coding: utf-8 -*-

from odoo import _, api, exceptions, fields, models
from odoo.tools import frozendict, formatLang
from collections import defaultdict
import json

VAT_DEFAULT = 'XXXXX'


class AccountTax(models.Model):
    _inherit = "account.tax"

    withholding_type = fields.Selection(
        selection=[
            ("iva", "Retención sobre IVA"),
            ("islr", "Retención sobre ISLR"),
        ],
        string="Retención de tipo"
    )

class AccountMoveWithHoldings(models.Model):
    _inherit = "account.move"

    invoice_tax_id = fields.Many2one(
        comodel_name='account.tax',
        string="Retención al IVA",
        domain=[
            ("withholding_type", "=", "iva"),
            ("type_tax_use", "=", "purchase"),
            ("active", "=", True)
        ],
        required=False,
    )
    withholding_iva = fields.Monetary(
        string='Retención del IVA ',
        store=True,
        compute='_compute_withholding',
        currency_field='company_currency_id'
    )
    withholding_islr = fields.Monetary(
        string='Retención del ISLR ',
        store=True,
        compute='_compute_withholding',
        currency_field='company_currency_id'
    )
    withholding_islr_base = fields.Monetary(
        string='Retención base del ISLR',
        store=True,
        compute='_compute_withholding',
        currency_field='company_currency_id'
    )
    sequence_withholding_iva = fields.Char(
        string="Secuencia de la retención del IVA",
        compute="_compute_secuence_withholding",
        store=True,
        copy=False
    )
    sequence_withholding_islr = fields.Char(
        string="Secuencia de la retención del ISLR",
        compute="_compute_secuence_withholding",
        store=True,
        copy=False
    )
    reference_number = fields.Char(
        string="Número de factura",
        copy=False
    )
    invoice_control_number = fields.Char(
        string="Número de control de factura",
        copy=False
    )
    subtracting = fields.Monetary(
        string='Sustraendo',
        default=0.0,
        currency_field='company_currency_id'
    )

    # Fields to export
    withholding_agent_vat = fields.Char(
        string="RIF del Agente de Retención",
        compute="_compute_fields_to_export",
        store=False,
        copy=False,
        readonly=True
    )
    retained_subject_vat = fields.Char(
        string="RIF del Sujeto Retenido",
        compute="_compute_fields_to_export",
        store=False,
        copy=False,
        readonly=True
    )
    withholding_number = fields.Char(
        string="Número de retención",
        compute="_compute_fields_to_export",
        store=False,
        copy=False,
        readonly=True
    )
    aliquot_iva = fields.Float(
        string="Alícuota del IVA",
        compute="_compute_fields_to_export",
        store=False,
        copy=False,
        readonly=True
    )
    withholding_percentage_islr = fields.Float(
        string="Porcentaje de retención",
        compute="_compute_fields_to_export",
        store=False,
        copy=False,
        readonly=True
    )
    amount_tax_iva = fields.Monetary(
        string="Total de impuestos (IVA)",
        compute="_compute_fields_to_export",
        store=False,
        copy=False,
        readonly=True,
        currency_field='company_currency_id'
    )
    amount_tax_islr = fields.Monetary(
        string="Total de impuestos (ISLR)",
        compute="_compute_fields_to_export",
        store=False,
        copy=False,
        readonly=True,
        currency_field='company_currency_id'
    )
    amount_total_iva = fields.Monetary(
        string="Total menos retenciones IVA",
        compute="_compute_fields_to_export",
        store=False,
        copy=False,
        readonly=True,
        currency_field='company_currency_id'
    )
    vat_exempt_amount_iva = fields.Monetary(
        string="Monto exento de IVA",
        compute="_compute_fields_to_export",
        store=False,
        copy=False,
        readonly=True,
        currency_field='company_currency_id'
    )
    vat_exempt_amount_islr = fields.Monetary(
        string="Monto exento de ISLR",
        compute="_compute_fields_to_export",
        store=False,
        copy=False,
        readonly=True,
        currency_field='company_currency_id'
    )
    amount_total_islr = fields.Monetary(
        string="Total menos retenciones ISLR",
        compute="_compute_fields_to_export",
        store=False,
        copy=False,
        readonly=True,
        currency_field='company_currency_id'
    )
    amount_total_purchase = fields.Monetary(
        string="Total de la compra",
        compute="_compute_fields_to_export",
        store=False,
        copy=False,
        readonly=True,
        currency_field='company_currency_id'
    )
    withholding_opp_iva = fields.Monetary(
        string='Retención del IVA',
        compute="_compute_fields_to_export",
        store=False,
        copy=False,
        readonly=True,
        currency_field='company_currency_id'
    )
    withholding_opp_islr = fields.Monetary(
        string='Total retenido',
        compute="_compute_fields_to_export",
        store=False,
        copy=False,
        readonly=True,
        currency_field='company_currency_id'
    )
    total_withheld = fields.Monetary(
        string='Retención del ISLR',
        compute="_compute_fields_to_export",
        store=False,
        copy=False,
        readonly=True,
        currency_field='company_currency_id'
    )
    tsc_tax_withholding_date = fields.Date(
        string='Fecha de retención de impuestos',
        help='Fecha en la que se realizan las retenciones de impuestos asociados a la factura. Para efectos del comprobante de retención corresponde a la fecha de emisión.',
        required=False,
        index=True,
        store=True,
        readonly=False,
        states={'draft': [('readonly', False)]},
        copy=True,
        tracking=True,
        default=fields.Date.context_today
    )

    @api.depends('invoice_tax_id', 'amount_tax', 'line_ids.tax_line_id')
    def _compute_withholding(self):
        for move in self:
            amount_total_withholding_iva = 0.0
            amount_total_withholding_islr = 0.0

            if move.is_invoice(True):
                for line in move.line_ids:
                    if line.tax_line_id:
                        if line.tax_line_id.withholding_type == "iva":
                            amount_total_withholding_iva += line.amount_currency
                        elif line.tax_line_id.withholding_type == "islr":
                            amount_total_withholding_islr += line.amount_currency

            move.withholding_iva = amount_total_withholding_iva
            move.withholding_islr_base = amount_total_withholding_islr - move.subtracting
            move.withholding_islr = amount_total_withholding_islr

    @api.depends("state", "withholding_iva", "withholding_islr")
    def _compute_secuence_withholding(self):
        for move in self:
            if move.state == "posted":
                if ((move.withholding_iva or 0.0) < 0.0) and not move.sequence_withholding_iva:
                    move.sequence_withholding_iva = self.env["ir.sequence"].next_by_code(
                        "account.move.withholding.iva")
                if ((move.withholding_islr or 0.0) < 0.0) and not move.sequence_withholding_islr:
                    move.sequence_withholding_islr = self.env["ir.sequence"].next_by_code(
                        "account.move.withholding.islr")

    @api.depends(
        "invoice_tax_id",
        "subtracting",
        "sequence_withholding_iva",
        "sequence_withholding_islr",
        "withholding_iva",
        "withholding_islr"
    )
    def _compute_fields_to_export(self):
        self.withholding_agent_vat = (
            self.env.company.company_registry.upper()
            if self.env.company.company_registry
            else VAT_DEFAULT
        )

        for move in self:
            sign = -1
            move.withholding_opp_iva = withholding_iva = sign * \
                (move.withholding_iva or 0.0)
            move.withholding_opp_islr = withholding_islr = sign * \
                (move.withholding_islr or 0.0)

            move.retained_subject_vat = (
                move.partner_id.vat.upper()
                if move.partner_id.vat
                else VAT_DEFAULT
            )

            if move.move_type in {'in_invoice', 'in_refund', 'in_receipt'} and (
                withholding_iva != 0.0 or withholding_islr != 0.0
            ):
                move.amount_total_purchase = move.amount_total + \
                    withholding_iva + withholding_islr

                if withholding_iva != 0.0:
                    date = move.date or move.invoice_date
                    move.withholding_number = f"{date:%Y%m}{move.sequence_withholding_iva:>08}"
                    move.amount_tax_iva = move.amount_tax + withholding_iva + withholding_islr
                    move.amount_total_iva = move.amount_total + withholding_islr

                    aliquot_iva = 0.0
                    vat_exempt_amount = 0.0

                    for line in move.line_ids:
                        if (
                            not line.tax_repartition_line_id
                            and line.display_type == 'product'
                            and (
                                not line.tax_ids or not any(
                                    tax.amount != 0.0 for tax in line.tax_ids
                                    if not tax.withholding_type
                                )
                            )
                        ):
                            vat_exempt_amount += line.amount_currency
                        elif (
                            aliquot_iva == 0.0
                            and line.tax_line_id
                            and line.tax_line_id.withholding_type == False
                            and line.tax_line_id.amount != 0.0
                        ):
                            aliquot_iva = line.tax_line_id.amount

                    move.aliquot_iva = aliquot_iva
                    move.vat_exempt_amount_iva = vat_exempt_amount

                else:
                    move.withholding_number = "0"
                    move.aliquot_iva = 0
                    move.amount_tax_iva = 0
                    move.amount_total_iva = 0
                    move.vat_exempt_amount_iva = 0

                if withholding_islr != 0.0:
                    move.total_withheld = sign*move.withholding_islr_base
                    move.amount_tax_islr = move.amount_tax + move.total_withheld
                    move.amount_total_islr = move.amount_total + withholding_iva

                    withholding_percentage_islr = 0.0
                    vat_exempt_amount = 0.0

                    for line in move.line_ids:
                        if (
                            not line.tax_repartition_line_id
                            and line.display_type == 'product'
                            and (
                                not line.tax_ids or not any(
                                    tax.amount != 0.0 for tax in line.tax_ids
                                    if tax.withholding_type == "islr"
                                )
                            )
                        ):
                            vat_exempt_amount += line.amount_currency
                        elif (
                            withholding_percentage_islr == 0.0
                            and line.tax_line_id
                            and line.tax_line_id.withholding_type == "islr"
                            and line.tax_line_id.amount != 0.0
                        ):
                            withholding_percentage_islr = line.tax_line_id.amount

                    move.vat_exempt_amount_islr = vat_exempt_amount
                    move.withholding_percentage_islr = sign*withholding_percentage_islr

                else:
                    move.amount_tax_islr = 0
                    move.amount_total_islr = 0
                    move.withholding_percentage_islr = 0
                    move.vat_exempt_amount_islr = 0
                    move.total_withheld = 0

            else:
                move.amount_total_purchase = 0
                move.withholding_number = "0"
                move.aliquot_iva = 0
                move.amount_tax_iva = 0
                move.amount_total_iva = 0
                move.amount_tax_islr = 0
                move.amount_total_islr = 0
                move.withholding_percentage_islr = 0
                move.vat_exempt_amount_iva = 0
                move.total_withheld = 0

    @api.onchange("invoice_tax_id")
    def _onchange_invoice_tax(self):
        super()._compute_tax_totals()

    def validate_subtracting(self, move=None):
        move = move or self
        if abs(move.subtracting) > abs(move.withholding_islr_base):
            raise exceptions.ValidationError(
                _(
                    'El valor del Sustraendo de ISLR debe ser menor o igual '
                    'a la retención de ISLR. Por favor, cambie el valor del '
                    'sustraendo a "0,00" si no aplica o a un valor menor o '
                    'igual a la retención'
                )
            )

    @api.onchange("subtracting")
    def _onchance_subtracting(self):
        self.ensure_one()

        super()._compute_tax_totals()

        self.validate_subtracting()

    @api.constrains('subtracting')
    def _check_subtracting(self):
        for move in self:
            self.validate_subtracting(move)

class AccountMoveLineWithHoldings(models.Model):
    _inherit = "account.move.line"

    @api.depends('quantity', 'discount', 'price_unit', 'tax_ids', 'currency_id')
    def _compute_totals(self):
        for line in self:
            if line.display_type != 'product':
                line.price_total = line.price_subtotal = False
            # Compute 'price_subtotal'.
            line_discount_price_unit = line.price_unit * (1 - (line.discount / 100.0))
            subtotal = line.quantity * line_discount_price_unit

            # Compute 'price_total'.
            if line.tax_ids:
                taxes_res = line.tax_ids.compute_all(
                    line_discount_price_unit,
                    quantity=line.quantity,
                    currency=line.currency_id,
                    product=line.product_id,
                    partner=line.partner_id,
                    is_refund=line.is_refund,
                )
                line.price_subtotal = taxes_res['total_excluded']
                line.price_total = taxes_res['total_included']
            else:
                line.price_total = line.price_subtotal = subtotal
class AccountTaxWithHoldings(models.Model):
    _inherit = "account.tax"

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

                move_iva_records = self.env['account.tax'].search([('withholding_type', '=', 'iva'), ('tax_group_id', '=', tax_group.id)])
                move_islr_records = self.env['account.tax'].search([('withholding_type', '=', 'islr'), ('tax_group_id', '=', tax_group.id)])

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

                            if line_invoice_tax:
                                line_invoice_tax.write({
                                    'move_id': move_id.id,
                                    'tax_line_id': move_id.invoice_tax_id.id,
                                    'credit': total_tax_amount if total_tax_amount > 0 else total_tax_amount * -1,
                                    'balance': total_tax_amount,
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
                                    'credit': total_tax_amount if total_tax_amount > 0 else total_tax_amount * -1,
                                    'balance': total_tax_amount,
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
                        if line_invoice_tax:
                            line_invoice_tax.write({
                                'move_id': move_id.id,
                                'tax_line_id': move_id.invoice_tax_id.id,
                                'credit': total_tax_amount if total_tax_amount > 0 else total_tax_amount * -1,
                                'balance': total_tax_amount,
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
                                'credit': total_tax_amount if total_tax_amount > 0 else total_tax_amount * -1,
                                'balance': total_tax_amount,
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