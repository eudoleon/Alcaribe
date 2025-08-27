# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

VAT_DEFAULT = 'XXXXX'


class AccountMoveWithHoldings(models.Model):
    _inherit = "account.move"

    # Solo IVA
    invoice_tax_id = fields.Many2one(
        comodel_name='account.tax',
        string="VAT withholding",
        domain=[
            ("withholding_type", "=", "iva"),
            ("type_tax_use", "=", "purchase"),
            ("active", "=", True)
        ],
        required=False,
    )
    withholding_iva = fields.Monetary(
        string='VAT withholding',
        store=True,
        compute='_compute_withholding',
        currency_field='company_currency_id'
    )
    sequence_withholding_iva = fields.Char(
        string="VAT withholding sequence",
        readonly=True,
        store=True,
        copy=False
    )
    reference_number = fields.Char(
        string="Invoice number",
        copy=False
    )
    invoice_control_number = fields.Char(
        string="Invoice control number",
        copy=False
    )
    subtracting = fields.Monetary(
        string='Subtrahend',
        default=0.0,
        currency_field='company_currency_id'
    )

    # Exportación solo para IVA
    withholding_agent_vat = fields.Char(
        string="RIF of the Withholding Agent",
        compute="_compute_fields_to_export",
        store=False,
        copy=False,
        readonly=True
    )
    retained_subject_vat = fields.Char(
        string="RIF of the Withholding Taxpayer",
        compute="_compute_fields_to_export",
        store=False,
        copy=False,
        readonly=True
    )
    withholding_number = fields.Char(
        string="Withholding number",
        compute="_compute_fields_to_export",
        store=False,
        copy=False,
        readonly=True
    )
    aliquot_iva = fields.Float(
        string="VAT rate",
        compute="_compute_fields_to_export",
        copy=False,
    )
    amount_tax_iva = fields.Monetary(
        string="Total taxes (VAT)",
        compute="_compute_fields_to_export",
        store=False,
        copy=False,
        readonly=True,
        currency_field='company_currency_id'
    )
    amount_total_iva = fields.Monetary(
        string="Total less VAT withholdings",
        compute="_compute_fields_to_export",
        store=False,
        copy=False,
        readonly=True,
        currency_field='company_currency_id'
    )
    vat_exempt_amount_iva = fields.Monetary(
        string="VAT exempt amount",
        compute="_compute_fields_to_export",
        store=False,
        copy=False,
        readonly=True,
        currency_field='company_currency_id'
    )
    amount_total_purchase = fields.Monetary(
        string="Total purchase",
        compute="_compute_fields_to_export",
        store=False,
        copy=False,
        readonly=True,
        currency_field='company_currency_id'
    )
    withholding_opp_iva = fields.Monetary(
        string='VAT withholding',
        compute="_compute_fields_to_export",
        store=False,
        copy=False,
        readonly=True,
        currency_field='company_currency_id'
    )
    tsc_tax_withholding_date = fields.Date(
        string='Tax withholding date',
        help=(
            'Date on which the withholding taxes associated with the '
            'invoice are withheld. For the purposes of the withholding '
            'voucher, this corresponds to the date of issue'
        ),
        index=True,
        states={'draft': [('readonly', False)]},
        copy=True,
        tracking=True,
        default=fields.Date.context_today
    )

    withholding_iva_generated_by_payment_id = fields.Many2one(
        "account.payment",
        string="Payment that generated the VAT withholding",
        copy=False,
        readonly=True,
    )

    @api.depends(
        'invoice_tax_id',
        'amount_tax',
        'line_ids',
        'line_ids.tax_line_id'
    )
    def _compute_withholding(self):
        for move in self:
            amount_total_withholding_iva = 0.0
            if move.is_invoice(True):
                for line in move.line_ids:
                    if line.tax_line_id and line.tax_line_id.withholding_type == "iva":
                        amount_total_withholding_iva += line.amount_currency
            move.withholding_iva = amount_total_withholding_iva

    def validation_generation_withholding(self, label_value, label_sequence):
        is_one = len(self._ids) == 1
        partner_id = None

        for move in self:
            if partner_id != move.partner_id.id:
                if partner_id is None:
                    partner_id = move.partner_id.id
                else:
                    raise ValidationError(_(
                        "Please select invoices from the same supplier "
                        "to generate the corresponding withholding tax"
                    ))

            if not is_one and move[label_sequence]:
                raise ValidationError(_(
                    "Please select only invoices that do not have such "
                    "withholdings already associated with them"
                ))

            if move.state != "posted" or (move[label_value] or 0.0) >= 0.0:
                raise ValidationError(_(
                    "Please select invoices that have information "
                    "to generate this type of withholding"
                ))

    def generate_withholding_iva(self):
        self.validation_generation_withholding("withholding_iva", "sequence_withholding_iva")
        self._generate_withholding_iva()

    def _generate_withholding_iva(self):
        self.sequence_withholding_iva = self.env["ir.sequence"].next_by_code(
            "account.move.withholding.iva"
        )

    @api.depends(
        "invoice_tax_id",
        "subtracting",
        "sequence_withholding_iva",
        "withholding_iva",
    )
    def _compute_fields_to_export(self):
        self.withholding_agent_vat = (
            self.env.company.vat.upper()
            if self.env.company.vat
            else VAT_DEFAULT
        )

        for move in self:
            sign = -1
            move.withholding_opp_iva = withholding_iva = sign * (move.withholding_iva or 0.0)

            move.retained_subject_vat = (
                move.partner_id.vat.upper()
                if move.partner_id.vat
                else VAT_DEFAULT
            )

            if move.move_type in {'in_invoice', 'in_refund', 'in_receipt'} and withholding_iva != 0.0:
                move.amount_total_purchase = move.amount_total + withholding_iva

                date = move.date or move.invoice_date
                move.withholding_number = f"{date:%Y%m}{move.sequence_withholding_iva:>08}"
                move.amount_tax_iva = move.amount_tax + withholding_iva
                move.amount_total_iva = move.amount_total

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
                        and not line.tax_line_id.withholding_type
                        and line.tax_line_id.amount != 0.0
                    ):
                        aliquot_iva = line.tax_line_id.amount

                move.aliquot_iva = aliquot_iva
                move.vat_exempt_amount_iva = vat_exempt_amount

            else:
                move.amount_total_purchase = 0
                move.withholding_number = "0"
                move.aliquot_iva = 0
                move.amount_tax_iva = 0
                move.amount_total_iva = 0
                move.vat_exempt_amount_iva = 0

    @api.onchange("invoice_tax_id")
    def _onchange_invoice_tax(self):
        super()._compute_tax_totals()

    def action_post(self):
        moves_with_payments = self.filtered('payment_id')
        other_moves = self - moves_with_payments

        if moves_with_payments:
            moves_with_payments.payment_id.action_post()

        if other_moves:
            other_moves._post(soft=False)

        return False
