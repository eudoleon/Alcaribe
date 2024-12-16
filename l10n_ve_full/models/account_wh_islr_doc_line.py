# coding: utf-8
import time

from odoo import api
from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _
from odoo.addons import decimal_precision as dp


class IslrWhDocLine(models.Model):
    _name = "account.wh.islr.doc.line"
    _description = 'Lines of Document Income Withholding'

    #@api.depends('amount', 'raw_tax_ut', 'subtract',  'base_amount',
    #             'raw_base_ut', 'retencion_islr')
    def _amount_all(self):
        """ Return all amount relating to the invoices lines
        """
        res = {}
        ut_obj = self.env['account.ut']
        for iwdl_brw in self.browse(self.ids):
            # Using a clousure to make this call shorter
            f_xc = ut_obj.sxc(
                iwdl_brw.invoice_id.company_id.currency_id.id,
                iwdl_brw.invoice_id.currency_id.id,
                iwdl_brw.islr_wh_doc_id.date_uid)

            res[iwdl_brw.id] = {
                'amount': (iwdl_brw.base_amount * (iwdl_brw.retencion_islr / 100.0)) or 0.0,
                'currency_amount': 0.0,
                'currency_base_amount': 0.0,
            }
            for xml_brw in iwdl_brw.xml_ids:
                res[iwdl_brw.id]['amount'] = xml_brw.wh
            if iwdl_brw.invoice_id.currency_id == iwdl_brw.invoice_id.company_id.currency_id:
                res[iwdl_brw.id]['currency_amount'] = f_xc(res[iwdl_brw.id]['amount'])
                res[iwdl_brw.id]['currency_base_amount'] = f_xc(iwdl_brw.base_amount)
            else:
                module_dual_currency = self.env['ir.module.module'].sudo().search(
                    [('name', '=', 'account_dual_currency'), ('state', '=', 'installed')])
                if module_dual_currency:
                    res[iwdl_brw.id]['currency_amount'] = res[iwdl_brw.id]['amount'] * iwdl_brw.invoice_id.tax_today
                    res[iwdl_brw.id]['currency_base_amount'] = iwdl_brw.base_amount * iwdl_brw.invoice_id.tax_today
                else:
                    res[iwdl_brw.id]['currency_amount'] = f_xc(res[iwdl_brw.id]['amount'])
                    res[iwdl_brw.id]['currency_base_amount'] = f_xc(iwdl_brw.base_amount)
        #pass
        #return res


    def _retention_rate(self):
        """ Return the retention rate of each line
        """
        res = {}
        for ret_line in self.browse(self.ids):
            if ret_line.invoice_id:
                pass
            else:
                res[ret_line.id] = 0.0
        return res

    name = fields.Char(
            'Descripción', size=64, help="Description of the voucher line")
    invoice_id = fields.Many2one(
            'account.move', 'Factura', ondelete='set null',
            help="Factura para Retener")
    #amount= fields.Float(compute='_amount_all',  digits=(16, 2), string='Withheld Amount',
    #        multi='all', help="Amount withheld from the base amount")
    amount = fields.Float(string='Cantidad retenida', digits=(16, 2), help="Monto retenido del monto base")
    currency_amount= fields.Float(digits=(16, 2),
            string='Moneda retenida Monto retenido',
            help="Monto retenido del monto base")
    base_amount= fields.Float(
            'Cantidad base', digits=(16,2),
            help="Cantidad base")
    currency_base_amount= fields.Float(digits=(16, 2),
            string='Monto base en moneda extranjera',
            help="Monto retenido del monto base")
    raw_base_ut= fields.Float(
            'Cantidad de UT', digits=(16,2),
            help="Cantidad de UT")
    raw_tax_ut= fields.Float(
            'Impuesto retenido de UT',
            digits=(16,2),
            help="Impuesto retenido de UT")
    subtract = fields.Float(
            'Sustraer', digits=(16,2),
            help="Sustraer")
    islr_wh_doc_id = fields.Many2one(
            'account.wh.islr.doc', 'Retener documento', ondelete='cascade',
            help="Retención de documentos del impuesto sobre la renta generado por esta factura")
    concept_id = fields.Many2one(
            'account.wh.islr.concept', 'Concepto de retención',
            help="Concepto de retención asociado a esta tasa")
    retencion_islr = fields.Float(
            'Tasa de retención',
            digits=(16,2),
            help="Tasa de retención")
    retention_rate = fields.Float(compute=_retention_rate,  string='Tasa de retención',
             help="Withhold rate has been applied to the invoice",
             digits=(16,2))
    xml_ids = fields.One2many(
            'account.wh.islr.xml.line', 'islr_wh_doc_line_id', 'XML Lines',
            help='ID de línea de factura de retención XML')
    iwdi_id = fields.Many2one(
            'account.wh.islr.doc.invoices', 'Factura retenida', ondelete='cascade',
            help="Facturas retenidas")
    partner_id = fields.Many2one('res.partner', related='islr_wh_doc_id.partner_id', string='Partner', store=True)
    #fiscalyear_id = fields.Many2one( 'account.fiscalyear', string='Fiscalyear',store=True)