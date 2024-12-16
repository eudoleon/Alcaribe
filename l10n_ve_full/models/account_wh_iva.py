# coding: utf-8
import time
from odoo import models, fields, api, exceptions, _
from odoo.exceptions import UserError

class AccountWhIva(models.Model):
    _name = "account.wh.iva"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Rentención de IVA"
    _check_company_auto = True

    @api.model
    def create(self, values):
        wh_iva_id = super(AccountWhIva, self).create(values)
        wh_iva_id._partner_invoice_check()
        return wh_iva_id


    def name_get(self,):
        res = []
        for item in self:
            if item.number and item.state == 'done':
                res.append((item.id, '%s (%s)' % (item.number, item.name)))
            else:
                res.append((item.id, '%s' % (item.name)))
        return res



    @api.model
    def _get_type(self):
        """ Return invoice type
        """
        context = self._context
        tyype = context.get('move_type')
        return tyype


    def _get_journal(self):
        # partner_id = self._context.get('uid')
        res = []
        partner_sale = self.env['account.journal'].search([('type', '=', 'sale'),('code', '=', 'RIV')])

        partner_purchase = self.env['account.journal'].search([('type', '=', 'purchase'),('code', '=', 'RIC')])
        type =  self._context.get('default_type')
        if not type:
            context = self._context
            tyype = context.get('type')
            if not tyype:
                res = []
        if type and type in ('out_invoice', 'out_refund','out_debit'):
            res = partner_sale
        elif type and type in ('in_invoice', 'in_refund','in_debit'):
            res = partner_purchase
        return res

    @api.model
    def _get_fortnight(self):
        """ Return currency to use
        """
        dt = time.strftime('%Y-%m-%d')
        tm_mday = time.strptime(dt, '%Y-%m-%d').tm_mday
        return tm_mday <= 7 and 'False' or 'True'

    @api.model
    def _get_currency(self):
        """ Return currency to use
        """
        if self.env.user.company_id:
            return self.env.user.company_id.currency_id.id
        return self.env['res.currency'].search([('rate', '=', 1.0)], limit=1)



    def action_cancel(self):
        """ Call cancel_move and return True
        """
        self.get_reconciled_move()
        self.cancel_move()
        self.clear_wh_lines()
        self.amount_base_ret = 0
        self.total_tax_ret = 0
        self.write({'state': 'cancel'})
        return True


    def get_reconciled_move(self):
        awil_obj = self.env['account.wh.iva.line']
        awil_brw = awil_obj.search([('retention_id','=',self.id)])

        dominio = [('move_id', '=', awil_brw.move_id.id),
                   ('reconciled', '=', True)]
        obj_move_line = self.env['account.move.line'].search(dominio)
        nombre = False
        obj_move_name = []
        for a in obj_move_line:
            nombre = a.move_name
        if nombre:
            obj_move_name = self.env['account.move.line'].search([('move_name', '=', nombre)])
            for move_line_ids in obj_move_name:
                move_line_ids
        if obj_move_line and len(obj_move_name)<=1:
            raise exceptions.ValidationError(
                ('El Comprobante ya tiene una aplicacion en la factura %s, debe desconciliar el comprobante para poder cancelar') % awil_brw.invoice_id.name)
        else:
            return True


    def cancel_move(self):
        """ Delete move lines related with withholding vat and cancel
        """
        # moves = self.pool.get('account.move')
        #moves =  self.env['res.partner']
        moves = []
        for ret in self:
            if ret.state == 'done':
                for ret_line in ret.wh_lines:
                    ret_line.move_id.button_draft()
                    ret_line.move_id.button_cancel()
                    #if ret_line.move_id:
                    #    ret_line.move_id._reverse_moves([{'date': fields.Date.today(), 'ref': _('Reversal of %s') % ret_line.move_id.name}], cancel=True)
                    #    ret_line.move_id.wh_iva = False
            # second, set the withholding as cancelled
            ret.write({'state': 'cancel'})
        return True


    def set_to_draft(self):
        self.write({'state': 'draft'})
        return True

    @api.model
    def _get_valid_wh(self, amount_ret, amount, wh_iva_rate,
                      offset=0.5):
        """ This method can be override in a way that
        you can afford your own value for the offset
        @param amount_ret: withholding amount
        @param amount: invoice amount
        @param wh_iva_rate: iva rate
        @param offset: compensation
        """
        if amount != 0 and amount_ret != 0:
            amount_total = '{0:,.2f}'.format(amount * (wh_iva_rate - offset) / 100.0)
            amount_total2 = '{0:,.2f}'.format(amount * (wh_iva_rate + offset) / 100.0)
        else:
            amount_total = 0
            amount_total2 = 0
        return (amount_ret >= float((amount * (wh_iva_rate - offset) / 100.0)) and
                amount_ret <= float((amount * (wh_iva_rate + offset) / 100.0)))


    def check_wh_taxes(self):
        """ Check that are valid and that amount retention is not greater than amount
        """
        note = _('Los impuestos en las siguientes facturas han sido mal calculados\n\n')
        error_msg = ''
        for record in self:
            wh_line_ids = []
            for wh_line in record.wh_lines:
                for tax in wh_line.tax_line:
                    if not record._get_valid_wh(
                            tax.amount_ret, tax.amount,
                            tax.wh_vat_line_id.wh_iva_rate):
                        if wh_line.id not in wh_line_ids:
                          #   note += _('\tInvoice: %s, %s, %s\n') % (
                          #       wh_line.invoice_id.name,
                          # #      wh_line.invoice_id.number,
                          #       wh_line.invoice_id.supplier_invoice_number
                          #       )
                            wh_line_ids.append(wh_line.id)
                        note += '\t\t%s\n' % tax.name
                    if tax.amount_ret > tax.amount:
                        porcent = '%'
                        error_msg += _(
                            "El importe retenido:% s (% s% s), debe ser inferior al"
                            " importe del impuesto %s(%s%s).") % (
                                tax.amount_ret, wh_line.wh_iva_rate, porcent,
                                tax.amount, tax.amount * 100, porcent)
            if wh_line_ids and record.type == 'in_invoice':
                raise UserError("Impuestos retenidos mal calculados \n %s" % (note))
        if error_msg:
            raise UserError("Acción no valida!\n %s" % (error_msg))
        return True


    def check_vat_wh(self):
        """ Check whether the invoice will need to be withheld taxes
        """
        res = {}
        for obj in self:
            if obj.type == 'out_invoice' and \
                    (not obj.date or not obj.date_ret):
                raise UserError("Error!\n Debe indicar: Fecha de contabilidad y (o) Fecha del comprobante")
            for wh_line in obj.wh_lines:
                if not wh_line.tax_line:
                    res[wh_line.id] = (
                        wh_line.invoice_id.name,
                        wh_line.invoice_id.id,
                        wh_line.invoice_id.supplier_invoice_number)
        if res:
            note = _(
                'Las siguientes facturas aún no se han retenido:\n\n')
            for i in res:
                note += '* %s, %s, %s\n' % res[i]
            note += _('\nPor favor, cargue los impuestos a retener e intente nuevamente')

            raise UserError("¡Facturas con impuestos retenidos faltantes!\n %s" % (note))
        return True


    def check_invoice_nro_ctrl(self):
        """ Method that check if the control number of the invoice is set
        Return: True if the control number is set, and raise an exception
        when is not.
        """
        res = {}
        for obj in self:
            for wh_line in obj.wh_lines:
                if not wh_line.invoice_id.nro_ctrl:
                    res[wh_line.id] = (
                        wh_line.invoice_id.name,
                     #   wh_line.invoice_id.number,
                        wh_line.invoice_id.supplier_invoice_number)
        if res:
            note = _('Las siguientes facturas no serán retenidas:\n\n')
            for i in res:
                if res[i]:
                    hello= res[i]
                    note += '* %s, %s\n' % res[i]
            note += _('\nPor favor, escriba el número de control e intente nuevamente')

            raise UserError("¡Facturas con número de control perdido!\n %s" % (note))
        return True


    def write_wh_invoices(self):
        """ Method that writes the wh vat id in sale invoices.
        Return: True: write successfully.
                False: write unsuccessfully.
        """
        for obj in self:
            if obj.type in ('out_invoice', 'out_refund', 'out_debit','in_debit', 'in_invoice','in_refund'):
                for wh_line in obj.wh_lines:
                    if not wh_line.invoice_id.write({'wh_iva_id': obj.id}):
                        return False
        return True

    @api.model
    #@api.onchange('partner_id')
    def _check_partner(self):
        """ Determine if a given partner is a VAT Withholding Agent
        """
        partner = self.env['res.partner']
        for obj in self:
            if obj.type in ('out_invoice', 'out_refund'):
                if not partner._find_accounting_partner(
                        obj.partner_id).wh_iva_agent:
                    raise exceptions.ValidationError(
                        _('El socio debe estar reteniendo el iva agente.'))
            else:
                if not partner._find_accounting_partner(
                        obj.company_id.partner_id).wh_iva_agent:
                    raise exceptions.ValidationError(
                        _('El socio debe estar reteniendo el iva agente.'))

    #_sql_constraints = [
    #    ('ret_num_uniq', 'unique (type,partner_id,company_id)',
    #     'number must be unique by partner and document type!')
    #]


    def write(self, values):
        #print("values: ", values)

        res = super(AccountWhIva, self).write(values)
        self._partner_invoice_check()
        return res


    def action_move_create(self):
        """ Create movements associated with retention and reconcile
        """
        ctx = dict(self._context,
                   vat_wh=True,
                   company_id=self.env.user.company_id.id)
        for ret in self.with_context(ctx):
            for line in ret.wh_lines:
                if line.move_id or line.invoice_id.wh_iva:
                    raise UserError("Factura ya retenida!\n¡Debe omitir la siguiente factura %s" % (line.invoice_id.name))


            # TODO: Get rid of field in future versions?
            # We rather use the account in the invoice
            #acc_id = ret.account_id.id


            if ret.wh_lines:

                for line in ret.wh_lines:
                    if line.invoice_id.move_type in ['in_invoice', 'in_refund', 'in_debit']:
                        name = ('COMP. RET. IVA ' + (ret.number if ret.number else str()) + ' Doc. ' + (line.invoice_id.supplier_invoice_number if line.invoice_id.supplier_invoice_number else str()))
                    else:
                        name = ('COMP. RET. IVA ' + (ret.number if ret.number else str()) + ' Doc. ' + (line.invoice_id.name if line.invoice_id.name else str()))

                    #invoice = self.env['account.move'].with_context(ctx).browse(line.invoice_id.id)
                    invoice = line.invoice_id
                    amount = line.amount_tax_ret
                    #amount = self.total_tax_ret
                    # if line.invoice_id.partner_id.supplier_rank > 1:
                    #     account_id = line.invoice_id.partner_id.property_account_payable_id
                    # elif line.invoice_id.partner_id.customer_rank > 1:
                    #     account_id = line.invoice_id.partner_id.property_account_receivable
                    account_id = ret.account_id
                    journal_id = ret.journal_id.id
                    writeoff_account_id = False
                    writeoff_journal_id = False
                    date = ret.date_ret
                    name = name
                    line_tax_line = line.tax_line
                    #print('line_id', line.id)
                    wh_iva_tax_line = self.env['account.wh.iva.line.tax'].search([('wh_vat_line_id','=',line.id)])
                    #print("wh_iva_tax_line", wh_iva_tax_line )
                    ret_move = invoice.ret_and_reconcile(
                        abs(amount), account_id, journal_id,
                        writeoff_account_id,writeoff_journal_id,
                        date,name,wh_iva_tax_line, 'wh_iva')

                    rl = {'move_id': ret_move.id}
                    lines = [(1, line.id, rl)]
                    ret.write({'wh_lines': lines})

                    if (rl and line.invoice_id.move_type
                            in ['out_invoice', 'out_refund', 'out_invoice','in_invoice','in_refund','out_debit']):
                        invoice.write({'wh_iva_id': ret.id})
            return True


    def clear_wh_lines(self):
        """ Clear lines of current withholding document and delete wh document
        information from the invoice.
        """
        if self.ids:
            wil = self.env['account.wh.iva.line'].search([
                ('retention_id', 'in', self.ids)])

            wil_tax = self.env['account.wh.iva.line.tax'].search(
                [('wh_vat_line_id','=', wil.ids)])
            invoice = wil.mapped("invoice_id")
            if wil: wil.unlink()
            for wilt in wil_tax: wilt.unlink()
            if invoice: invoice.write({'wh_iva_id': False,'wh_iva': False})

        return True


    def _partner_invoice_check(self):
        """ Verify that the partner associated of the invoice is correct
        @param values: Contain withholding lines, partner id and invoice_id
        """
        partner = self.env['res.partner']
        for record in self:
            inv_str = str()
            for line in record.wh_lines:
                acc_part_id = partner._find_accounting_partner(
                    line.invoice_id.partner_id)
                if acc_part_id.id != record.partner_id.id:
                    inv_str += '%s' % '\n' + (
                        line.invoice_id.name or
                        line.invoice_id.number or '')

            if inv_str:
                raise UserError(
                    _("Facturas incorrectas \nLas siguientes facturas no son las seleccionadas"
                      " partner: %s ") % (inv_str))

        return True



    def compute_amount_wh(self):
        """ Calculate withholding amount each line
        """
        #if self.check_wh_lines_fortnights():
        for retention in self:
            whl_ids = [line.id for line in retention.wh_lines]
            if whl_ids:
                awil = self.env['account.wh.iva.line'].browse(whl_ids)
                awil.load_taxes()
        return True


    def _dummy_cancel_check(self):
        '''
        This will be the method that another developer should use to create new
        check on Withholding Document
        Make super to this method and create your own cases
        '''
        return True


    def _check_tax_iva_lines(self):
        """Check if this IVA WH DOC is being used in a TXT IVA DOC"""
        til = self.env["txt.iva.line"].search([
            ('txt_id.state', '!=', 'draft'),
            ('voucher_id', 'in', self.ids)])

        if not til:
            return True

        note = _('El siguiente DOC IVA TXT debe establecerse en Borrador antes de '
                 'Cancelar este documento\n\n')
        ti_ids = list(set([til_brw.txt_id.id for til_brw in til]))
        for ti_brw in self.env['txt.iva'].browse(ti_ids):
            note += '%s\n' % ti_brw.name
            raise UserError(_("Procedimiento Invalido!\n %s")% (note))


    def cancel_check(self):
        '''
        Unique method to check if we can cancel the Withholding Document
        '''

        if not self._check_tax_iva_lines():
            return False
        if not self._dummy_cancel_check():
            return False
        return True


    def _dummy_confirm_check(self):
        '''
        This will be the method that another developer should use to create new
        check on Withholding Document
        Make super to this method and create your own cases
        '''
        return True

    def confirm_check(self):
        '''
        Unique method to check if we can confirm the Withholding Document
        '''
        if (not self.check_wh_lines() or
                # not self.check_wh_lines_fortnights() or
                not self.check_invoice_nro_ctrl() or
                not self.check_vat_wh() or
                not self.check_wh_taxes() or
                not self.write_wh_invoices() or
                not self._dummy_confirm_check()):
            return False
        else:
            consulta = self.env['account.wh.iva'].search([('name', '=', self.name), ('number_2', '!=', False)])
            if not consulta:
                if self.type in ['in_invoice', 'in_refund']:
                    self.number = self.update_ret_number()
                    self.number_2 = self.number
            else:
                if self.type in ['in_invoice', 'in_refund']:
                    self.number = consulta[-1].number_2
            # dt = time.strftime('%Y-%m-%d')

            self.write({'date_ret': self.date_ret})
            self.action_move_create()
            if self.type in ('in_invoice', 'in_refund', 'in_debit'):
                if not self.number:
                    self.number = self._get_sequence_code()
                    self.write({'number': self.number})

            self.write({'state': 'done'})
            self.wh_lines[0].invoice_id.write({'wh_iva': True,'iva_number_asignado':self.number})
        return True

    def _get_company(self):
        res_company = self.env['res.company'].search([('id', '=', self.company_id.id)])
        return res_company

    def _get_default_company(self):
        res_company = self.env['res.company'].search([('id', '=', self.wh_lines.invoice_id.company_id.id)])
        if not res_company:
            res_company = self.env.company
        return res_company

    def _get_sequence_code(self):
        # metodo que crea la secuencia del número de control, si no esta creada crea una con el
        # nombre: 'l10n_nro_control

        self.wh_lines.invoice_id.ensure_one()
        if self.wh_lines[0].invoice_id.iva_number_asignado:
            return self.wh_lines[0].invoice_id.iva_number_asignado
        SEQUENCE_CODE = 'account.wh.iva.in_invoice'
        company_id = self._get_company()
        #IrSequence = self.env['ir.sequence'].with_context(force_company=company_id.id)
        IrSequence = self.env['ir.sequence'].with_company(company_id)
        self.number = IrSequence.next_by_code(SEQUENCE_CODE)
        return self.number

    #@api.onchange('date_ret')

    def update_ret_number(self):
        local_number = self.env['ir.sequence'].next_by_code('purchase.account.wh.iva.sequence')
        if local_number and self.date_ret:
            account_month = self.date_ret.split('-')[1]
            if not account_month == local_number[4:6]:
                local_number = local_number[:4] + account_month + local_number[6:]
        return local_number

    def check_wh_lines(self):
        """ Check that wh iva has lines to withhold."""
        for awi_brw in self:
            if not awi_brw.wh_lines:
                raise UserError(
                    _("Valores faltantes! \nLíneas de retención faltantes!!!"))
        return True


    def copy(self, default=None):
        """ Update fields when duplicating
        """
        # NOTE: use ids argument instead of id for fix the pylint error W0622.
        # Redefining built-in 'id'
        if not default:
            default = {}
        for record in self:
            if record.type == 'in_invoice':
                raise UserError(
                    _('Alerta! \n No puedes duplicar este documento!!!'))

        default.update({
            'state': 'draft',
            'number': False,
         #   'code': False,
            'wh_lines': [],
           # 'period_id': False
        })

        return super(AccountWhIva, self).copy(default)


    def unlink(self):
        """ Overwrite the unlink method to throw an exception if the
        withholding is not in cancel state."""
        for awi_brw in self:
            if awi_brw.state != 'cancel':
                raise UserError(
                    _("Procedimiento inválido!! \nEl documento de retención debe estar en estado Cancelado "
                      "para poder ser eliminado."
                      ))

            else:
                awi_brw.clear_wh_lines()
        return super(AccountWhIva, self).unlink()


    number_2 =fields.Char('numero respaldo')

    name = fields.Char(
        string='Descripción', size=64,
        help="Descripcion de la "
             "Retencion",tracking=True)
    '''
    code = fields.Char(
        string='Internal Code', size=32, readonly=True,
        #states={'draft': [('readonly', False)]}, default=_get_wh_iva_seq,
        help="Internal withholding reference")
    '''
    number_customer= fields.Char(
        string='Numero de Comprobante', size=32,
        help="Numero de Retencion de IVA")
    number = fields.Char(
        string='Numero de Comprobante', size=32,
        help="Numero de Retencion de IVA",tracking=True)
    type = fields.Selection([
        ('out_invoice', 'Factura de Cliente'),
        ('out_refund', 'Nota de Credito'),
        ('out_debit', 'Nota de Debito'),
        ('in_invoice', 'Factura de Proveedor'),
        ('in_refund', 'Nota de Credito'),
        ('in_debit', 'Nota de Debito')], string='Type', default=_get_type, readonly=True, help="Withholding type",tracking=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmado'),
        ('done', 'Realizado'),
        ('cancel', 'Cancelado')], string='Estado', readonly=True, default='draft',
        help="Estado de retención",tracking=True)
    date_ret = fields.Date(
        string='Fecha Contable',
        help="Mantener vacío para usar la fecha actual")
    date = fields.Date(
        string='Fecha del Vale',
        help="Emisión / Vale / Fecha del documento")
    account_id = fields.Many2one(
        'account.account', string='Cuenta',
        help="La cuenta de pago utilizada para esta retención.")
    currency_id = fields.Many2one(
        'res.currency', string='Moneda', default=_get_currency,
        help="Moneda")
    period_id = fields.Date(string='Periodo')
    company_id = fields.Many2one(
        'res.company', string='Compañia', readonly=True, store=True,
        default=_get_default_company,#lambda self: self.env.company.id,
        help="Compañia")
    partner_id = fields.Many2one(
        'res.partner', string='Empresa',
        help="Retención de cliente / proveedor")
    journal_id = fields.Many2one(
        'account.journal', string='Diario', default=_get_journal,
        help="Entrada de diario")
    wh_lines = fields.One2many(
        'account.wh.iva.line', 'retention_id',
        string='Líneas de retención de IVA',
        help="Líneas de retención de IVA")
    amount_base_ret = fields.Float(
        string='Importe', # digits=(16, 2),
        compute='_amount_ret_all', store=True,
        help=" Base para Calcular monto del impuesto")
    total_tax_ret = fields.Float(
        string='Cantidad retenida de impuesto de IVA', store=True,
        compute='_amount_ret_all',
        help="Calculo del importe de la retención de impuestos")
    fortnight = fields.Selection([
        ('PS', 'Primera Semana'),
        ('SS', 'Segunda Semana'),
        ('TS', 'Tercera Semana'),
        ('CS', 'Cuarta Semana')], string="Semana",
        help="Tipo de Retencion")
    consolidate_vat_wh = fields.Boolean(
        string='Consolidar Semana de Retencion de IVA',
        help='Si se establece, las retenciones se generan en un mismo'
             'se agrupará en un recibo de retención.')
    third_party_id = fields.Many2one(
        'res.partner', string='Socio de terceros',
        help='Socio tercero')
    withholding_rate = fields.Float(compute='_amount_ret_all', store=True)


    @api.depends('wh_lines.amount_tax_ret', 'wh_lines.base_ret')
    def _amount_ret_all(self):
        """ Return withholding amount total each line
        """
        for rec in self:
            self.type = rec.type
            rec.total_tax_ret = 0
            rec.amount_base_ret = 0
            if rec.create_date != False:
                if rec.wh_lines:
                    rec.total_tax_ret = sum(l.amount_tax_ret for l in rec.wh_lines)
                    rec.amount_base_ret = sum(l.base_ret for l in rec.wh_lines)
                    rec.withholding_rate = rec.wh_lines[0].wh_iva_rate
