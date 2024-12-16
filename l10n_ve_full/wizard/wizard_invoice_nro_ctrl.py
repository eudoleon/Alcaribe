# coding: utf-8

from odoo.tools.translate import _
from odoo import models, fields, api
from odoo.exceptions import UserError


class WizardInvoiceNroCtrl(models.TransientModel):
    _name = "wizard.invoice.nro.ctrl"
    _description = 'Invoice nro. ctrl'

    invoice_id = fields.Many2one('account.move', string='Invoice', help="Invoice to be declared damaged.")
    date = fields.Date(string='Date', default=fields.Date.today, help="Fecha utilizada para el papel dañado declarado.")
    sure = fields.Boolean(string='¿Estas Seguro?')
    nro_ctrl = fields.Char(string='Número de Control', size=32, store=True,
                           help="Número utilizado para gestionar facturas preimpresas, por ley "
                                "Necesito poner este número aquí para declarar Informes de impuestos correctamente.")
    comment_paper = fields.Char(string='Comentario')
    paper_anu = fields.Boolean(default='False')
    marck_paper = fields.Boolean(default='False')

    @api.onchange('invoice_id')
    def _get_nro_control(self):
        self.nro_ctrl = self.invoice_id.nro_ctrl
        return

    def action_invoice_create(self, wizard_brw, inv_brw):

        """
        If the invoice has control number, this function is responsible for
        passing the bill to damaged paper
        @param wizard_brw: nothing for now
        @param inv_brw: damaged paper
        """
        invoice_line_obj = self.env['account.move.line']
        # invoice_obj = self.env['account.move']
        acc_mv_obj = self.env['account.move']
        # acc_mv_l_obj =
        # tax_obj = self.env['account.invoice.tax']
        uid = self._uid
        res_company = self.env['res.company'].search([('id', '=', uid)])
        if inv_brw.nro_ctrl:
            invoice = ({
                # 'number': inv_brw.number,
                'number': '%s (%s)' % (inv_brw.number, 'PAPELANULADO_NRO_CTRL_%s' % (
                                        inv_brw.nro_ctrl and inv_brw.nro_ctrl or '')),
                'name': 'PAPELANULADO_NRO_CTRL_%s' % (
                    inv_brw.nro_ctrl and inv_brw.nro_ctrl or ''),
                'comment_paper': self.comment_paper,
                'paper_anu': True,
                'marck_paper': False

            })
            invoice = invoice
            inv_brw = inv_brw.id
            self.env['account.move'].browse(inv_brw).write(invoice)
        else:
            raise UserError("Error de Validación! \n Puede ejecutar este proceso solo si la factura tiene Numero de Control, verifique la factura e intente nuevamente.")

        invoice_line_obj = self.env['account.move.line'].search([('move_id', '=', inv_brw.id)])
        for line in invoice_line_obj:
            id = line.id
            invoice_line = ({
                'quantity': 0.00,
                'invoice_line_tax_id': [],
                'price_unit': 0.00})
            invoice_line_obj.browse(id).write(invoice_line)
        tax_ids = self.env['account.tax'].search([])
        tax = self.env['account.tax'].search([('move_id', '=', inv_brw)])
        if tax:
            self.env['account.tax'].browse(tax.id).write({'invoice_id': []})
        invoice_tax = {
                'name': 'SDCF',
                'tax_id': tax_ids and tax_ids[0].id,
                'amount': 0.00,
                'base': 0.00,
                'account_id': res_company.acc_id.id,
                'invoice_id': inv_brw
        }

        invoice_tax = invoice_tax
        self.env['account.tax'].create(invoice_tax)

        move_id = self.env['account.move'].browse(inv_brw)
        move_id = move_id.move_id.id
        if move_id:
            acc_mv_obj.browse(id).button_cancel()
            acc_mv_obj.browse(id).write({'ref': 'Damanged Paper','amount':0.00})
            for i in self.env['account.move.line'].search([('move_id','=', move_id)]):
                id = i.id
                sql = "UPDATE account_move_line set debit = 0.00,credit = 0.00,balance = 0.00,debit_cash_basis = 0.00,credit_cash_basis = 0.00,balance_cash_basis = 0.00,amount_residual = 0.00,tax_base_amount = 0.00 WHERE id = %s" % (id)
                self._cr.execute(sql)

            invoice_ob = self.env['account.move'].browse(inv_brw).id
            if invoice_ob:
                sql = "UPDATE account_invoice set state = 'paid' ,residual = 0.00 , residual_signed = 0.00 , residual_company_signed = 0.00 WHERE id = %s" % (invoice_ob)
                self._cr.execute(sql)

        return inv_brw

    def new_open_window(self, list_ids, xml_id, module):
        """ Generate new window at view form or tree
        """
        mod_obj = self.env['ir.model.data']
        act_obj = self.env['ir.actions.act_window']
        result = mod_obj._get_id(module, xml_id)
        imd_id = mod_obj.browse(result).res_id
        result = act_obj.search_read([('id', '=', imd_id)])[0]
        result['res_id'] = list_ids
        return result

    def create_invoice(self):
        """ Create a invoice refund
        """
        context = self._context or {}
        wizard_brw = self.browse(self._ids)
        inv_id = self._context.get('active_id')
        for wizard in wizard_brw:
            if not wizard.sure:
                raise UserError("Validation error! \nPlease confirm that you know what you're doing by checking the option bellow!")
            if (wizard.invoice_id and wizard.invoice_id.company_id.jour_id and
                    wizard.invoice_id and wizard.invoice_id.company_id.acc_id):
                inv_id = self.action_invoice_create(wizard, wizard.invoice_id)
            else:
                raise UserError("Error de Validación! \nDebe ir al formulario de empresa y configurar un diario y una cuenta para facturas dañadas")

        return self.new_open_window([inv_id], 'action_invoice_tree1', 'account')
