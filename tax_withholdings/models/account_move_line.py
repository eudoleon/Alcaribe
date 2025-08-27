# -*- coding: utf-8 -*-

from collections import defaultdict
from odoo import _, api, fields, models


class AccountMoveLineWithHoldings(models.Model):
    _inherit = "account.move.line"

    # 🔇 Campo de ISLR eliminado. Si existía en tu módulo,
    # al quitarlo del código solo queda la columna huérfana en BD (no pasa nada).
    # Si quieres borrar la columna físicamente, hazlo con un script SQL en una migración.

    @api.depends('quantity', 'discount', 'price_unit', 'tax_ids', 'currency_id')
    def _compute_totals(self):
        for line in self:
            if line.display_type != 'product':
                line.price_total = line.price_subtotal = False
                continue

            # Subtotal sin impuestos
            line_discount_price_unit = line.price_unit * (1 - (line.discount / 100.0))
            subtotal = line.quantity * line_discount_price_unit

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

                # Solo IVA (nada de ISLR)
                tax_iva = 0.0
                if line.move_id:
                    for tax in line.tax_ids:
                        # Cálculo adicional cuando tengas un impuesto "IVA" + un "invoice_tax_id"
                        # (mantengo tu lógica original, pero aislada a IVA)
                        if 'iva' in (tax.name or '').lower() and line.move_id.invoice_tax_id:
                            amount = line.price_unit * tax.amount / 100
                            amount_iva = (amount * line.move_id.invoice_tax_id.amount / 100) * line.quantity
                            tax_iva += amount_iva

                line.price_total = taxes_res['total_included'] + tax_iva
            else:
                line.price_total = line.price_subtotal = subtotal

    def reconcile(self):
        """Reconciliación dejando SOLO la generación de retención IVA."""
        res = super().reconcile()

        move_iva_ids = self.env["account.move"]
        payment_iva_ids = defaultdict(lambda: self.env["account.move"])

        for partial in res["partials"]:
            move_id = partial.credit_move_id.move_id

            if (
                not move_id.is_invoice(include_receipts=True)
                or move_id.payment_state not in {'paid', 'in_payment', 'partial'}
            ):
                continue

            payment_id = partial.debit_move_id.payment_id

            # Solo IVA (ISLR eliminado)
            if (move_id.withholding_iva or 0.0) < 0.0 and not move_id.sequence_withholding_iva:
                if payment_id and payment_id.temp_sequence_withholding_iva:
                    payment_iva_ids[payment_id] |= move_id
                else:
                    move_iva_ids |= move_id
                    move_id.withholding_iva_generated_by_payment_id = payment_id

        if move_iva_ids:
            move_iva_ids._generate_withholding_iva()

        for payment_id, move_ids in payment_iva_ids.items():
            move_ids.sequence_withholding_iva = payment_id.temp_sequence_withholding_iva
            move_ids.withholding_iva_generated_by_payment_id = payment_id
            payment_id.temp_sequence_withholding_iva = False

        return res
