from odoo import models, fields, api, _
from odoo.exceptions import Warning

class recordRetention(models.TransientModel):
    _name = 'account.wh.iva.record.retention'

    invoice_ids = fields.Many2many('account.move', string='Facturas')
    control_number = fields.Char('Numero de Comprobante')
    partner_id = fields.Many2one('res.partner', string='Socio', required=True )

    def generate_retention_iva(self):
        if not self.partner_id.wh_iva_agent:
            raise Warning(_('El cliente debe estar registrado como agente de retención de ingresos'))
        for inv in self.invoice_ids:
            monto_tax = 0
            resul = inv._withholdable_tax()
            for i in inv.line_ids:
                if len(inv.line_ids.tax_ids) == 1:
                    for tax in i.tax_ids:
                        if tax.amount == 0:
                            monto_tax = 2000
            if inv.company_id.partner_id.wh_iva_agent and inv.partner_id.wh_iva_agent and resul and monto_tax == 0:
                if inv.state == 'posted':
                    for ilids in inv.invoice_line_ids:
                        inv.check_document_date()
                        inv.check_invoice_dates()
                        apply = inv.check_wh_apply()
                        if apply:
                            inv.check_withholdable()
                            inv.action_wh_iva_supervisor()
                            inv.action_wh_iva_create()
                            inv.wh_iva_id.number = self.control_number

    def generate_retention_supplier(self):
        if not self.partner_id.wh_iva_agent:
            raise Warning(_('El proveedor debe estar registrado como agente de retención de ingresos'))
        for inv in self.invoice_ids:
            monto_tax = 0
            resul = inv._withholdable_tax()
            for i in inv.line_ids:
                if len(inv.line_ids.tax_ids) == 1:
                    for tax in i.tax_ids:
                        if tax.amount == 0:
                            monto_tax = 2000
            if inv.company_id.partner_id.wh_iva_agent and inv.partner_id.wh_iva_agent and resul and monto_tax == 0:
                if inv.state == 'posted':
                    for ilids in inv.invoice_line_ids:
                        inv.check_document_date()
                        inv.check_invoice_dates()
                        apply = inv.check_wh_apply()
                        if apply:
                            inv.check_withholdable()
                            inv.action_wh_iva_supervisor()
                            inv.action_wh_iva_create()






