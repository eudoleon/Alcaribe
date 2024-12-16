# coding: utf-8
import time

from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.addons import decimal_precision as dp


class AccountWhIslrDoc(models.Model):
    _name = "account.wh.islr.doc"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_ret desc, number desc'
    _description = 'Document Income Withholding'
    _rec_name = 'name'
    _check_company_auto = True

    def name_get(self):
        if not len(self.ids):
            return []
        res = []
        for item in self.browse():
            if item.number and item.state == 'done':
                res.append((item.id, '%s (%s)' % (item.number, item.name)))
            else:
                res.append((item.id, '%s' % (item.name)))
        return res

    @api.model
    def _get_type(self):
        """ Return type of invoice or returns in_invoice
        """
        if self._context is None:
            self.context = {}
        inv_type = self._context.get('type', 'in_invoice')
        return inv_type

    '''@api.model
    def _get_journal(self):

        """ Return a iva journal depending of invoice type
        """

        partner_id = self._context.get('uid')
        partner = self.env['res.partner'].search([('id', '=', partner_id)])
        purchase_journal_id = partner.purchase_journal_id.id
        res = self.env['account.journal'].search([('id', '=', purchase_journal_id)])
        return res'''

    @api.model
    def _get_journal(self, partner_id=None):
        # Return a islr journal depending on the type of bill

        # if self._context is None:
        #    self.context = {}
        # journal_obj = self.env['account.journal']
        # user_obj = self.env['res.users']
        # company_id = user_obj.browse(self._uid).company_id.id
        filtro = partner_id
        type = self._context.get('default_type')
        res = []
        if not partner_id:
            # partner_id = self.env['res.partner'].search([('id', '=', self._context.get('uid'))])
            company = self.env.user.sudo().company_id
            filtro = company.partner_id

        if type in ('out_invoice', 'out_refund'):
            res = filtro.sale_islr_journal_id
            # journal_obj.search([('type', '=', 'islr_sale'),
            #                     ('company_id', '=', company_id)], limit=1)
        if type in ('in_invoice', 'in_refund'):
            res = filtro.purchase_islr_journal_id
            # journal_obj.search([(
            # 'type', '=', 'islr_purchase')], limit=1)
        if res:
            return res
        else:
            if type:
                raise UserError(
                    "Configuracion Incompleta. \nNo se encuentra un diario para ejecutar la retención ISLR automáticamente, cree uno en vendedor/proveedor > contabilidad > Diario de retencion ISLR")
                return False
            else:
                res = filtro.purchase_islr_journal_id
                return res

        '''context = dict(self._context or {})
        type_inv = context.get('type', 'in_invoice')
        type2journal = {'out_invoice': 'islr_sale',
                        'in_invoice': 'islr_purchase'}
        journal_obj = self.env['account.journal']
        user = self.env['res.users'].browse()
        company_id = context.get('company_id', user.company_id.id)
        domain = [('company_id', '=', company_id)]
        domain += [('type', '=', type2journal.get(
            type_inv, 'islr_purchase'))]
        res = journal_obj.search(domain, limit=1)
        return res and res[0] or False'''

    @api.model
    def _get_currency(self):
        """ Return the currency of the current company
        """
        user = self.env['res.users'].browse(self._uid)
        if user.company_id:
            return user.company_id.currency_id.id
        else:
            return self.env['res.currency'].search(
                [('rate', '=', 1.0)])[0]

    def _get_amount_total(self):
        """ Return the cumulative amount of each line
        """
        res = {}
        for rete in self.browse():
            res[rete.id] = 0.0
            for line in rete.concept_ids:
                res[rete.id] += line.amount
        return res

    def _get_company(self):
        res_company = self.env['res.company'].search([('id', '=', self.company_id.id)])
        return res_company

    # @api.onchange('date_ret')

    def retencion_seq_get(self):
        # TODO REVISAR ESTA SECUENCIA SALTA UN NUMERO
        local_number = self.env['ir.sequence'].next_by_code('account.wh.islr.doc')
        if local_number and self.date_ret:
            account_month = self.date_ret.split('-')[1]
            if not account_month == local_number[4:6]:
                local_number = local_number[:4] + account_month + local_number[6:]
        return local_number


    amount_total_signed = fields.Many2one('account.move', string='campo')
    desc = fields.Char(
        'Descripcion', size=50,
        help="Descripción del vale")
    name = fields.Char(
        'Numero de Comprobante', size=64,
        required=True,
        help="Número de Comprobante de Retención")
    # code = fields.Char(
    #         string='Codigo', size=32,
    #         default=lambda s: s.retencion_seq_get(),
    #         help="referencia del vale2222")
    number = fields.Char(
        'Número de Retención', size=32, help="referencia del vale")
    number_comprobante = fields.Char(
        'Número de Comprobante de Retención', size=32, help="Número de Comprobante de Retención",tracking=True)

    type = fields.Selection([
        ('out_invoice', 'Factura del cliente'),
        ('in_invoice', 'Factura del proveedor'),
        ('in_refund', 'Reembolso de la factura del proveedor'),
        ('out_refund', 'Reembolso de la factura del cliente'),
    ], string='Tipo', readonly=True,
        default=lambda s: s._get_type(),
        help="Tipo de referencia",tracking=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmado'),
        ('done', 'Realizado'),
        ('cancel', 'Cancelado')
    ], string='Estado', readonly=True, default='draft',
        help="estado del vale",tracking=True)
    date_ret = fields.Date(
        'Fecha de contabilidad', readonly=True,
        states={'draft': [('readonly', False)]},
        help="Mantener vacío para usar la fecha actual")
    date_uid = fields.Date(
        'Fecha de retención', readonly=True,
        states={'draft': [('readonly', False)]}, help="Fecha del vale")
    # period_id = fields.Many2one(
    #        'account.period', 'Period', readonly=True,
    #       states={'draft': [('readonly', False)]},
    #      help="Period when the accounts entries were done")
    account_id = fields.Many2one(
        'account.account', 'Cuenta',  # required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        help="Cuenta por cobrar o cuenta por pagar de socio")
    partner_id = fields.Many2one(
        'res.partner', 'Empresa', readonly=True, required=True,
        states={'draft': [('readonly', False)]},
        help="Socio objeto de retención")
    currency_id = fields.Many2one(
        'res.currency', 'Moneda', required=True, readonly=True,
        states={'draft': [('readonly', False)]},
        default=lambda s: s._get_currency(),
        help="Moneda en la que se realiza la transacción")
    journal_id = fields.Many2one(
        'account.journal', 'Diario', required=True, readonly=True,
        states={'draft': [('readonly', False)]},
        default=lambda s: s._get_journal(),
        help="Diario donde se registran los asientos contables",tracking=True)
    company_id = fields.Many2one(
        'res.company', 'Compañia', required=True, readonly=True, store=True,
        default=lambda s: s._get_company(),
        help="Compañia")
    amount_total_ret = fields.Float(
        compute='_get_amount_total', store=True, string='Monto total',
        digits=(16, 2),
        help="Importe total retenido")
    concept_ids = fields.One2many(
        'account.wh.islr.doc.line', 'islr_wh_doc_id', 'Concepto de retención de ingresos',
        readonly=True, states={'draft': [('readonly', False)]},
        help='Concepto de retención de ingresos')
    invoice_ids = fields.One2many(
        'account.wh.islr.doc.invoices', 'islr_wh_doc_id', 'Facturas retenidas',
        readonly=True, states={'draft': [('readonly', False)]},
        help='Facturas a retener')
    islr_wh_doc_id = fields.One2many(
        'account.move', 'islr_wh_doc_id', 'Facturas',
        states={'draft': [('readonly', False)]},
        help='Se refiere al documento de retención de ingresos del impuesto generado en la factura')
    user_id = fields.Many2one(
        'res.users', 'Salesman', readonly=True,
        states={'draft': [('readonly', False)]},
        default=lambda s: s._uid,
        help="Vendor user")
    automatic_income_wh = fields.Boolean(
        string='Retención Automática de Ingresos',
        default=False,
        help='Cuando todo el proceso se verifique automáticamente, y si todo está bien, se configurará como hecho')

    # invoice_id= fields.Many2one('account.wh.islr.doc.invoices', string='Factura')

    def name_get(self, ):
        res = []
        for item in self:
            if item.number and item.state == 'done':
                res.append((item.id, '%s (%s)' % (item.number, item.name)))
            else:
                res.append((item.id, '%s' % (item.name)))
        return res

    @api.model
    def _check_partner(self):
        """ Determine if a given partner is a Income Withholding Agent
        """
        # context = self._context or {}
        rp_obj = self.env['res.partner']
        # obj = self.browse()
        if self.type in ('out_invoice', 'out_refund') and \
                rp_obj._find_accounting_partner(
                    self.partner_id).islr_withholding_agent:
            return True
        if self.type in ('in_invoice', 'in_refund') and \
                rp_obj._find_accounting_partner(
                    self.company_id.partner_id).islr_withholding_agent:
            return True
        return False

    _constraints = [
        (_check_partner,
         'Error! El socio debe ser un agente de retención de ingresos.',
         ['partner_id']),
    ]

    def check_income_wh(self):
        """ Check invoices to be retained and have
        their fair share of taxes.
        """
        context = self._context or {}
        context = self._context or {}
        ids = isinstance(int) and [self.ids] or self.ids
        obj = self.browse()
        res = {}
        # Checks for available invoices to Withhold
        if not obj.invoice_ids:
            raise UserError(
                "Facturas faltantes !!! \n¡Necesita agregar facturas para retener impuestos sobre la renta!")

        for wh_line in obj.invoice_ids:
            # Checks for xml_id elements when withholding to supplier
            # Otherwise just checks for withholding concepts if any
            if not (wh_line.islr_xml_id or wh_line.iwdl_ids):
                res[wh_line.id] = (wh_line.invoice_id.name,
                                   wh_line.invoice_id.supplier_invoice_number)
        if res:
            note = _('Las siguientes facturas aún no se han retenido:\n\n')
            for i in res:
                note += '* %s, %s, %s\n' % res[i]
            note += _('\n Por favor, cargue los impuestos a retener e intente nuevamente')
            raise UserError("¡Facturas con impuestos retenidos faltantes! \n %s" % (note))
        return True

    def check_auto_wh(self):
        """ Tell us if the process already checked and everything was fine.
        """
        context = self._context or {}
        ids = isinstance(self.ids, (int)) and [self.ids] or self.ids
        obj = self.browse()
        return self.automatic_income_wh or False

    def check_auto_wh_by_type(self):
        """ Tell us if the process already checked and everything was
        fine in case of a in_invoice or in_refund
        """
        context = self._context or {}
        ids = isinstance(self.ids, (int)) and [self.ids] or self.ids
        brw = self.browse()
        if brw.type in ('out_invoice', 'out_refund'):
            return False
        return brw.automatic_income_wh or False

    @api.model
    def compute_amount_wh(self, islr_wh_doc_id):
        """ Calculate the total withholding each invoice
        associated with this document
        """
        context = self._context or {}
        ids = isinstance(islr_wh_doc_id, (int)) and [islr_wh_doc_id] \
              or isinstance(islr_wh_doc_id, (list)) and islr_wh_doc_id \
              or self.ids
        iwdi_obj = self.env['account.wh.islr.doc.invoices']
        iwdl_obj = self.env['account.wh.islr.doc.line']
        # inv_obj = self.env['account.move']
        # inv_brw = inv_obj.browse
        if isinstance(ids[0], int):
            iwd_brw = self.browse(ids)
        else:
            iwd_brw = islr_wh_doc_id[0]
        # if not self.date_uid or inv_obj.date_invoice:
        #    raise UserError(
        #       _('Missing Date !'), _("Please Fill Voucher Date"))

        '''
        period_ids = self.env('account.period').search(
            [('date_start', '<=', iwd_brw.date_uid),
                      ('date_stop', '>=', iwd_brw.date_uid)])

        if len(period_ids):
            period_id = period_ids[0]
        else:
            raise UserError(
                _('Warning !'),
                _("Not found a fiscal period to date: '%s' please check!") % (
                    iwd_brw.date_uid or time.strftime('%Y-%m-%d')))
        iwd_brw.write({'period_id': period_id})
        '''
        # TODO Searching & Unlinking for concept lines from the current withholding
        # iwdl_ids = iwdl_obj.search([('islr_wh_doc_id', '=', islr_wh_doc_id)])
        # if iwdl_ids:
        #    iwdl_ids.unlink()

        for iwdi_brw in iwd_brw.invoice_ids:
            iwdi_brw.load_taxes(iwdi_brw)
            calculated_values = iwdi_obj.get_amount_all(iwdi_brw)
            pruee = calculated_values.get(iwdi_brw.id)
            iwdi_brw.amount_islr_ret = pruee.get('amount_islr_ret')
            iwdi_brw.base_ret = pruee.get('base_ret')
            iwdi_brw.currency_amount_islr_ret = pruee.get('currency_amount_islr_ret')
            iwdi_brw.currency_base_ret = pruee.get('currency_base_ret')
            iwdl_ids = iwdl_obj.search([('islr_wh_doc_id', '=', iwd_brw.id)])
            total_amount = 0.0
            for iwdl_id in iwdl_ids:
                # iwdl_id.amount = calculated_values.get('amount', 0.0)
                total_amount += iwdl_id.amount
            iwd_brw.amount_total_ret = total_amount
        return True

    def validate(self, *args):
        if args[0] in ['in_invoice', 'in_refund'] and args[1] and args[2]:
            return True
        return False

    def action_done(self):
        """ Call the functions in charge of preparing the document
        to pass the state done
        """
        context = self._context or {}
        ids = isinstance(self.ids, (int)) and [self.ids] or self.ids
        self.action_number()
        self.action_move_create()
        self.write({'state': 'done'})
        for a in self.invoice_ids:
            a.invoice_id.status = 'pro'

        # ACTUALIZA EL MONTO EN LA FACTURA
        iwdl = self.env['account.wh.islr.doc.line'].search([('islr_wh_doc_id', '=', self.id)])
        # iwdl.invoice_id.residual = iwdl.invoice_id.residual - self.amount_total_ret
        # iwdl.invoice_id.residual_company_signed = iwdl.invoice_id.residual_company_signed - self.amount_total_ret

        # guarda el l atabla account_invoice el campo islr_wh_doc_id
        # inv_obj = self.env['account.move'].search([('id','=',iwdl.invoice_id.id)])
        # inv_obj.write({'islr_wh_doc_id': self.id})
        # iwdl.invoice_id.islr_wh_doc_id = iwdl.invoice_id.id
        return True

    def action_process(self):
        # TODO: ERASE THE REGARDING NODE IN THE WORKFLOW
        # METHOD HAVE BEEN LEFT FOR BACKWARD COMPATIBILITY
        return True

    def action_cancel_process(self):
        """ Delete all withholding lines and reverses the process of islr
        """
        # if not self._context:
        #    context = {}
        line_obj = self.env['account.wh.islr.doc.line']
        doc_inv_obj = self.env['account.wh.islr.doc.invoices']
        inv_obj = self.env['account.move']
        inv_line_obj = self.env['account.move.line']
        xml_obj = self.env['account.wh.islr.xml.line']
        wh_doc_id = self.ids

        # DELETED XML LINES
        islr_lines = line_obj.search([
            ('islr_wh_doc_id', '=', wh_doc_id)])
        for islr_line in islr_lines:
            xml_lines = islr_line and xml_obj.search(
                [('islr_wh_doc_line_id', 'in', [islr_line.id])])
            if xml_lines:
                xml_lines.unlink()

        wh_line_list = line_obj.search([
            ('islr_wh_doc_id', '=', wh_doc_id)])
        wh_line_list.unlink()

        doc_inv_list = doc_inv_obj.search([
            ('islr_wh_doc_id', '=', wh_doc_id)])
        doc_inv_list.unlink()

        inv_list = inv_obj.search([
            ('islr_wh_doc_id', '=', wh_doc_id)])
        inv_list.write({'status': 'no_pro'})
        inv_list.write({'islr_wh_doc_id': False})

        # inv_line_list = inv_line_obj.search(
        #    [('invoice_id', 'in', inv_list)])
        inv_line_obj.write({'apply_wh': False})

        return True

    @api.onchange('partner_id', 'inv_type')
    def onchange_partner_id(self):
        """ Unlink all taxes when change the partner in the document.
        @param type: invoice type
        @param partner_id: partner id was changed
        """
        context = self._context or {}
        acc_id = False
        res_wh_lines = []
        rp_obj = self.env['res.partner']
        inv_obj = self.env['account.move']

        # Unlink previous iwdi
        iwdi_obj = self.env['account.wh.islr.doc.invoices']
        iwdi_ids = self._ids and iwdi_obj.search(
            [('islr_wh_doc_id', '=', self._ids[0])])
        if iwdi_ids:
            iwdi_ids.unlink()
            self.iwdi_ids = []

        # Unlink previous line
        iwdl_obj = self.env['account.wh.islr.doc.line']
        iwdl_ids = self._ids and iwdl_obj.search(
            [('islr_wh_doc_id', '=', self._ids[0])])
        if iwdl_ids:
            iwdl_ids.unlink()
            self.iwdl_ids = []

        if self.partner_id:
            acc_part_id = rp_obj._find_accounting_partner(rp_obj.browse(
                self.partner_id.id))
            args = [('state', '=', 'open'),
                    ('islr_wh_doc_id', '=', False),
                    '|',
                    ('partner_id', '=', acc_part_id.id),
                    ('partner_id', 'child_of', acc_part_id.id),
                    ]
            if self.type in ('out_invoice', 'out_refund'):
                acc_id = acc_part_id.property_account_receivable_id and \
                         acc_part_id.property_account_receivable_id.id
                args += [('move_type', 'in', ('out_invoice', 'out_refund'))]
            else:
                acc_id = acc_part_id.property_account_payable_id and \
                         acc_part_id.property_account_payable_id.id
                args += [('move_type', 'in', ('in_invoice', 'in_refund'))]

            inv_ids = inv_obj.search(args)
            inv_ids = iwdi_obj._withholdable_invoices(inv_ids)

            for invoice in inv_ids:
                # for inv_brw in inv_obj.browse(inv_ids[0].id):
                res_wh_lines += [{'invoice_id': invoice}]

        # values = {
        #    'account_id': acc_id,
        #    'invoice_ids': res_wh_lines}
        # self.write(values)
        self.account_id = acc_id
        self.invoice_ids = res_wh_lines

    # @api.onchange('date_ret','date_uid')
    # def on_change_date_ret(self):
    #     res = {}
    #     if self.date_ret:
    #         if not self.date_uid:
    #             res.update({'date_uid': self.date_ret})
    #   #      obj_per = self.env('account.period')
    #      #   per_id = obj_per.find( date_ret)
    #      #   res.update({'period_id': per_id and per_id[0]})
    #     return {'value': res}

    @api.model_create_multi
    def create(self, vals):
        """ When you create a new document, this function is responsible
        for generating the sequence code for the field
        """
        if not self._context:
            context = {}
        #   code = self.env['ir.sequence'].get('account.wh.islr.doc')
        # code = vals.get('name', False)
        #       vals[0]['code'] = code
        # name = vals['invoice_ids'][2]['invoice_id']
        # vals['name'] =name

        return super(AccountWhIslrDoc, self).create(vals)

    def action_confirm(self):
        """ This checking if the provider allows retention is
        automatically verified and checked
        """
        context = self._context or {}
        ids = isinstance(self.ids, (int)) and [self.ids] or self.ids
        check_auto_wh = self.browse(
            ids[0]).company_id.automatic_income_wh
        return self.write(
            {'state': 'confirmed', 'automatic_income_wh': check_auto_wh})

    def _get_sequence_code(self):
        # metodo que crea la secuencia del número de control, si no esta creada crea una con el
        # nombre: 'l10n_nro_control

        self.invoice_ids.invoice_id.ensure_one()
        if self.invoice_ids[0].invoice_id.islr_number_asignado:
            return self.invoice_ids[0].invoice_id.islr_number_asignado
        SEQUENCE_CODE = 'account.wh.islr.doc.in_invoice' # if self.type == 'in_invoice' else 'account.wh.islr.doc.in_refund'
        company_id = self._get_company()
        #IrSequence = self.env['ir.sequence'].with_context(force_company=company_id.id)
        IrSequence = self.env['ir.sequence'].with_company(company_id)
        number = IrSequence.next_by_code(SEQUENCE_CODE)
        return number

    def action_number(self, *args):
        """ Is responsible for generating a numero for the document
        if it does not have one
        """
        # context = self._context or {}
        # obj_ret = self.browse()
        if self.type in ['in_invoice','in_refund']:
            if not self.number:
                    number = self._get_sequence_code()
                    if not number:
                        raise UserError(
                            "Error Configuracion \nSin secuencia configurada para retención de ingresos del proveedor")
                    self.write({'number': number})
                    self.invoice_ids[0].invoice_id.write({'islr_number_asignado': number})
        #
        #
        #else:
            # self.env.cr.execute(
            #     'SELECT id, number '
            #     'FROM islr_wh_doc '
            #     'WHERE id IN (' + ','.join([str(item) for item in self.ids]) + ')')

            # if not self.number:
            #     company_id = self._get_company()
            #     number = self.env['ir.sequence'].with_company(company_id).next_by_code('account.wh.islr.doc.%s' % self.type)
            #     if not number:
            #         raise UserError(
            #             "Falta la configuración! \nSin secuencia configurada para ingresos del proveedor Retenciones")
            #     self.write({'number': number})

        return True

    def concilio_saldo_pendiente_isrl(self):
        id_islr=self.id
        tipo_empresa=self.type
        if tipo_empresa=="in_invoice" or tipo_empresa=="in_refund" or tipo_empresa=="in_receipt":#aqui si la empresa es un proveedor
            type_internal="payable"
        if tipo_empresa=="out_invoice" or tipo_empresa=="out_refund" or tipo_empresa=="out_receipt":# aqui si la empresa es cliente
            type_internal="receivable"
        busca_movimientos = self.env['account.move'].search([('isrl_ret_id','=',id_islr)])
        #raise UserError(_('busca_movimientos = %s')%busca_movimientos)
        for det_movimientos in busca_movimientos:
            busca_line_mov = self.env['account.move.line'].search([('move_id','=',det_movimientos.id),('account_internal_type','=',type_internal)])
            if busca_line_mov.credit == 0:
                id_move_debit=busca_line_mov.id
                monto_debit=busca_line_mov.debit
            if busca_line_mov.debit == 0:
                id_move_credit = busca_line_mov.id
                monto_credit = busca_line_mov.credit
        if tipo_empresa == "in_invoice" or tipo_empresa=="out_refund" or tipo_empresa=="in_receipt":
            monto=monto_debit
        if tipo_empresa == "out_invoice" or tipo_empresa=="in_refund" or tipo_empresa=="out_receipt":
            monto=monto_credit
        value = {
             'debit_move_id':id_move_debit,
             'credit_move_id':id_move_credit,
             'amount':monto,
             'debit_amount_currency':monto,
             'credit_amount_currency':monto,
             'max_date':self.date_ret,
        }
        self.env['account.partial.reconcile'].create(value)

    def action_cancel(self):
        """ The operation is canceled and not allows automatic retention
        """
        # context = self._context or {}
        # if self.browse(cr,uid,ids)[0].type=='in_invoice':
        # return True
        self.get_reconciled_move()
        self.cancel_move()
        self.action_cancel_process()

        self.env['account.wh.islr.doc'].write(
            {'state': 'cancel', 'automatic_income_wh': False})
        return True

    def get_reconciled_move(self):
        iwdi_obj = self.env['account.wh.islr.doc.invoices']
        iwdi_brw = iwdi_obj.search([('islr_wh_doc_id', '=', self.id)])

        dominio = [('move_id', '=', iwdi_brw.move_id.id),
                   ('reconciled', '=', True)]
        obj_move_line = self.env['account.move.line'].search(dominio)

        if obj_move_line:
            return True #UserError( "El Comprobante ya tiene una aplicacion en la factura %s, debe desconciliar el comprobante para poder cancelar" % (obj_move_line.move_id.name))
        else:
            return True

    def cancel_move(self):
        """ Retention cancel documents
        """
        iwdi_obj = self.env['account.wh.islr.doc.invoices']
        iwdi_brw = iwdi_obj.search([('islr_wh_doc_id', '=', self.id)])

        for ret in self:
            if ret.state == 'done':
                for ret_line in iwdi_brw.move_id:
                    ret_line.button_draft()
                    ret_line.button_cancel()
                    #ref_move = ret_line._reverse_moves([{'date': self.date_ret
                    #                                     }], True)
                    #ref_move.write({'ref': 'Reversión de ' + str(ret_line.name) + ' para la ' + str(
                    #    self.invoice_ids.invoice_id.display_name)})
            # second, set the withholding as cancelled
            ret.write({'state': 'cancel'})
        return True

        # account_move_obj = self.env['account.move']
        # for ret in self.browse():
        #     if ret.state == 'done':
        #         for ret_line in ret.invoice_ids:
        #             if ret_line.move_id:
        #                 account_move_obj.button_cancel(
        #                      [ret_line.move_id.id])
        #             ret_line.write({'move_id': False})
        #             if ret_line.move_id:
        #                 #account_move_obj.unlink([ret_line.move_id.id])
        #                 ret_line.move_id.unlink()
        # self.write({'state': 'cancel'})
        # return

    def action_cancel_draft(self):
        """ Back to draft status
        """
        ids = isinstance(self.ids, (int)) and [self.ids] or self.ids
        self.write({'state': 'draft'})
        #    for iwd_id in ids:
        # Deleting the existing instance of workflow for islr withholding
        #    self.delete_workflow( [iwd_id])
        #      self.create_workflow( [iwd_id])
        return True

    def action_move_create(self):
        """ Build account moves related to withholding invoice
        """
        context = self._context or {}
        ids = isinstance(self.ids, (int)) and [self.ids] or self.ids
        ixwl_obj = self.env['account.wh.islr.xml.line']
        ret = self.browse(ids)
        self = self.with_context({'income_wh': True})
        acc_id = ret.account_id.id
        acc_id_2 = ret.account_id
        if not ret.date_uid:
            self.write({
                'date_uid': time.strftime('%Y-%m-%d')})

        ret.refresh()
        if ret.type in ('in_invoice', 'in_refund'):
            self.write({
                'date_ret': ret.date_ret})
        else:
            if not ret.date_ret:
                self.write({
                    'date_ret': time.strftime('%Y-%m-%d')})

        # Reload the browse because there have been changes into it
        ret = self.browse(ids)

        #   period_id = ret.period_id and ret.period_id.id or False
        journal_id = ret.journal_id.id

        '''
        if not period_id:
            period_ids = self.env('account.period').search(

                [('date_start', '<=',
                  ret.date_ret or time.strftime('%Y-%m-%d')),
                 ('date_stop', '>=',
                  ret.date_ret or time.strftime('%Y-%m-%d'))])
            if len(period_ids):
                period_id = period_ids[0]
            else:
                raise UserError(
                    _('Warning !'),
                    _("Not found a fiscal period to date: '%s' please check!")
                    % (ret.date_ret or time.strftime('%Y-%m-%d')))
        '''
        ut_obj = self.env['account.ut']
        for line in ret.invoice_ids:
            if ret.type in ('in_invoice', 'in_refund'):
                name = 'COMP. RET. ISLR ' + ret.name + \
                       ' Doc. ' + (line.invoice_id.supplier_invoice_number or '')
            else:
                name = 'COMP. RET. ISLR ' + ret.name + \
                       ' Doc. ' + (line.invoice_id.display_name or '')
            writeoff_account_id = True
            writeoff_journal_id = False
            # amount = line.amount_islr_ret
            amount = self.amount_total_ret
            ret_move = line.invoice_id.ret_and_reconcile(
                amount, acc_id_2, journal_id, writeoff_account_id,
                writeoff_journal_id, ret.date_ret, name,
                line.iwdl_ids, 'wh_islr')

            # if (line.invoice_id.currency_id.id !=
            #         line.invoice_id.company_id.currency_id.id):
            #     f_xc = ut_obj.sxc(
            #         line.invoice_id.company_id.currency_id.id,
            #         line.invoice_id.currency_id.id,
            #         line.islr_wh_doc_id.date_uid)
            #     # move_obj = self.env['account.move']
            #     move_line_obj = self.env['account.move.line']
            #     line_ids = move_line_obj.search([('move_id', '=', ret_move.id)])
            #     for ml in line_ids:
            #         ml.write({'currency_id': line.invoice_id.currency_id.id})
            #         if ml.credit:
            #             ml.write({'amount_currency': f_xc(ml.credit) * -1})
            #         elif ml.debit:
            #             ml.write({'amount_currency': f_xc(ml.debit)})
            # ret_move.post()
            # make the withholding line point to that move
            # rl = {
            #    'move_id': ret_move['move_id'],
            # }
            # lines = [(op,id,values)] #escribir en un one2many
            # lines = [(1, line.id, rl)]
            self.write({
                'invoice_ids': line})
        xml_ids_obj = self.env['account.wh.islr.xml.line']
        for line in ret.concept_ids:
            # xml_ids_obj += [xml.id for xml in line.xml_ids]
            xml_ids_obj = xml_ids_obj.search([('islr_wh_doc_line_id', '=', line.id)])
            # xml_ids_obj.write({'date_ret': time.strftime('%Y-%m-%d')})
            xml_ids_obj.write({'date_ret': self.date_ret})

        # self.write( ids, {'period_id': period_id}, context=context)
        # guarda en el la tabla account.wh.islr.doc.invoices
        iwdi_obj = self.env['account.wh.islr.doc.invoices'].search([('islr_wh_doc_id', '=', self.id)])
        if not iwdi_obj:
            raise UserError("Advertencia! \nPor favor recuerde seleccionar las facturas a retener")
        iwdi_obj.write({'move_id': ret_move.id})

        return {'move_id': ret_move}

    def wh_and_reconcile(self, invoice_id, pay_amount,
                         pay_account_id, pay_journal_id,
                         writeoff_acc_id,
                         writeoff_journal_id, name=''):
        """ retain, reconcile and create corresponding journal items
        @param invoice_id: invoice to retain and reconcile
        @param pay_amount: amount payable on the invoice
        @param pay_account_id: payment account
        @param period_id: period for the journal items
        @param pay_journal_id: payment journal
        @param writeoff_acc_id: account for reconciliation
        @param writeoff_period_id: period for reconciliation
        @param writeoff_journal_id: journal for reconciliation
        @param name: withholding voucher name
        """
        inv_obj = self.env['account.move']
        rp_obj = self.env['res.partner']
        ret = self.browse()[0]
        if self._context is None:
            context = {}
        # TODO check if we can use different period for payment and the
        # writeoff line
        # assert len(invoice_ids)==1, "Can only pay one invoice at a time"
        invoice = inv_obj.browse(invoice_id)
        acc_part_id = rp_obj._find_accounting_partner(invoice.partner_id)
        src_account_id = invoice.account_id.id
        # Take the seq as name for move
        types = {'out_invoice': -1, 'in_invoice':
            1, 'out_refund': 1, 'in_refund': -1, 'entry': 1}
        direction = types[invoice.type]

        date = ret.date_ret

        l1 = {
            'debit': direction * pay_amount > 0 and direction * pay_amount,
            'credit': direction * pay_amount < 0 and - direction * pay_amount,
            'account_id': src_account_id,
            'partner_id': acc_part_id.id,
            'ref': invoice.number,
            'date': date,
            'currency_id': False,
        }
        l2 = {
            'debit': direction * pay_amount < 0 and - direction * pay_amount,
            'credit': direction * pay_amount > 0 and direction * pay_amount,
            'account_id': pay_account_id,
            'partner_id': acc_part_id.id,
            'ref': invoice.number,
            'date': date,
            'currency_id': False,
        }
        if not name:
            if invoice.type in ['in_invoice', 'in_refund']:
                name = 'COMP. RET. ISLR ' + ret.number + \
                       ' Doc. ' + (invoice.supplier_invoice_number or '')
            else:
                name = 'COMP. RET. ISLR ' + ret.number + \
                       ' Doc. ' + (invoice.number or '')

        l1['name'] = name
        l2['name'] = name

        lines = [(0, 0, l1), (0, 0, l2)]
        move = {'ref': invoice.number,
                'line_ids': lines,
                'journal_id': pay_journal_id,
                'date': date}
        move_id = self.env['account.move'].create(move)

        self.env['account.move'].post([move_id])

        line_ids = []
        total = 0.0
        line = self.env['account.move.line']
        self.env.cr.execute('select id from account_move_line where move_id in (' + str(
            move_id) + ',' + str(invoice.move_id.id) + ')')
        lines = line.browse([item[0] for item in self._cr.fetchall()])
        for aml_brw in lines + invoice.payment_ids:
            if aml_brw.account_id.id == src_account_id:
                line_ids.append(aml_brw.id)
                total += (aml_brw.debit or 0.0) - (aml_brw.credit or 0.0)
        if ((not round(total, self.env['decimal.precision'].precision_get(
                'Withhold ISLR'))) or writeoff_acc_id):
            self.env['account.move.line'].reconcile(
                line_ids, 'manual', writeoff_acc_id,
                writeoff_journal_id, )
        else:
            self.env['account.move.line'].reconcile_partial(
                line_ids, 'manual')

        # Update the stored value (fields.function), so we write to trigger
        # recompute
        self.env['account.move'].write(
            {})

    def unlink(self):
        """ Overwrite the unlink method to throw an exception if the
        withholding is not in cancel state."""
        context = self._context or {}
        for islr_brw in self:
            if islr_brw.state != 'cancel':
                raise UserError(
                    "Procedimiento inválido !! \nEl documento de retención debe estar en estado Cancelado para ser eliminado")
        return super(AccountWhIslrDoc, self).unlink()

    def _dummy_cancel_check(self):
        '''
        This will be the method that another developer should use to create new
        check on Withholding Document
        Make super to this method and create your own cases
        '''
        return True

    def _check_xml_wh_lines(self):
        """Check if this ISLR WH DOC is being used in a XML ISLR DOC"""
        context = self._context or {}
        ids = isinstance(self.ids, (int)) and [self.ids] or self.ids
        ixwd_ids = []
        ixwd_obj = self.env['account.wh.islr.xml']
        for iwd_brw in self.browse(ids):
            for iwdi_brw in iwd_brw.invoice_ids:
                for ixwl_brw in iwdi_brw.islr_xml_id:
                    if (ixwl_brw.islr_xml_wh_doc and
                            ixwl_brw.islr_xml_wh_doc.state != 'draft'):
                        ixwd_ids += [ixwl_brw.islr_xml_wh_doc.id]

        if not ixwd_ids:
            return True

        note = _('El siguiente ISLR XML DOC debe establecerse en Borrador antes de '
                 'Cancelar este documento\n\n')
        for ixwd_brw in ixwd_obj.browse(ixwd_ids):
            note += '%s\n' % ixwd_brw.name
        raise UserError("Procedimiento inválido !! \n %s" % (note))

    def cancel_check(self):
        '''
        Unique method to check if we can cancel the Withholding Document
        '''
        context = self._context or {}
        ids = isinstance(self.ids, (int)) and [self.ids] or self.ids

        if not self._check_xml_wh_lines():
            return False
        if not self._dummy_cancel_check():
            return False
        return True

class IslrWhHistoricalData(models.Model):
    _name = "account.wh.islr.historical.data"
    _description = 'Lines of Document Income Withholding'


    partner_id = fields.Many2one(
            'res.partner', 'Partner', readonly=False, required=True,
            help="Partner for this historical data")
    # fiscalyear_id = fields.Many2one(
    #         'account.fiscalyear', 'Fiscal Year', readonly=False, required=True,
    #         help="Fiscal Year to applicable to this cumulation")
    concept_id = fields.Many2one(
            'account.wh.islr.concept', 'Entrada de diario', required=True,
            help="Concepto de retención asociado a estos datos históricos")
    raw_base_ut = fields.Float(
            'Cantidad acumulada de UT', required=True,
            digits=(16, 2),
            help="Cantidad de UT")
    raw_tax_ut = fields.Float(
            'Impuesto retenido de UT acumulado', required=True,
            digits=(16, 2),
            help="Impuesto retenido de UT")