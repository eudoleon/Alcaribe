# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class AccountPartialReconcile(models.Model):
    _inherit = "account.partial.reconcile"

    def unlink(self):
        reverse_withholding_iva = []
        reverse_withholding_islr = []

        for partial in self:
            move_id = partial.credit_move_id.move_id
            payment_id = partial.debit_move_id.payment_id

            payment_iva_id = move_id.withholding_iva_generated_by_payment_id
            payment_islr_id = move_id.withholding_islr_generated_by_payment_id

            if move_id.sequence_withholding_iva and payment_iva_id and payment_iva_id == payment_id:
                reverse_withholding_iva.append((move_id, payment_id))

            if move_id.sequence_withholding_islr and payment_islr_id and payment_islr_id == payment_id:
                reverse_withholding_islr.append((move_id, payment_id))

        res = super().unlink()

        if res:
            for move_id, payment_id in reverse_withholding_iva:
                payment_id.temp_sequence_withholding_iva = move_id.sequence_withholding_iva
                move_id.withholding_iva_generated_by_payment_id = False
                move_id.sequence_withholding_iva = False

            for move_id, payment_id in reverse_withholding_islr:
                payment_id.temp_sequence_withholding_islr = move_id.sequence_withholding_islr
                move_id.withholding_islr_generated_by_payment_id = False
                move_id.sequence_withholding_islr = False

        return res
