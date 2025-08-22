# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

VAT_DEFAULT = 'XXXXX'


class AccountMoveWithHoldings(models.Model):
    _inherit = "account.move"

    @api.onchange(
        'invoice_line_ids',
        'invoice_line_ids.name',
        'invoice_line_ids.price_subtotal',
        'invoice_line_ids.price_unit',
        'invoice_line_ids.quantity',
    )

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
        string='VAT withholding ',
        store=True,
        compute='_compute_withholding',
        currency_field='company_currency_id'
    )
    withholding_islr = fields.Monetary(
        string='ISLR withholding ',
        store=True,
        compute='_compute_withholding',
        currency_field='company_currency_id'
    )
    withholding_islr_base = fields.Monetary(
        string='ISLR base withholding',
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
    sequence_withholding_islr = fields.Char(
        string="ISLR withholding sequence",
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

    # Fields to export
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
    withholding_percentage_islr = fields.Float(
        string="Withholding percentage",
        compute="_compute_fields_to_export",
        copy=False,
    )
    withholding_code_islr = fields.Char(
        string="Withholding code",
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
    amount_tax_islr = fields.Monetary(
        string="Total taxes (ISLR)",
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
    vat_exempt_amount_islr = fields.Monetary(
        string="Amount exempt from ISLR",
        compute="_compute_fields_to_export",
        store=False,
        copy=False,
        readonly=True,
        currency_field='company_currency_id'
    )
    amount_total_islr = fields.Monetary(
        string="Total less ISLR withholdings",
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
        string='VAT withholding   ',
        compute="_compute_fields_to_export",
        store=False,
        copy=False,
        readonly=True,
        currency_field='company_currency_id'
    )
    withholding_opp_islr = fields.Monetary(
        string='Total retained',
        compute="_compute_fields_to_export",
        store=False,
        copy=False,
        readonly=True,
        currency_field='company_currency_id'
    )
    total_withheld = fields.Monetary(
        string='ISLR withholding',
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
    withholding_islr_generated_by_payment_id = fields.Many2one(
        "account.payment",
        string="Payment that generated the ISLR withholding",
        copy=False,
        readonly=True,
    )

    def _onchange_set_subtracting_from_label(self):
        """Si alguna línea de la factura tiene 'SUSTRAENDO' en la etiqueta (name),
        sumar su importe y colocarlo en move.subtracting para el comprobante ISLR.
        """
        for move in self:
            # Aplica solo a compras / documentos que pueden tener ISLR (ajusta si necesitas otros tipos)
            if move.move_type not in ('in_invoice', 'in_refund', 'in_receipt'):
                continue

            amount = 0.0
            for line in move.invoice_line_ids:
                # name = "Etiqueta" que ves en la UI
                if not line.name:
                    continue
                if 'sustraendo' in line.name.lower():
                    # Tomamos el subtotal (cantidad * precio, sin impuestos)
                    # Si prefieres usar el precio unitario, cambia a line.price_unit
                    amount += line.price_subtotal or 0.0

            # Solo pisamos si encontramos algo; así permites editar manualmente si no hay línea marcada
            if amount:
                move.subtracting = amount

    @api.depends(
        'invoice_tax_id',
        'amount_tax',
        'line_ids',
        'line_ids.tax_line_id'
    )
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

    def generate_withholding_islr(self):
        self.validation_generation_withholding("withholding_islr", "sequence_withholding_islr")
        self._generate_withholding_islr()

    def _generate_withholding_islr(self):
        self.sequence_withholding_islr = self.env["ir.sequence"].next_by_code(
            "account.move.withholding.islr"
        )

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
            self.env.company.vat.upper()
            if self.env.company.vat
            else VAT_DEFAULT
        )

        for move in self:
            sign = -1
            move.withholding_opp_iva = withholding_iva = sign * (move.withholding_iva or 0.0)
            move.withholding_opp_islr = withholding_islr = sign * (move.withholding_islr or 0.0)

            move.retained_subject_vat = (
                move.partner_id.vat.upper()
                if move.partner_id.vat
                else VAT_DEFAULT
            )

            if move.move_type in {'in_invoice', 'in_refund', 'in_receipt'} and (
                withholding_iva != 0.0 or withholding_islr != 0.0
            ):
                move.amount_total_purchase = move.amount_total + withholding_iva + withholding_islr

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
                    move.total_withheld = sign * move.withholding_islr_base
                    move.amount_tax_islr = move.amount_tax + move.total_withheld
                    move.amount_total_islr = move.amount_total + withholding_iva

                    withholding_percentage_islr = 0.0
                    withholding_code_islr = ''
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

                        if (line.tax_ids):
                            for tax_id in line.tax_ids:
                                if tax_id.withholding_type == 'islr' and line.tsc_cod_retencion_islr:
                                    withholding_code_islr = line.tsc_cod_retencion_islr

                    move.vat_exempt_amount_islr = vat_exempt_amount
                    move.withholding_percentage_islr = sign * withholding_percentage_islr
                    move.withholding_code_islr = withholding_code_islr

                else:
                    move.amount_tax_islr = 0
                    move.amount_total_islr = 0
                    move.withholding_percentage_islr = 0
                    move.withholding_code_islr = ''
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
                move.withholding_code_islr = ''
                move.vat_exempt_amount_iva = 0
                move.total_withheld = 0

    @api.onchange("invoice_tax_id")
    def _onchange_invoice_tax(self):
        super()._compute_tax_totals()

    def validate_subtracting(self, move=None):
        move = move or self
        if abs(move.subtracting) > abs(move.withholding_islr_base):
            raise ValidationError(_(
                'The value of the ISLR Subtrahend must be less '
                'than or equal to the ISLR Withholding. Please change '
                'the value of the subtrahend to "0.00" if not applicable or '
                'to a value less than or equal to the withholding'
            ))

    @api.onchange("subtracting")
    def _onchance_subtracting(self):
        self.ensure_one()
        super()._compute_tax_totals()
        self.validate_subtracting()

    @api.constrains('subtracting')
    def _check_subtracting(self):
        for move in self:
            self.validate_subtracting(move)

    def action_post(self):
        for move in self:
            if move.move_type in {'in_invoice', 'in_refund', 'in_receipt'}:
                for line in move.line_ids:
                    for tax_id in line.tax_ids:
                        if tax_id.withholding_type == 'islr' and not line.tsc_cod_retencion_islr:
                            raise ValidationError(_(
                                "Please, indicate the ISLR withholding code"
                            ))

        moves_with_payments = self.filtered('payment_id')
        other_moves = self - moves_with_payments

        if moves_with_payments:
            moves_with_payments.payment_id.action_post()

        if other_moves:
            other_moves._post(soft=False)

        return False
