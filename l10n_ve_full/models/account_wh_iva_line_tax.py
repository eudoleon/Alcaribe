# coding: utf-8
import time
from odoo import models, fields, api, exceptions, _
from odoo.exceptions import UserError
from odoo.addons import decimal_precision as dp



class AccountWhIvaLineTax(models.Model):
    _name = 'account.wh.iva.line.tax'

    move_id = fields.Many2one('account.move',string='Invoice', required=True,
        ondelete='restrict', help="Withholding invoice")
    id_tax = fields.Integer('hola')

    inv_tax_id = fields.Many2one(
        'account.tax', string='Impuesto de factura',
        ondelete='set null', help="Tax Line")
    wh_vat_line_id = fields.Many2one(
        'account.wh.iva.line', string='VAT Withholding Line', required=True,
        ondelete='cascade', help="Line withholding VAT")
    tax_id = fields.Many2one(
        'account.tax', string='Tax',
        related='inv_tax_id.tax_id', store=True, readonly=True,
        ondelete='set null', help="Tax")
    name = fields.Char(
        string='Nombre del Impuesto', size=256,
        related='inv_tax_id.name', store=True, readonly=True,
        ondelete='set null', help=" Tax Name")
    base = fields.Float(
        string='Base de la factura', digit=(16, 2),
        store=True, compute='_get_base_amount',
        help="Tax Base")
    amount = fields.Float(
        string='Cantidad gravada', digits=(16, 2),
        store=True, compute='_get_base_amount',
        help="Withholding tax amount")
    company_id = fields.Many2one(
        'res.company', string='Company',
        related='inv_tax_id.company_id', store=True, readonly=True,
        ondelete='set null', help="Company")
    amount_ret = fields.Float(
        string='Cantidad gravada retenida',
        store=True, compute='_get_amount_ret', digits=(16, 2), inverse='_set_amount_ret',
        help="Importe de retención de IVA")
    alicuota = fields.Float('% Alicuota del impuesto')


    @api.depends('inv_tax_id')
    def _get_base_amount(self):
        """ Return withholding amount
        """
        for record in self:

            f_xc = self.env['account.ut'].sxc(
                record.move_id.currency_id.id,
                record.move_id.company_id.currency_id.id,
                record.wh_vat_line_id.retention_id.date)
            if record.move_id.currency_id == record.move_id.company_id.currency_id:
                record.base = f_xc(record.base)
                record.amount = f_xc((record.amount))
            else:
                module_dual_currency = self.env['ir.module.module'].sudo().search([('name','=','account_dual_currency'),('state','=','installed')])
                if module_dual_currency:
                    record.base = record.base * record.move_id.tax_today
                    record.amount = record.amount * record.move_id.tax_today
                else:
                    record.base = f_xc(record.base)
                    record.amount = f_xc((record.amount))
            if record.id_tax:
                busq = self.env['account.tax'].search([('id', '=', record.id_tax)])
                record.name = busq.name
                record.alicuota = busq.amount

    def _set_amount_ret(self):
        """ Change withholding amount into iva line
        @param value: new value for retention amount
        """
        # NOTE: use ids argument instead of id for fix the pylint error W0622.
        # Redefining built-in 'id'
        for record in self:
            if record.wh_vat_line_id.retention_id.type != 'out_invoice':
                continue
            if not record.amount_ret:
                continue
            sql_str = """UPDATE account_wh_iva_line_tax set
                    amount_ret='%s'
                    WHERE id=%d """ % (record.amount_ret, record.id)
            self._cr.execute(sql_str)
        return True


    @api.depends('amount', 'wh_vat_line_id.wh_iva_rate')
    def _get_amount_ret(self):
        """ Return withholding amount
        """
        for record in self:
            # TODO: THIS NEEDS REFACTORY IN ORDER TO COMPLY WITH THE SALE
            # WITHHOLDING
            record.amount_ret = (record.amount * record.wh_vat_line_id.wh_iva_rate / 100.0)

