# -*- coding: utf-8 -*-
from odoo import fields, models

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def create_vendor_bill(self):
        vendor_bill = self.env['account.move'].browse()
        print(">>>>>>>>>>>>Vendor Bill",vendor_bill)
        vendor_bill = vendor_bill.new({
            'partner_id': self.partner_id.id,
            'purchase_id': self.id,
            'company_id': self.env.company.id,
            'invoice_payment_term_id': self.payment_term_id.id,
            'currency_id': self.currency_id.id,
            'fiscal_position_id': self.fiscal_position_id,
            'date': fields.date.today(),
            'ref': self.partner_ref,
            # 'type': 'in_invoice',
        })
        vendor_bill._onchange_purchase_auto_complete()
        self.invoice_ids += vendor_bill

    def _get_invoiced(self):
        super(PurchaseOrder, self)._get_invoiced()
        partner_ref = ''
        if self.invoice_status == 'to invoice':
            partner_ref = ''
            if self.partner_ref and self.name:
                partner_ref = self.name +'-'+ self.partner_ref
            else:
                partner_ref = self.name
            self.write({'partner_ref': partner_ref})
            self.create_vendor_bill()
            super(PurchaseOrder, self)._get_invoiced()
