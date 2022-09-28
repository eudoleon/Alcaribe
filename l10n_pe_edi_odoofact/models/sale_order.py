# -*- coding: utf-8 -*-
###############################################################################
#
#    Copyright (C) 2019-TODAY OPeru.
#    Author      :  Grupo Odoo S.A.C. (<http://www.operu.pe>)
#
#    This program is copyright property of the author mentioned above.
#    You can`t redistribute it and/or modify it.
#
###############################################################################

from odoo import api, fields, models, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _create_invoices(self, grouped=False, final=False, date=None):
        res = super(SaleOrder, self)._create_invoices(grouped, final, date)
        for move in res:
            has_downpayment = False
            for mline in move.invoice_line_ids:
                if mline.product_id and mline.product_id.l10n_pe_edi_is_for_advance:
                    has_downpayment = True
                    break
            if final and has_downpayment:
                move.l10n_pe_edi_operation_type = '4'
            move._get_dues_ids()
        return res

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _prepare_invoice_line(self, **optional_values):
        res = super(SaleOrderLine, self)._prepare_invoice_line(**optional_values)
        if self.is_downpayment:
            invoice_line = self.invoice_lines.filtered(lambda x: x.parent_state == 'posted')
            if invoice_line:
                res['l10n_pe_edi_regularization_advance'] = True
                res['l10n_pe_edi_advance_serie'] = invoice_line[0].move_id.l10n_pe_edi_serie
                res['l10n_pe_edi_advance_number'] = invoice_line[0].move_id.l10n_pe_edi_number
        return res