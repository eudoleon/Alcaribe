# coding: utf-8
import time
from odoo import models, fields, api, exceptions, _
from odoo.exceptions import UserError


class AccountWhIvaLine(models.Model):
    _name = "account.wh.iva.line"
    _description = "Detalle de retención IVA"

    @api.model
    def _get_type(self):
        """ Return invoice type
        """
        context = self._context
        tyype = context.get('move_type')
        return tyype

    name = fields.Char(
        string='Descripción', size=64, required=True,
        help="Descripcion de la line de la Retencion de IVA")
    retention_id = fields.Many2one(
        'account.wh.iva', string='Retención de IVA',
        ondelete='cascade', help="Retención de IVA")
    invoice_id = fields.Many2one(
        'account.move', string='Factura', required=True, domain="[('move_type', 'in', ('out_invoice', 'in_invoice'))]",
        ondelete='restrict', help="Factura de Retención")
    supplier_invoice_number = fields.Char(
        string='Número de factura del proveedor', size=64,
        related='invoice_id.supplier_invoice_number',
        store=True)
    nro_ctrl = fields.Char(
        'Número de Control', size=32, related='invoice_id.nro_ctrl',
        help="Número utilizado para gestionar facturas preimpresas, por ley "
             "Necesito poner aquí este número para poder declarar"
             "Informes fiscales correctamente.", store=True)
    tax_line = fields.One2many(
        'account.wh.iva.line.tax', 'wh_vat_line_id', string='Impuestos',
        help="Lineas de Impuestos")
    amount_tax_ret = fields.Float(
        string='Importe del Impuesto',
        compute='_amount_all',
        help="Importe del Impuesto")
    base_ret = fields.Float(
        string='Base para la Retención de IVA',
        compute='_amount_all',
        help="Retención sin importe de impuestos")
    move_id = fields.Many2one(
        'account.move', string='Entrada de cuenta',store=True,
        ondelete='restrict', help="Entrada de Cuenta")
    wh_iva_rate = fields.Float(
        string='Tasa de retención de IVA',
        help="Tasa de retención de IVA")
    date = fields.Date(
        string='Fecha del Voucher',
        related='retention_id.date',
        help='Emisión / Vale / Fecha del documento')
    date_ret = fields.Date(
        string='Fecha Contable',
        related='retention_id.date_ret',
        help='Fecha Contable. Fecha de retención')
    state = fields.Selection(related='retention_id.state', readonly=True)

    _sql_constraints = [
        ('ret_fact_uniq', 'unique (invoice_id)', 'La factura ya tiene'
         ' asignado en el depósito de retención, ¡no puede asignárselo dos veces!')
    ]
    type = fields.Selection([
        ('out_invoice', 'Factura de Cliente'),
        ('out_refund', 'Nota de Credito'),
        ('out_debit', 'Nota de Debito'),
        ('in_invoice', 'Factura de Proveedor'),
        ('in_refund', 'Nota de Credito'),
        ('in_debit', 'Nota de Debito')], string='Tipo de Factura', default=_get_type)

    check_false = fields.Boolean('false')

    fb_id = fields.Many2one('account.fiscal.book', 'Fiscal Book',
                            help='Libro fiscal donde esta línea está relacionada')

    @api.onchange('invoice_id')
    def invoice_id_change(self):
        if self.invoice_id:
            self.type = self.invoice_id.type

    def load_taxes(self):
        """ Clean and load again tax lines of the withholding voucher
        """
        awilt = self.env['account.wh.iva.line.tax']
        partner = self.env['res.partner']
        for rec in self:
            if rec.invoice_id:
                rate = rec.retention_id.type in [('out_invoice','out_refund', 'out_debit')] and \
                    partner._find_accounting_partner(
                        rec.invoice_id.company_id.partner_id).wh_iva_rate or \
                    partner._find_accounting_partner(
                        rec.invoice_id.partner_id).wh_iva_rate
                rec.write({'wh_iva_rate': rate})

                #crear el id en las lineas
                self.write({'retention_id': rec.invoice_id.wh_iva_id.id})

                # Clean tax lines of the withholding voucher
                #awilt.search([('wh_vat_line_id', '=', rec.id)]).unlink()
                # Filter withholdable taxes

                for line_ids in rec.invoice_id.invoice_line_ids:
                    # Load again tax lines of the withholding voucher
                    #a retener
                    for i in line_ids.tax_ids:
                        if i.appl_type in ['general','reducido','adicional']:
                            monto_total = float(line_ids.price_total)
                            monto_subtotal = float(line_ids.price_subtotal)
                            if len(line_ids.tax_ids) > 1:
                                taxxx = line_ids.tax_ids[0]
                            else:
                                taxxx = line_ids.tax_ids
                            for tax in taxxx:
                                taxd = tax.id
                            awilt.create({'wh_vat_line_id': rec.id,
                                          'id_tax': taxd,
                                       #   'tax_id': tax.tax_id.id,
                                          'move_id': rec.invoice_id.id,
                                          'base': monto_subtotal,
                                          'amount': monto_total - monto_subtotal
                                          })
                        elif i.appl_type == 'exento':
                            monto_total = float(line_ids.price_total)
                            monto_subtotal = float(line_ids.price_subtotal)
                            if len(line_ids.tax_ids) > 1:
                                taxxx = line_ids.tax_ids[0]
                            else:
                                taxxx = line_ids.tax_ids
                            for tax in taxxx:
                                taxd = tax.id
                            awilt.create({'wh_vat_line_id': rec.id,
                                          'id_tax': taxd,
                                          #   'tax_id': tax.tax_id.id,
                                          'move_id': rec.invoice_id.id,
                                          'base': monto_subtotal,
                                          'amount': 0
                                          })

        return True



    @api.depends('tax_line.amount_ret', 'tax_line.base', 'invoice_id')
    def _amount_all(self):
        """ Return amount total each line
        """
        for rec in self:
            rec.amount_tax_ret = 0
            rec.base_ret = 0
            if rec.create_date != False:
                self.check_false = True
                if rec.invoice_id:
                    self.type = rec.type
                    rec.amount_tax_ret = 0
                    rec.base_ret = 0

                    if rec.invoice_id.move_type == 'in_refund':
                        # rec.amount_tax_ret =  rec.invoice_id.amount_tax

                        rec.amount_tax_ret = sum(l.amount_ret for l in rec.tax_line)
                        rec.base_ret = sum(l.base for l in rec.tax_line)
                    else:
                 #       rec.amount_tax_ret = sum(l.amount_ret for l in rec.tax_line)
                 #        rec.amount_tax_ret = (rec.invoice_id.amount_tax*(float(self.wh_iva_rate)/100))
                 #        rec.base_ret = sum(l.base for l in rec.tax_line)

                        rec.amount_tax_ret = sum(l.amount_ret for l in rec.tax_line)
                        rec.base_ret = sum(l.base for l in rec.tax_line)
            else:
                self.check_false = rec.create_date



    def invoice_id_change(self, invoice_id):
        """ Return invoice data to assign to withholding vat
        @param invoice: invoice for assign a withholding vat
        """
        result = {}
        invoice = self.env['account.move'].browse(invoice_id)
        if invoice:
            self._cr.execute('select retention_id '
                             'from account_wh_iva_line '
                             'where invoice_id=%s' % (invoice_id))
            ret_ids = self._cr.fetchone()
            if bool(ret_ids):
                ret = self.env['account.wh.iva'].browse(ret_ids[0])
                raise UserError("Factura asignada!\n La factura ya se ha asignado en retención")
            result.update({
                'name': invoice.name,
                'supplier_invoice_number': invoice.supplier_invoice_number if invoice.supplier_invoice_number else ' ',
                'nro_ctrl': invoice.nro_ctrl})

        return {'value': result}

