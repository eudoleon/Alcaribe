from odoo import models, fields, api, _, exceptions
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero, float_compare
from datetime import date
import logging
_logger = logging.getLogger(__name__)
import psycopg2

MAP_INVOICE_TYPE_PAYMENT_SIGN = {
    'out_invoice': 1,
    'in_refund': 1,
    'in_invoice': -1,
    'out_refund': -1,
    'entry': 1,
}
class AccountPayment(models.Model):
    _name = 'vendor.vendor'

    payment = fields.Many2one('account.payment.ce')
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Proveedore",
        store=True, readonly=False, ondelete='restrict',
        domain="[('parent_id','=', False)]")
    vendor_due_amt = fields.Float(compute="depends_partner_id",  string="Total a Pagar", store=True)
    vendor_due_amt_vencida = fields.Float(compute="depends_partner_id", string="Total Vencida", store=True)
    amount_sugerido = fields.Float("Monto Sugerido")
    amount = fields.Float("Monto a pagar")
    nota = fields.Char("Notas")

    @api.onchange('amount_sugerido')
    def _onchange_amount_sugerido(self):
        for record in self:
            record.amount = record.amount_sugerido

    @api.depends('partner_id',)
    def depends_partner_id(self):
        supplier_amount_due = 0.0
        vendor_due_amt_ven = 0.0
        for record in self:
            for partner in record.partner_id:
                today = date.today()
                supplier_amount_due = 0.0
                vendor_due_amt_ven = 0.0
                vendor_due_amt_ven = abs(sum([i.amount_residual for i in self.env['account.move.line'].search([('partner_id','=',partner.id),
                                                    ('date_maturity','<',record.payment.date),
                                                    ('company_id','=',record.payment.company_id.id),
                                                    ('move_id.move_type', 'in', ['in_invoice', 'in_refund']),
                                                    ('move_id.state', '=', 'posted'),
                                                    ]) ]))
                record.update({
                    'vendor_due_amt_vencida': vendor_due_amt_ven
                })


class AccountPayment(models.Model):
    _name = 'account.payment.ce'
    _description = "Generacion de Egresos Masivos"
    _order = "date desc, name desc"
    _check_company_auto = True
    _inherit = ['mail.thread', 'mail.activity.mixin']   
    
    @api.depends('payment_lines.invoice_id')
    def _compute_domain_move_line(self):
        for pay in self:
            invoices = pay.mapped('payment_lines.invoice_id')
            pay.domain_move_lines = [(6,0,invoices.ids)]

    @api.depends('payment_line_ids.move_line_id')
    def _compute_domain_accountmove_line(self):
        for pay in self:
            invoices = pay.mapped('payment_line_ids.move_line_id')
            pay.domain_account_move_lines = [(6,0,invoices.ids)]
    def _get_default_journal(self):
        ''' Retrieve the default journal for the account.payment.
        /!\ This method will not override the method in 'account.move' because the ORM
        doesn't allow overriding methods using _inherits. Then, this method will be called
        manually in 'create' and 'new'.
        :return: An account.journal record.
        '''
        return self.env['account.move']._search_default_journal(('bank', 'cash'))

    name = fields.Char(string='Number', default="/", compute="_compute_name", copy=False,  readonly=False, store=True, index=True, tracking=True)
    payment_line_ids = fields.One2many('account.payment.detail.massive', 'payment_id', copy=False,
        string="Detalle de pago", help="detalle de pago")
    payment_lines = fields.One2many('account.payment.detail.massive', 'payment_id', copy=False,
        domain=[('exclude_from_payment_detail', '=', False)], string="Documentos", help="detalle de pago y/o cobro")
    vendor_ids = fields.One2many('vendor.vendor', 'payment',
        string='Cuenta de origen', 
        store=True, readonly=False,)
    state = fields.Selection(selection=[
            ('draft', 'Draft'),
            #('pre_aprobado', 'Contabilidad Aprobado'),
            ('pre-posted', 'Solicitar Aprobacion'),
            ('aprobado', 'Aprobado'),
            #('pre-posted2', 'Pre-Contabilizacion'),
            ('posted', 'Contabilizado'),
            ('cancel', 'Cancelled'),
        ], string='Status', required=True, readonly=True, copy=False, tracking=True,
        default='draft')
    # fields account origin and destination
    account_id = fields.Many2one('account.account', string='Cuenta de origen')
    account_ids = fields.Many2many(
        comodel_name='account.account',
        string='Cuenta de origen',
        store=True, readonly=False,
        #compute='_compute_destination_account_id',
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
        check_company=True)
    destination_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Destination Account',
        store=True, readonly=False,
        #compute='_compute_destination_account_id',
        domain="[('account_type', 'in', ('asset_receivable', 'liability_payable')), ('company_id', '=', company_id)]",
        check_company=True)
    change_destination_account = fields.Char(string="cambio de cuenta destino")

    company_currency_id = fields.Many2one('res.currency', string="Moneda de la compañia",
        required=True, default=lambda self: self.env.company.currency_id)

    account_move_payment_ids = fields.Many2many("account.move.line", "account_move_payment_ce_rel", 'moe_line_id','payment_id',
        string="Buscar Otros Documentos", domain="[('parent_state','!=','draft'),('account_id.account_type', '=','liability_payable')]")
    invoice_id = fields.Many2one(
        comodel_name='account.move',
        string='Factura',
        required=False)
    processed  = fields.Boolean(
        string='Procesado',
        required=False)
    date = fields.Date(
        string='Date',
        required=True,
        index=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        copy=False,
        default=fields.Date.context_today
    )
    domain_account_move_lines = fields.Many2many("account.move.line", 'domain_account_move_line_ces_rel', string="restriccion de campos", compute="_compute_domain_accountmove_line")
    domain_move_lines = fields.Many2many("account.move", 'domain_move_line_pay_rel', string="restriccion de campos", compute="_compute_domain_move_line")
    payment_difference_line = fields.Monetary(string="Diferencia de pago",
        store=True, readonly=True,  tracking=True)
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, readonly=True,
        states={'draft': [('readonly', False)]},
        check_company=True)
    company_id = fields.Many2one(comodel_name='res.company', string='Company', store=True, readonly=True, compute='_compute_company_id')
    payment_type = fields.Selection([
        ('outbound', 'Send Money'),
        ('inbound', 'Receive Money'),
    ], string='Payment Type', default='outbound', required=True)
    partner_type = fields.Selection([
        ('customer', 'Customer'),
        ('supplier', 'Vendor'),
    ], default='supplier', tracking=True, required=True)
    payment_reference = fields.Char(string="Payment Reference", copy=False,
        help="Reference of the document used to issue this payment. Eg. check number, file name, etc.")
    currency_id = fields.Many2one('res.currency', string='Currency', store=True, readonly=False,
        compute='_compute_currency_id',
        help="The payment's currency.")
    partner_id = fields.Many2many(
        comodel_name='res.partner',
        string="Proveedore",
        store=True, readonly=False, ondelete='restrict',
        domain="[('parent_id','=', False)]",check_company=True)
    amount = fields.Monetary(currency_field='currency_id')
    payment_date = fields.Date(string='Fecha de Pago', required=True, default=fields.Date.today(),tracking=True)
    partner_bank_id = fields.Many2one('res.partner.bank', string='Recipient Bank',
        help='Bank Account Number to which the invoice will be paid. A Company bank account if this is a Customer Invoice or Vendor Credit Note, otherwise a Partner bank account number.',
        check_company=True)
    application = fields.Selection([('I', 'Inmediata'),
                                        ('M', 'Medio día'),
                                        ('N', 'Noche')                                      
                                    ], string='Aplicación', required=True, default='I')
    sequence = fields.Char(string='Secuencia de envío', size=2, default='10', required=True)
    account_debit = fields.Char(string='Nro. Cuenta a debitar', store=True, readonly=True, related='journal_id.bank_account_id.acc_number', change_default=True)
    description = fields.Char(string='Descripción del pago', required=True)

    excel_file = fields.Binary('Excel file')
    excel_file_name = fields.Char('Excel name', size=64)

    txt_file = fields.Binary('TXT file')
    txt_file_name = fields.Char('TXT name', size=64)
    payment_ids = fields.One2many('account.payment', 'ce_origin', string="Egresos Generados",copy=False, store=True)
    payment_type_bnk = fields.Selection([('220', 'Pago a Proveedores'),
                                    ('225', 'Pago de Nómina'),
                                    ('238', 'Pagos a Terceros'),], string='Tipo de pago', required=True, default='220')
    line_count = fields.Integer(string="Purchase Request Line count", compute="_compute_line_count", readonly=True,)
    date_start = fields.Date(string='Fecha de Inicial', default=fields.Date.today(), tracking=True)
    date_end = fields.Date(string='Fecha de Final', required=True, default=fields.Date.today(), tracking=True)
    pre_aprobado = fields.Many2many(
        comodel_name="res.users",
        string="Aprobador",
        tracking=True,
        #default=lambda self: self.env.ref('pago_masivo_bancos_ce.group_treasury_aprobador_account').sudo().users.ids,
        index=True,
    )
    assigned_to = fields.Many2one(
        comodel_name="res.users",
        string="Aprobador",
        tracking=True,
        index=True,
    )
    assigned_contabilizar = fields.Many2one(
        comodel_name="res.users",
        string="Contabilizador",
        tracking=True,
        index=True,
    )
    balance_bank = fields.Monetary(currency_field='currency_id', string="Salo Actual de Banco", store=True, copy=False)
    category_vendor_id = fields.Many2many('res.partner.category')
    payment_method_line_id = fields.Many2one('account.payment.method.line', string='Payment Method',
            readonly=False, store=True, copy=False,
            compute='_compute_payment_method_line_id',
            domain="[('id', 'in', available_payment_method_line_ids)]",
            help="Manual: Pay or Get paid by any method outside of Odoo.\n"
            "Payment Acquirers: Each payment acquirer has its own Payment Method. Request a transaction on/to a card thanks to a payment token saved by the partner when buying or subscribing online.\n"
            "Check: Pay bills by check and print it from Odoo.\n"
            "Batch Deposit: Collect several customer checks at once generating and submitting a batch deposit to your bank. Module account_batch_payment is necessary.\n"
            "SEPA Credit Transfer: Pay in the SEPA zone by submitting a SEPA Credit Transfer file to your bank. Module account_sepa is necessary.\n"
            "SEPA Direct Debit: Get paid in the SEPA zone thanks to a mandate your partner will have granted to you. Module account_sepa is necessary.\n")
    available_payment_method_line_ids = fields.Many2many('account.payment.method.line',
        compute='_compute_payment_method_line_fields')
    hide_payment_method_line = fields.Boolean(
        compute='_compute_payment_method_line_fields',
        help="Technical field used to hide the payment method if the selected journal has only one available which is 'manual'")
    payment_method_id = fields.Many2one(
        related='payment_method_line_id.payment_method_id',
        string="Method",
        tracking=True,
        store=True
    )
    @api.depends('available_payment_method_line_ids')
    def _compute_payment_method_line_id(self):
        ''' Compute the 'payment_method_line_id' field.
        This field is not computed in '_compute_payment_method_line_fields' because it's a stored editable one.
        '''
        for pay in self:
            available_payment_method_lines = pay.available_payment_method_line_ids

            # Select the first available one by default.
            if pay.payment_method_line_id in available_payment_method_lines:
                pay.payment_method_line_id = pay.payment_method_line_id
            elif available_payment_method_lines:
                pay.payment_method_line_id = available_payment_method_lines[0]._origin
            else:
                pay.payment_method_line_id = False

    @api.depends('payment_type', 'journal_id', 'currency_id')
    def _compute_payment_method_line_fields(self):
        for pay in self:
            pay.available_payment_method_line_ids = pay.journal_id._get_available_payment_method_lines(pay.payment_type)
            to_exclude = pay._get_payment_method_codes_to_exclude()
            if to_exclude:
                pay.available_payment_method_line_ids = pay.available_payment_method_line_ids.filtered(lambda x: x.code not in to_exclude)
            if pay.payment_method_line_id.id not in pay.available_payment_method_line_ids.ids:
                # In some cases, we could be linked to a payment method line that has been unlinked from the journal.
                # In such cases, we want to show it on the payment.
                pay.hide_payment_method_line = False
            else:
                pay.hide_payment_method_line = len(pay.available_payment_method_line_ids) == 1 and pay.available_payment_method_line_ids.code == 'manual'

    def _get_payment_method_codes_to_exclude(self):
        # can be overriden to exclude payment methods based on the payment characteristics
        self.ensure_one()
        return []

    # @api.constrains('amount', 'journal_id')
    # def _check_amount(self):
    #     for rec in self:
    #         if rec.amount > rec.balance_bank:
    #             raise exceptions.ValidationError('No se puede pagar más de lo que hay en la cuenta bancaria')

    @api.onchange('journal_id')
    def _onchange_journal_id_2(self):
        for record in self:
            record.partner_bank_id = record.journal_id.bank_account_id.id or False
            record.balance_bank    = sum([i.balance for i in record.env['account.move.line'].search([('company_id','=',record.company_id.id),
                                                    ('date','<=',record.date),
                                                    ('account_id', '=', record.journal_id.default_account_id.id),
                                                    ('move_id.state', '=', 'posted'),
                                                    ]) ])
            record.account_type_debit = record.journal_id.account_type_debit or False
            record.format_file = record.journal_id.format_file or False
            record.type_file = record.journal_id.type_file or False


    def _get_partners_with_accounts_payable(self):
        query = """SELECT res_partner.id
            FROM res_partner
            JOIN account_move_line ON account_move_line.partner_id = res_partner.id
            JOIN account_account ON ( account_account.id = account_move_line.account_id AND account_account.account_type = 'liability_payable')
            JOIN account_move ON ( account_move.id = account_move_line.move_id AND account_move.move_type IN ('in_invoice', 'in_refund'))
            WHERE account_move_line.company_id = %s
            GROUP BY res_partner.id
            HAVING sum(account_move_line.amount_residual) != 0;
        """ % (self.company_id.id)
        self.env.cr.execute(query)
        results = self.env.cr.fetchall()
        return results

    def button_change_proveedores(self):
        self.vendor_ids = [(5,0,0)]
        partner =  self.env['res.partner']
        for record in self:
            results = self._get_partners_with_accounts_payable()
            partner_ids = []
            for result in results:
                domain = [
                    ('id','=', result[0] )]
                if record.category_vendor_id:
                    domain.append(('category_id','not in', record.category_vendor_id.ids))
                partners = partner.search(domain)
                if partners:
                    partner_ids.append((0,0,{'partner_id' : partners.id}))
            if partner_ids:
                self.vendor_ids = partner_ids
                self.delete_lines_qty_zero()

    def action_delete_counterpart_lines(self):
        if self.payment_lines and self.state == "draft":
            self.payment_lines = [(5, 0, 0)]
            for rec in self.payment_ids:
                rec.action_draft()
            self._cr.execute("DELETE FROM accocunt_payment WHERE ce_origin = %s", (self.id,))


    def delete_lines_qty_zero(self):
        lines = self.env['vendor.vendor'].search([
            ('payment', '=', self.id),
            ('vendor_due_amt', '=', 0)])
        lines.unlink()
        return True 
        
    def delete_lines_qty_zero_amount(self):
        for record in self:
            for line in record.vendor_ids:
                if line.amount == 0:
                    line.unlink()
        return True

    @api.depends('state', 'journal_id', 'date','vendor_ids')
    def _compute_name(self):
        self.ensure_one()
        company = self.company_id.id or self.env.company.id
        SEQUENCE_CODE = 'programacion_de_pagos'
        ctx = dict(self._context, company_id=company)
        IrSequence = self.env['ir.sequence'].with_context(ctx)
        numero = IrSequence.next_by_code(SEQUENCE_CODE)
        # si aún no existe una secuencia para esta empresa, cree una
        if not numero:
            IrSequence.sudo().create({
                'prefix': 'PRO',
                'name': 'Programacion De Pagos CE %s' % 1,
                'code': SEQUENCE_CODE,
                'implementation': 'no_gap',
                'padding': 8,
                'number_increment': 1,
                'company_id': company,
            })
            numero = IrSequence.next_by_code(SEQUENCE_CODE)
        for rec in self:
            if rec.name == '/':
                rec.name = numero


    def genera_mov(self):
        self.payment_lines = [(5,0,0)]
        self._generate_aml()

    def _generate_aml(self):
        domain = [
                #('date','>=',self.date_start),
                ('date','<=',self.date_end),
                ('account_id.account_type', '=', 'liability_payable'),
                ('amount_residual', '!=', 0 ),
                ('move_id.state','=', 'posted')]
        partners = {}
        partner_ids = []
        for v in self.vendor_ids:
            partners.setdefault(v.partner_id.id, 0.0)
            partners[v.partner_id.id] += v.amount
            partner_ids.append(v.partner_id.id)
        if self.vendor_ids:
            domain.append(('partner_id','in', partner_ids))
        if self.account_ids:
            domain.append(('account_id','in', self.account_ids.ids))
        moves = self.env['account.move.line'].search(domain, order="partner_id, date asc")
        self.with_context(button=True, vendors=partners)._change_and_add_payment_detail(moves)

        
    def post_payment(self):
        for rec in self:
            if not rec.payment_ids:
                raise UserError('No hay Pagos para Publicar')
            for line in rec.payment_ids:
                
                line.action_post()
                rec.write({
                'state': 'posted',
                            })

    def cancel_payment(self):
        for rec in self:
            for line in rec.payment_ids:
                line.action_cancel()
                rec.write({
                'state': 'cancel',
                            })

    def pre_approved(self):
        for rec in self:
            rec.write({'state': 'pre-posted',})
            rec._purchase_request_confirm_message_content_app()
            rec.message_1()
            rec.activity_update()

    def pre_approved_2(self):
        for rec in self:
            rec.write({'state': 'aprobado',})
            rec.message_2()
            rec.activity_update()

    @api.model
    def _get_partner_id(self):
        for request in self:
            user = self.env.user
            for user_app in user:
                user_id = self.env['res.users'].search([['id', '=', user_app.id]])
                user_id = request.assigned_to[0] or self.env.user
            return user_id.partner_id.id

    @api.model
    def _get_partner_conta_id(self,):
        for request in self:
            user_id = request.assigned_contabilizar or self.env.user
            return user_id.partner_id.id
                            
    def message_1(self):
        for request in self:
            user = self.env.user
            if user:
                for user_app in user:
                        user_id = self.env['res.users'].search([['id', '=', user_app.id]])
                        partner_id = user_id.partner_id.id
                        request.message_subscribe(partner_ids=[partner_id])
            
    def message_2(self):
        for request in self:
            if request.assigned_contabilizar:
                partner_id = self._get_partner_conta_id()
                request.message_subscribe(partner_ids=[partner_id])
    
    def pre_aprobador(self):
        for rec in self:
            rec._purchase_request_confirm_message()
            #rec.write({
            #    'state': 'pre_aprobado'})    

    def pre_aprobador_rfc(self):
        for rec in self:
            #rec._purchase_request_confirm_message()
            rec.write({
                'state': 'pre_aprobado',
                            })

    def Aprobador_rfc(self):
        for rec in self:
            #rec._purchase_request_confirm_message()
            rec.write({
                'state': 'aprobado',
                            })

    def restart_payment(self):
        for rec in self:
            for line in rec.payment_ids:
                line.action_draft()
                rec.write({
                'state': 'draft',
                            })

    def activity_update(self):
        to_clean, to_do = self.env['account.payment.ce'], self.env['account.payment.ce']
        for payment in self:
            note = _(
                'Una nueva programacion de pago %(payment_type)s Fue creada por %(user)s, Revisar y aprobar',
                payment_type=payment.journal_id.name,
                user=payment.create_uid.name,
            )
            note_2 = _(
                'Una nueva programacion de pago %(payment_type)s Fue creada por %(user)s, Contabilizar',
                payment_type=payment.journal_id.name,
                user=payment.create_uid.name,
            )
            if payment.state == 'draft':
                to_clean |= payment
            elif payment.state == 'pre-posted':
                payment.activity_schedule(
                    'account_payment_ce.mail_act_payment_approval',
                    note=note,
                    user_id=payment.assigned_to.id or self.env.user.id)
            elif payment.state == 'pre-posted2':
                payment.activity_schedule(
                    'account_payment_ce.mail_act_payment_approval_2',
                    note=note_2,
                    user_id=payment.assigned_contabilizar.id or self.env.user.id)
            elif payment.state == 'posted':
                to_do |= payment
        if to_clean:
            to_clean.activity_unlink(['account_payment_ce.mail_act_payment_approval','account_payment_ce.mail_act_payment_approval_2'])
        if to_do:
            to_do.activity_feedback(['account_payment_ce.mail_act_payment_approval','account_payment_ce.mail_act_payment_approval_2'])

    def _purchase_request_confirm_message_content_app(self, request_dict=None):
        self.ensure_one()
        if not request_dict:
            request_dict = {}
        title = _("Solicitud de programacion de pagos %s") % (self.name)
        message = "<h3>%s</h3><ul>" % title
        message += _(
            "Los siguientes proveedores estan para programacion de pagos en la solicitud %s "
        ) % (self.name)

        for line in self.vendor_ids:
            message += _(
                "<li><b>%s</b>:   Monto sugerido %s    , Monto de Pago %s   , Fecha %s</li>"
            ) % (
                    line.partner_id.name,
                    line.amount_sugerido,
                    line.amount,
                    self.date,
            )
        aprobadores = self.env.user #self.env.ref('pago_masivo_bancos_ce.group_treasury_manager_aprobador')
        email = self.env.user.email
        message += "</ul>"
        email_vals = {}
        email_vals.update({'subject': title.encode('utf-8'),
                                    'email_to': email,
                                    'email_from': self.env.user.email, 
                                    'body_html':message.encode('utf-8'),
                                    'model' : 'account.payment.ce',
                                    'res_id': self.id})
                # create and send email
        if email_vals:
            email_id = self.env['mail.mail'].create(email_vals)
            if email_id:
                email_id.send()   
        return message


    def _purchase_request_confirm_message_content(self, request_dict=None):
        self.ensure_one()
        if not request_dict:
            request_dict = {}
        title = _("Solicitud de programacion de pagos %s") % (self.name)
        message = "<h3>%s</h3><ul>" % title
        message += _(
            "Los siguientes proveedores estan para programacion de pagos en la solicitud %s "
        ) % (self.name)

        for line in self.vendor_ids:
            message += _(
                "<li><b>%s</b>:   Monto sugerido %s     Monto de Pago %s, Fecha %s</li>"
            ) % (
                    line.partner_id.name,
                    line.amount_sugerido,
                    line.amount,
                     self.date,
            )
        aprobadores = self.env.user # self.env.ref('pago_masivo_bancos_ce.group_treasury_aprobador_account')
        users = aprobadores.users
        email = ", ".join(user.email for user in users)
        message += "</ul>"
        email_vals = {}
        email_vals.update({'subject': title.encode('utf-8'),
                                    'email_to': email,
                                    'email_from': self.env.user.email, 
                                    'body_html':message.encode('utf-8'),
                                    'model' : 'account.payment.ce',
                                    'res_id': self.id})
                # create and send email
        if email_vals:
            email_id = self.env['mail.mail'].create(email_vals)
            if email_id:
                email_id.send()   
        return message

    def _purchase_request_confirm_message(self):
        payment_obj = self.env["account.payment.ce"]
        for po in self:
            payment_dict = {}
            for line in po.vendor_ids:
                date_planned = "%s" % po.date
                data = {
                        "name": line.partner_id.name,
                        "amount_sugerido": line.amount_sugerido,
                        "amount": line.amount,
                        "date_planned": date_planned,
                    }
                    #payment_dict[request_id][request_line.id] = data
                payment_dict["result"] = data
            for request_id in payment_dict:
                message = po._purchase_request_confirm_message_content(payment_dict)
                po.message_post(body=message,
                subtype_id=self.env.ref("mail.mt_comment").id)
        return True

    def action_view_purchase_request_line(self):
        xmlid = "pago_masivo_bancos_ce.account_payment_detail_massive_action"
        action = self.env["ir.actions.act_window"]._for_xml_id(xmlid)
        lines = self.mapped("payment_lines")
        if len(lines) > 1:
            action["domain"] = [("id", "in", lines.ids)]
        elif lines:
            action["views"] = [
                (self.env.ref("pago_masivo_bancos_ce.account_payment_detail_massive_form").id, "form")
            ]
            action["res_id"] = lines.ids[0]
        return action

    def action_view_purchase_ce_line(self):
        xmlid = "pago_masivo_bancos_ce.account_payment_detail_massive_action_payment"
        action = self.env["ir.actions.act_window"]._for_xml_id(xmlid)
        lines = self.mapped("payment_ids")
        if len(lines) > 1:
            action["domain"] = [("id", "in", lines.ids)]
        elif lines:
            action["views"] = [
                (self.env.ref("account.view_account_payment_form").id, "form")
            ]
            action["res_id"] = lines.ids[0]
        return action


    @api.depends('journal_id')
    def _compute_company_id(self):
        for move in self:
            move.company_id = move.journal_id.company_id or move.company_id or self.env.company

    @api.depends("payment_lines")
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.mapped("payment_lines"))

    @api.depends('journal_id')
    def _compute_currency_id(self):
        for pay in self:
            pay.currency_id = pay.journal_id.currency_id or pay.journal_id.company_id.currency_id

    @api.onchange('payment_line_ids','payment_line_ids.tax_ids','payment_lines','payment_lines.tax_ids')
    def _onchange_matched_manual_ids(self, force_update = False):
        in_draft_mode = self != self._origin
        
        def need_update():
            amount = 0
            for line in self.payment_line_ids:
                if line.auto_tax_line:
                    amount -= line.balance
                    continue
                if line.tax_ids:
                    balance_taxes_res = line.tax_ids._origin.compute_all(
                        line.invoice_id.amount_untaxed  or line.payment_amount or line.balance,
                        currency=line.currency_id,
                        quantity=1,
                        product=line.product_id,
                        partner=line.partner_id,
                        is_refund=False,
                        handle_price_include=True,
                    )
                    for tax_res in balance_taxes_res.get("taxes"):
                        amount += tax_res['amount']
            return amount 
        
        if not force_update and not need_update():
            return
        
        to_remove = self.env['account.payment.detail.massive']        
        if self.payment_line_ids:
            for line in list(self.payment_line_ids):
                print(line, line.auto_tax_line)
                if line.auto_tax_line:
                    to_remove += line
                    continue
                if line.tax_ids:
                    balance_taxes_res = line.tax_ids._origin.compute_all(
                        line.invoice_id.amount_untaxed or line.payment_amount or line.balance,
                        currency=line.currency_id,
                        quantity=1,
                        product=line.product_id,
                        partner=line.partner_id,
                        is_refund=False,
                        handle_price_include=True,
                    )
                    for tax_res in balance_taxes_res.get("taxes"):
                        create_method = in_draft_mode and line.new or line.create
                        create_method({
                            'payment_id' : self.id,
                            'partner_id' : line.partner_id.id,
                            'account_id' : tax_res['account_id'],
                            'name' : tax_res['name'],
                            'payment_amount' : tax_res['amount'],
                            'tax_repartition_line_id' : tax_res['tax_repartition_line_id'],
                            'tax_tag_ids' : tax_res['tag_ids'],
                            'auto_tax_line' : True,
                            'tax_line_id2' :tax_res['id'],
                            'tax_base_amount' : line.invoice_id.amount_untaxed or line.payment_amount or line.balance,
                            'tax_line_id' : line.id,
                            })
            
            if in_draft_mode:
                self.payment_line_ids -=to_remove
            else:
                to_remove.unlink()



    def action_post(self):
        for rec in self:
            if not rec.code_advance:
                sequence_code = ''
                if rec.advance:
                    if rec.partner_type == 'customer':
                        sequence_code = 'account.payment.advance.customer'
                    if rec.partner_type == 'supplier':
                        sequence_code = 'account.payment.advance.supplier'
                    if rec.partner_type == 'employee':
                        sequence_code = 'account.payment.advance.employee'

                rec.code_advance = self.env['ir.sequence'].with_context(ir_sequence_date=rec.date).next_by_code(sequence_code)
                if not rec.code_advance and rec.advance:
                    raise UserError(_("You have to define a sequence for %s in your company.") % (sequence_code,))
            if not rec.name:
                if rec.partner_type == 'employee':
                    sequence_code = 'account.payment.employee'
                    rec.name = self.env['ir.sequence'].with_context(ir_sequence_date=rec.date).next_by_code(sequence_code)
                    if not rec.name:
                        raise UserError(_("You have to define a sequence for %s in your company.") % (sequence_code,))
            if self.payment_line_ids and self.payment_type != 'transfer':
                amount = rec.amount * (rec.payment_type in ('outbound', 'transfer') and 1 or -1)
                self._create_payment_entry_line(rec.move_id)
                super().action_post()
                for line in self.payment_lines:
                    invoice_id = line.inv_id
                    if invoice_id:
                        invoice_id.with_context(skip_account_move_synchronization=True).js_assign_outstanding_line(line.id)
            else:
                super(AccountPayment, rec).action_post()
        return True

    ##### END advance
    # @api.onchange('journal_id', 'payment_type')
    # def _onchange_account_id(self):
    #     account = self._compute_destination_account_id()
    #     self.account_id = account

    @api.onchange( 'payment_type', 'partner_type', 'partner_id', 'journal_id', 'destination_account_id')
    def _change_destination_account(self):
        change_destination_account = '0'
        account_id = None
        partner = self.partner_id.with_context(company_id=self.company_id.id)

        if self.payment_type == 'transfer':
            self._onchange_amount()
            if not self.company_id.transfer_account_id.id:
                raise UserError(_('There is no Transfer Account defined in the accounting settings. Please define one to be able to confirm this transfer.'))
            account_id = self.company_id.transfer_account_id.id

            # Esta comentado porque no corresponde al modulo
            # account_id = self.destination_journal_id and self.destination_journal_id.default_debit_account_id.id or False
        elif self.partner_id:
            if self.partner_type == 'customer':
                account_id = partner.property_account_receivable_id.id
            else:
                account_id = partner.property_account_payable_id.id
        elif self.partner_type == 'customer':
            # default_account = self.env['ir.property'].with_context(force_company=self.company_id.id).get('property_account_receivable_id', 'res.partner')
            default_account = partner.property_account_receivable_id
            account_id = default_account.id
        elif self.partner_type == 'supplier':
            # default_account = self.env['ir.property'].with_context(force_company=self.company_id.id).get('property_account_payable_id', 'res.partner')
            default_account = partner.property_account_payable_id
            account_id = default_account.id

        if self.destination_account_id.id != account_id:
            change_destination_account = self.destination_account_id.id
        self.change_destination_account = change_destination_account

    @api.onchange('currency_id')
    def _onchange_currency(self):
        for line in self.payment_line_ids:
            line.payment_currency_id = self.currency_id.id or False
            line._onchange_to_pay()
            line._onchange_payment_amount()
        # return super(AccountPayment, self)._onchange_currency()

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        default.update(payment_line_ids=[])
        return super(AccountPayment, self).copy(default)

    @api.onchange('account_move_payment_ids')
    def _onchange_account_move_payment_ids(self):
        if self.account_move_payment_ids:
            where_clause = "account_move_line.amount_residual != 0 AND ac.reconcile AND account_move_line.id in %s"
            where_params = [tuple(self.account_move_payment_ids.ids)]
            self._cr.execute('''
            SELECT account_move_line.id
            FROM account_move_line
            LEFT JOIN account_account ac ON (account_move_line.account_id = ac.id)
            WHERE ''' + where_clause, where_params
            )
            res = self._cr.fetchall()
            if res:
                for r in res:
                    moves = self.env['account.move.line'].browse(r)
                    self._change_and_add_payment_detail(moves)
        self.account_move_payment_ids = None


    @api.onchange('customer_invoice_ids')
    def _onchange_customer_invoice_ids(self):
        if self.customer_invoice_ids:
            where_clause = "account_move_line.amount_residual != 0 AND ac.reconcile AND am.id in %s"
            where_params = [tuple(self.customer_invoice_ids.ids)]
            self._cr.execute('''
            SELECT account_move_line.id
            FROM account_move_line
            LEFT JOIN account_move am ON (account_move_line.move_id = am.id)
            LEFT JOIN account_account ac ON (account_move_line.account_id = ac.id)
            WHERE ''' + where_clause, where_params
            )
            res = self._cr.fetchall()
            if res:
                for r in res:
                    moves = self.env['account.move.line'].browse(r)
                    self._change_and_add_payment_detail(moves)
        self.customer_invoice_ids = None

    @api.onchange('supplier_invoice_ids')
    def _onchange_supplier_invoice_ids(self):
        if self.supplier_invoice_ids:
            where_clause = "account_move_line.amount_residual != 0 AND ac.reconcile AND am.id in %s"
            where_params = [tuple(self.supplier_invoice_ids.ids)]
            self._cr.execute('''
            SELECT account_move_line.id
            FROM account_move_line
            LEFT JOIN account_move am ON (account_move_line.move_id = am.id)
            LEFT JOIN account_account ac ON (account_move_line.account_id = ac.id)
            WHERE ''' + where_clause, where_params
            )
            res = self._cr.fetchall()
            if res:
                for r in res:
                    moves = self.env['account.move.line'].browse(r)
                    self._change_and_add_payment_detail(moves)
        self.supplier_invoice_ids = None

    def _change_and_add_payment_detail(self, moves):
        SelectPaymentLine = self.env['account.payment.detail.massive']
        current_payment_lines = self.payment_line_ids.filtered(lambda line: not line.exclude_from_payment_detail)
        move_lines = moves - current_payment_lines.mapped('move_line_id')
        other_lines = self.payment_line_ids - current_payment_lines
        self.payment_line_ids = other_lines + self.payment_lines
        ctx = self._context or {}
        vendors = ctx.get('vendors', False)
        _logger.info('\n\n %r \n\n', vendors)
        for line in move_lines:
            data = self._get_data_move_lines_payment(line)
            if ctx.get('button') and vendors:
                _logger.info('\nline.partner_id.id\n %r \n\n', [line.partner_id.id, line.amount_residual, vendors[line.partner_id.id]])
                amount = vendors[line.partner_id.id] - (line.amount_residual *-1)
                if amount > 0.0:
                    vendors[line.partner_id.id] -= (line.amount_residual *-1)
                elif vendors[line.partner_id.id] >0.0 or vendors[line.partner_id.id] == (line.amount_residual*-1):
                    data['to_pay'] = False
                    data['payment_amount'] =  vendors[line.partner_id.id]
                    vendors[line.partner_id.id] = 0
                else:
                    continue
            if ctx.get('button'):
                pay = SelectPaymentLine.create(data)
            else:
                pay = SelectPaymentLine.new(data)
            pay._onchange_move_lines()
            pay._onchange_to_pay()
            pay._onchange_payment_amount()
            _logger.info('\n\n %r \n\n', pay)


    def _get_data_move_lines_payment(self, line):
        data = {
            'move_line_id': line.id,
            'move_line_origin': line.id,
            'account_id': line.account_id.id,
            'tax_ids' : [(6, 0, line.tax_ids.ids)],
            'tax_repartition_line_id' : line.tax_repartition_line_id.id,
            'tax_base_amount': line.tax_base_amount,
            'tax_tag_ids' : [(6, 0, line.tax_tag_ids.ids)],
            'payment_id': self.id,
            'payment_currency_id': self.currency_id.id,
            'payment_difference_handling': 'open',
            #'writeoff_account_id': False,
            'to_pay': True
            }
        return data

    @api.onchange('payment_lines')
    def _onchange_payment_lines(self):
        current_payment_lines = self.payment_line_ids.filtered(lambda line: not line.exclude_from_payment_detail)
        other_lines = self.payment_line_ids - current_payment_lines
        self.payment_line_ids = other_lines + self.payment_lines
        self._onchange_recompute_dynamic_line()

    @api.onchange('currency_id', 'amount', 'payment_type')
    def _onchange_payment_amount_currency(self):
        # self.writeoff_account_id = self._get_account_diff_currency(self.payment_difference_line)
        #self.writeoff_account_id = self._get_account_diff_currency(self.payment_difference_line)
        self._recompute_dynamic_lines()

    def _get_account_diff_currency(self, amount):
        account = False
        company = self.env.company
        exchange_journal = company.currency_exchange_journal_id
        account = amount > 0 and exchange_journal.company_id.account_journal_payment_debit_account_id 
        if not account:
            account = company.income_currency_exchange_account_id
        return account

    @api.onchange('payment_difference_line', 'account_id')
    def _onchange_diference_account(self):
        self._recompute_dynamic_lines()

    @api.onchange('date')
    def _onchange_payment_date(self):
        for line in self.payment_line_ids.filtered(lambda line: not line.exclude_from_payment_detail):
            line._onchange_to_pay()
            line._onchange_payment_amount()
            line._compute_payment_difference()
            line._compute_debit_credit_balance()
        self._recompute_dynamic_lines()

    @api.onchange('payment_line_ids', 'account_id', 'destination_account_id')
    def _onchange_recompute_dynamic_line(self):
        self._recompute_dynamic_lines()

    def _recompute_dynamic_lines(self):
        amount = self.amount * (self.payment_type in ('outbound', 'transfer') and 1 or -1)
        self._onchange_accounts(-amount, account_id=self.account_id, is_account_line=True)

        # Diferencia de cambio
        if self.payment_type != 'transfer':
            payment_lines = self.payment_line_ids.filtered(lambda line: not line.exclude_from_payment_detail)
            if not payment_lines:
                counter_part_amount = amount
            else:
                counter_part_amount = 0.0
            self._onchange_accounts(counter_part_amount, account_id=self.destination_account_id, is_counterpart=True)
            payment_difference =  self.payment_difference_line * (self.payment_type in ('outbound', 'transfer') and 1.0 or -1.0)
            #self._onchange_accounts(payment_difference, account_id=self.writeoff_account_id, is_diff=True)
            # self._onchange_accounts(payment_difference, account_id=self.account_id, is_diff=True)

        # para destino transferencia y/o destin
        if self.payment_type == 'transfer':
            self._onchange_accounts(amount, account_id=self.destination_account_id, is_transfer=True)

        if self != self._origin:
            self.payment_lines = self.payment_line_ids.filtered(lambda line: not line.exclude_from_payment_detail)

    def _onchange_accounts(self, amount,
                                account_id=None, is_account_line=False, is_manual_currency=False, is_transfer=False, is_diff=False, is_counterpart=False):
        self.ensure_one()
        in_draft_mode = self != self._origin
        def _create_origin_and_transfer_payment(self, total_balance, account, journal, new_payment_line):
            line_values = self._set_fields_detail(total_balance, is_account_line, is_manual_currency, is_counterpart, is_transfer, is_diff, account)
            if self.payment_type == 'transfer' and (journal and journal.type == 'bank'):
                if journal.bank_account_id and journal.bank_account_id.partner_id:
                    line_values.update({
                        'partner_id': journal.bank_account_id.partner_id.id
                        })
            if new_payment_line:
                new_payment_line.update(line_values)
            else:
                line_values.update({
                    'company_id': self.company_id and self.company_id.id or False,
                    })
                create_method = in_draft_mode and self.env['account.payment.detail.massive'].new or self.env['account.payment.detail.massive'].create
                new_payment_line = create_method(line_values)

            new_payment_line._onchange_to_pay()
            new_payment_line._onchange_payment_amount()
        journal = self.journal_id
        if is_account_line:
            existing_account_origin_line = self.payment_line_ids.filtered(lambda line: line.is_account_line)
        elif is_counterpart:
            existing_account_origin_line = self.payment_line_ids.filtered(lambda line: line.is_counterpart)
        elif is_manual_currency:
            existing_account_origin_line = self.payment_line_ids.filtered(lambda line: line.is_manual_currency)
        elif is_diff:
            existing_account_origin_line = self.payment_line_ids.filtered(lambda line: line.is_diff)
        elif is_transfer:
            existing_account_origin_line = self.payment_line_ids.filtered(lambda line: line.is_transfer)
            journal = self.destination_journal_id
        if not account_id:
            self.payment_line_ids -= existing_account_origin_line
            return
        if self.currency_id.is_zero(amount):
            self.payment_line_ids -= existing_account_origin_line
            return

        _create_origin_and_transfer_payment(self, amount, account_id, journal, existing_account_origin_line)

    def _set_fields_detail(self, total_balance, is_account_line, is_manual_currency, is_counterpart, is_transfer, is_diff, account):
        line_values = {
            'payment_amount': total_balance,
            'partner_id': self.partner_id.id or False,
            'payment_id': self.id,
            'company_currency_id': self.env.company.currency_id.id,
            'is_account_line': is_account_line,
            'is_manual_currency': is_manual_currency,
            'is_counterpart': is_counterpart,
            'is_transfer': is_transfer,
            'is_diff': is_diff,
            'name':    self.ref or '/',
            'currency_id' : self.currency_id.id,
            'account_id': account,
            'ref': self.name or '/',
            'exclude_from_payment_detail': True,
            'payment_currency_id': self.currency_id.id,
        }
        company_currency = self.env.company.currency_id
        if self.currency_id and self.currency_id != company_currency:
            amount = company_currency._convert(total_balance, self.currency_id, self.env.company, self.date or fields.Date.today())
            line_values.update({
                'amount_currency' : amount
                })
        return line_values

    @api.model
    def _prepare_ce_line(self, line=False, payment_order=False):
        po_line_vals = {
            'move_line_id': line.move_line_id.id,
            'account_id': line.account_id.id,
            'tax_ids' : [(6, 0, line.tax_ids.ids)],
            'tax_repartition_line_id' : line.tax_repartition_line_id.id,
            'tax_base_amount': line.tax_base_amount,
            'tax_tag_ids' : [(6, 0, line.tax_tag_ids.ids)],
            'payment_id': payment_order.id,
            'payment_currency_id': line.payment_currency_id.id,
            'payment_difference_handling': line.payment_difference_handling,
            'ref': line.ref,
            'name': line.name,
            'move_line_origin' : line.move_line_origin.id,
            'move_id': line.move_id.id or False,
            'number' : line.number,
            'amount_currency' : line.amount_currency,
            'invoice_id' : line.invoice_id.id,
            'amount_currency' : line.amount_currency,
            'date' : line.date,
            'amount_residual' : line.amount_residual,
            'amount_residual_currency': line.amount_residual_currency,
            'to_pay': line.to_pay,
            'is_manual_currency' : line.is_manual_currency,
            'payment_amount': line.payment_amount,
            'partner_id': line.partner_id.id,
            'exclude_from_payment_detail': False,
            'is_account_line': line.is_account_line,
            'currency_id' : line.currency_id.id,
        }
        return po_line_vals

    def request_ce(self):
        payment_obj = self.env['account.payment']
        payment_line_obj = self.env['account.payment.detail']

        for rec in self:
            if not rec.payment_lines:
                raise UserError(_('Por favor, crea al menos una línea de pago'))
            if rec.payment_ids.filtered(lambda x:x.state in ['draft','posted'] ):
                raise UserError(_('Ya hay pagos Creados'))
            currency_id = rec.env.company.currency_id.id
            company_id = rec.company_id.id
            journal_id = self.journal_id.id
            default_account_id = self.journal_id.default_account_id.id
            po_dict = {}

            # Organiza las líneas de pago por tercero
            lines_by_partner = {}
            for line in rec.payment_lines:
                for partner in line.partner_id:
                    if partner not in lines_by_partner:
                        lines_by_partner[partner] = []
                    lines_by_partner[partner].append(line)

            # Procesa las líneas de pago por tercero
            for partner, lines in lines_by_partner.items():
                all_line_vals = []  # Lista para almacenar todos los valores de las líneas
                payment_order = po_dict.get(partner)

                if not payment_order:
                    po_vals = self._prepare_po_vals(partner, rec, currency_id, company_id, journal_id, default_account_id)
                    payment_order = payment_obj.create(po_vals)
                    po_dict[partner] = payment_order

                for line in lines:
                    po_line_vals = rec._prepare_ce_line(line, payment_order)
                    all_line_vals.append(po_line_vals)

                    # Se crean todas las líneas a la vez después de iterar sobre todas las líneas para este tercero
                    if line is lines[-1]:  # Este es el último elemento
                        payment_line_obj.sudo().create(all_line_vals)
                        payment_order._payment_amount()
                        payment_order._onchange_payment_date()

                    _logger.info('Contenido de all_line_vals para el partner %s: %s', partner.name, all_line_vals)

    def _prepare_po_vals(self, partner, rec, currency_id, company_id, journal_id, default_account_id):
        """
        Prepara los valores para una nueva orden de pago.

        Los valores son generados a partir de los parámetros proporcionados.
        """
        return {
            'partner_id': partner.id,
            'currency_id': currency_id,
            'date': rec.date,
            'ref' : partner.name,
            'ce_origin': self.id,
            'outstanding_account_id' : rec.payment_method_line_id.payment_account_id.id,
            'company_id': company_id,
            'journal_id': journal_id,
            'partner_type': 'supplier', 
            'payment_type' : 'outbound',
            'destination_account_id': partner.property_account_payable_id.id,
        }

    @api.onchange('payment_lines', 'amount', 'payment_lines.payment_amount','state','write_date')
    def _payment_amount(self):
        amount = 0.0
        for val in self:
            for line in val.payment_lines:
                amount += (line.payment_amount)
                val.amount = val.currency_id.round(amount)

class AccountPaymentDetail(models.Model):
    _inherit = "account.payment.detail"

    move_line_origin = fields.Many2one('account.move.line', string="Comprobante diario")

class AccountPaymentDetail(models.Model):
    _name = "account.payment.detail.massive"
    _description = "Detalle de transferencia, pago y/o cobro"
    _check_company_auto = True

    @api.depends('move_line_id', 'date', 'currency_id')
    def _amount_residual(self):
        # for line in self:
        residual, residual_currency = 0.0, 0.0
        for val in self:
            if val.move_line_id:
                amount, amount_currency = val._compute_payment_amount_currency()
                val.amount_residual = amount # self.move_line_id.amount_residual
                val.amount_residual_currency = amount_currency # self.move_line_id.amount_residual_currency

    @api.depends('payment_amount', 'payment_currency_id', 'invoice_id', 'move_line_id',
        'payment_id.payment_type', 'payment_id.date', 'payment_id.currency_id')
    def _compute_debit_credit_balance(self):
        for val in self:
            balance = val.payment_amount
            company = val.company_id or val.env.company

            if val.payment_id.currency_id and self.payment_id.currency_id != company.currency_id:
                currency = val.payment_id.currency_id
                balance = currency._convert(balance, val.company_currency_id, company, val.payment_id.date or fields.Date.today())


            sign = val.payment_id.payment_type == 'outbound' and 1 or -1
            if val.invoice_id:
                if MAP_INVOICE_TYPE_PAYMENT_SIGN[val.invoice_id.move_type] < 1 and (val.move_line_id and val.move_line_id.balance > 0):
                    sign = 1
                else:
                    sign = MAP_INVOICE_TYPE_PAYMENT_SIGN[val.invoice_id.move_type]

                balance *= sign * -1


            if val.account_id.account_type == 'liability_payable':
                balance *= 1
                if val.move_line_id.balance < 0.0:
                    balance = abs(balance)

            val.debit = balance > 0.0 and balance or False
            val.credit = balance < 0.0 and abs(balance) or False
            val.balance = balance


    @api.depends('balance')
    def _compute_type(self):
        for val in self:
            val.type = val.balance > 0 and 'Ingreso' or "Egreso"
    payment_id = fields.Many2one('account.payment.ce', string="Pago y/o Cobro", 
        check_company=True, index=True, auto_join=True, ondelete="cascade")
    name = fields.Char('Etiqueta')
    state = fields.Selection(related='payment_id.state', store=True)
    other_payment_id = fields.Many2one('account.payment', string="Pagos")
    move_line_id = fields.Many2one('account.move.line', string="Documentos, pagos/cobros", copy=False)
    partner_type = fields.Selection(related="payment_id.partner_type") 
    account_id = fields.Many2one('account.account', string="Cuenta", required=True)
    invoice_id = fields.Many2one('account.move', string="Factura")
    partner_id = fields.Many2one('res.partner', string="Empresa")
    currency_id = fields.Many2one('res.currency', string="Moneda")
    # currency_id = fields.Many2one('res.currency', compute="_compute_currency_id", string="Moneda", store=True)
    company_currency_id = fields.Many2one('res.currency', string="Moneda de la compañia",
        required=True, default=lambda self: self.env.company.currency_id)
    move_id = fields.Many2one('account.move', string="Comprobante diario")
    move_line_origin = fields.Many2one('account.move.line', string="Comprobante diario")
    ref = fields.Char(string="Referencia")
    number = fields.Char('Número')
    type = fields.Char(compute="_compute_type", store=True, readonly=True, string="Type")
    debit = fields.Monetary('Debit', compute='_compute_debit_credit_balance', store=True, readonly=True, currency_field='company_currency_id')
    credit = fields.Monetary('Credit', compute='_compute_debit_credit_balance', store=True, readonly=True, currency_field='company_currency_id')
    balance = fields.Monetary(compute='_compute_debit_credit_balance', store=True, readonly=True, currency_field='company_currency_id',
        help="Technical field holding the debit - credit in order to open meaningful graph views from reports")
    amount_currency = fields.Monetary(string="Moneda de importes")
    journal_id = fields.Many2one('account.journal', related="payment_id.journal_id", string="Diario", store=True)
    company_id = fields.Many2one('res.company', related="journal_id.company_id", store=True)
    date = fields.Date(related="payment_id.date")
    is_account_line = fields.Boolean(string="Cuenta origen", default=False)
    is_transfer = fields.Boolean(string="Es transferencia", default=False)
    is_diff = fields.Boolean(string="Es Diferencia", default=False)
    is_counterpart = fields.Boolean(string="Es Contrapartida", default=False)
    is_manual_currency = fields.Boolean(string="Moneda manual", default=False)
    amount_residual = fields.Monetary(string="Deuda MN", compute="_amount_residual", store=True, currency_field='company_currency_id',
        help="The residual amount on a journal item expressed in the company currency.")
    amount_residual_currency = fields.Monetary(string="Deuda ME", compute="_amount_residual", store=True, currency_field='currency_id',
        help="The residual amount on a journal item expressed in its currency (possibly not the company currency).")
    date_maturity = fields.Date(related="move_line_id.date_maturity", store=True, string="Fecha vencimiento")
    payment_currency_id = fields.Many2one('res.currency', string="Moneda de pago", default=lambda self: self.env.company.currency_id)
    payment_amount = fields.Monetary('Monto de pago', currency_field="payment_currency_id")
    exclude_from_payment_detail = fields.Boolean(help="Campo tecnico utilizado para excluir algunas lineas de la \
        pestaña detalle de payment_lines en la vista formulario")
    to_pay = fields.Boolean('A pagar', default=False)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', index=True,  store=True, readonly=False, check_company=True, copy=True)
    product_id = fields.Many2one('product.product', string='Product')
    tax_ids = fields.Many2many('account.tax', string='Taxes', help="Taxes that apply on the base amount", index=True,  store=True, check_company=True)
    tax_tag_ids = fields.Many2many(string="Tags", comodel_name='account.account.tag', ondelete='restrict',
        help="Tags assigned to this line by the tax creating it, if any. It determines its impact on financial reports.")
    tax_repartition_line_id = fields.Many2one('account.tax.repartition.line',
        string="Originator Tax Distribution Line", ondelete='restrict', 
        check_company=True,
        help="Tax distribution line that caused the creation of this move line, if any")   
    auto_tax_line = fields.Boolean()
    tax_line_id = fields.Many2one('account.payment.detail.massive', ondelete = 'cascade')
    tax_line_id2 = fields.Many2one('account.tax', ondelete = 'cascade')
    tax_base_amount = fields.Monetary(string="Base Amount", 
        currency_field='company_currency_id')
    tag_ids = fields.Many2many(
        comodel_name="account.payment.tag",
        string="Tags",
        relation="payment_ce_tag_rel",
        column1="payment_ce_id",
        column2="tag_id",
    )

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if not self.payment_currency_id:
            self.payment_currency_id = self.payment_id and self.payment_id.currency_id.id or self.env.company.currency_id.id

    @api.depends('move_line_id', 'invoice_id', 'payment_amount', 'payment_id.date', 'payment_currency_id')
    def _compute_payment_difference(self):
        for val in self:
            if val.move_line_id:
                payment_amount = -val.payment_amount if val.payment_id.payment_type == 'outbound' else val.payment_amount
                if val.move_line_id.currency_id and  val.move_line_id.currency_id != val.move_line_id.company_currency_id:
                    payment_amount =  val.move_line_id.company_currency_id._convert(
                        payment_amount, val.currency_id, val.company_id, val.date or fields.Date.today()
                        )
                val.payment_difference = val._compute_payment_amount() - payment_amount
            else:
                val.payment_difference = 0.0

    payment_difference = fields.Monetary(compute='_compute_payment_difference', string='Payment Difference', readonly=True, store=True)
    payment_difference_handling = fields.Selection([('open', 'Mantener abierto'), ('reconcile', 'Marcar la factura como totalmente pagada')], default='open', string="Payment Difference Handling", copy=False)
    writeoff_account_id = fields.Many2one('account.account', string="Difference Account", domain=[('deprecated', '=', False)], copy=False)

    # esta funciona es para capturar el monto convertido en dolares o soles a la fecha de pago
    def _compute_payment_amount_currency(self):
        total = 0.0
        for val in self:
            payment_currency = val.currency_id or val.journal_id.currency_id or val.journal_id.company_id.currency_id or val.company_currency_id
            if not val.move_line_id:
                total = val.payment_amount
                amount_currency = 0.0
            else:
                amount = val.move_line_id.amount_residual
                amount_currency = val.move_line_id.amount_residual_currency
            if float_is_zero(amount_currency, precision_rounding=payment_currency.rounding):
                return amount, amount_currency
            else:
                amount = payment_currency._convert(amount_currency, val.company_currency_id,
                                                        val.company_id, val.date or fields.date.today())
                return amount, amount_currency

    def _compute_payment_amount(self, invoices=None, currency=None):
        for val in self:
            payment_currency = currency
            if not payment_currency:
                payment_currency = val.currency_id or val.journal_id.currency_id or val.journal_id.company_id.currency_id or val.company_currency_id

            sign = 1
            if val.move_line_id:
                if val.move_line_id.move_id:
                    sign = MAP_INVOICE_TYPE_PAYMENT_SIGN[val.move_line_id.move_id.move_type]

            # amount = self.move_line_id.amount_residual
            amount = val.amount_residual
            if not val.move_line_id:
                amount = val.payment_amount

            if (payment_currency == val.move_line_id.company_currency_id) or (payment_currency == val.company_currency_id):
                total = sign * amount
            else:
                if val.move_line_id:
                    if not val.move_line_id.amount_residual_currency:
                        total = sign * val.company_currency_id._convert(
                            amount, payment_currency, val.company_id, val.date or fields.Date.today()
                        )
                    else:
                        total = sign * val.move_line_id.amount_residual_currency
                else:
                    total = sign * val.company_currency_id._convert(
                            amount, payment_currency, val.company_id, val.date or fields.Date.today()
                        )
            return total

    @api.onchange('payment_amount', 'payment_currency_id', 'payment_id.payment_type', 'date')
    def _onchange_payment_amount(self):
        for val in self:
            currency = False
            amount = 0.0
            if not val.exclude_from_payment_detail and val.payment_id.payment_type != 'transfer':
                if val.payment_currency_id != val.company_id.currency_id:
                    amount = val.payment_amount
                    currency = val.payment_currency_id or False
            elif val.exclude_from_payment_detail and val.payment_id.payment_type != 'transfer':
                company = val.company_id or val.env.company
                currency = val.journal_id.currency_id or val.journal_id.company_id.currency_id or val.env.company.currency_id
                if currency != val.journal_id.company_id.currency_id:
                    if currency != val.payment_currency_id:
                        amount = val.company_currency_id._convert(val.payment_amount, currency, company, val.payment_id.date or fields.Date.today())
                    else:
                        amount = val.payment_amount
            if val.account_id.currency_id:
                currency = val.account_id.currency_id
                if currency != val.company_currency_id and val.payment_id.currency_id == val.company_currency_id:
                    amount = val.company_currency_id._convert(val.payment_amount, currency, val.company_id, val.payment_id.date or fields.Date.today())
            else:
                if val.invoice_id and val.invoice_id.currency_id != val.company_currency_id:
                    currency = val.invoice_id.currency_id
                    amount = val.company_currency_id._convert(val.payment_amount, currency, val.company_id, val.payment_id.date or fields.Date.today())
            val.amount_currency = amount
            val.currency_id = currency
            return {'values':{'currency_id':currency and currency.id or False, 'amount_currency': amount}}

    @api.onchange('to_pay', 'payment_id.payment_type', 'payment_amount')
    def _onchange_to_pay(self):
        for val in self:
            if val.payment_id.payment_type != 'transfer':
                if val.to_pay:
                    if val.payment_currency_id != val.company_currency_id:
                        val.payment_amount = abs(val._compute_payment_amount(currency=val.payment_currency_id))
                    else:
                        val.payment_amount = abs(val.amount_residual)

    @api.onchange('move_line_id')
    def _onchange_move_lines(self):
        for val in self:
            if val.move_line_id:
                val.invoice_id = val.move_line_id.move_id and val.move_line_id.move_id.id or False
                val.name = val.move_line_id.name
                val.ref = val.move_line_id.ref or False
                val.account_id = val.move_line_id.account_id.id
                val.partner_id = val.move_line_id.partner_id.id
                val.number = val.move_line_id.move_id.name
                val.company_currency_id = val.move_line_id.company_currency_id.id
                val.other_payment_id = val.move_line_id.payment_id.id
            vals = val._onchange_payment_amount()
            val.currency_id = vals['values'].get('currency_id')
            val.amount_currency = vals['values'].get('amount_currency')



    def _onchange_read_line_pay(self):
        for line in self:
            line._onchange_to_pay()
            line._onchange_payment_amount()

    def _get_counterpart_move_line_vals(self):
        vals = {
            'account_id' : self.account_id.id,
            'currency_id' : self.currency_id != self.company_currency_id and self.currency_id.id or False,
            'partner_id' : self.partner_id and self.partner_id.id or False,
            'tax_ids' : [(6, 0, self.tax_ids.ids)],
            'tax_tag_ids' : [(6, 0, self.tax_tag_ids.ids)],
            'tax_base_amount': self.tax_base_amount,
            'tax_line_id': self.tax_line_id2.id,
            'tax_repartition_line_id' :  self.tax_repartition_line_id.id,
        }
        if self.invoice_id:
            name = "Pago Documento: " + self.invoice_id.name
            tax_ids = [(6, 0, self.tax_ids.ids)],
            tax_repartition_line_id = self.tax_repartition_line_id and self.tax_repartition_line_id.id  or False,
        else:
            name = self.name or ''
        vals.update(
            name = name,
            ref = self.payment_id.ref or ''
        )
        if self.currency_id and self.currency_id != self.company_currency_id:
            sing = self.debit > 0.0 and 1 or -1
            vals.update({
                'amount_currency': abs(self.amount_currency) * sing
                })
        return vals

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    ce_origin = fields.Many2one('account.payment.ce', string="Programacion de Pagos")
    num_autorizaciones = fields.Char('Numero de autorizaciones')
    
    #@api.onchange('payment_lines', 'amount', 'payment_lines.payment_amount')
    def _payment_amount(self):
        for val in self:
            amount = 0.0
            if val.payment_type != 'transfer':
                for line in val.payment_line_ids:
                    sign = 1.0
                    if not line.is_counterpart and not line.is_account_line and not line.is_manual_currency and not line.is_diff:
                        if line.move_line_id and line.balance < 0:
                            sign = -1.0
                        amount += (line.payment_amount * sign)
                    if line.is_account_line or line.is_counterpart:
                        # Agrega una verificación de condición basada en el saldo del movimiento (line.balance)
                        if line.balance < 0:
                            amount -= abs(line.payment_amount * sign) or val.amount
                        else:
                            amount += (line.payment_amount * sign) or val.amount

                if val.payment_type == 'outbound':
                    amount *= -1.0

                val.amount = abs(val.currency_id.round(amount))
            self.num_autorizaciones = self.get_sequence_aut()

    @api.model
    def _payment_txt(self):
        lines = self.payment_lines
        labels = (line.name or line.move_line_id.name or line.move_line_id.move_name for line in lines)
        self.ref = str(('%s')%(' / '.join(labels)))
    
    def get_sequence_aut(self):
        self.ensure_one()
        company = self.company_id.id or self.env.company.id
        SEQUENCE_CODE = 'num_autorizaciones'
        ctx = dict(self._context, company_id=company)
        IrSequence = self.env['ir.sequence'].with_context(ctx)
        name = IrSequence.next_by_code(SEQUENCE_CODE)
        # si aún no existe una secuencia para esta empresa, cree una
        if not name:
            IrSequence.sudo().create({
                'prefix': 'PAY',
                'name': 'Programacion De Pagos %s' % 1,
                'code': SEQUENCE_CODE,
                'implementation': 'no_gap',
                'padding': 8,
                'number_increment': 1,
                'company_id': company,
            })
            name = IrSequence.next_by_code(SEQUENCE_CODE)
        return name

    # def _onchange_accounts(self, amount,
    #                             account_id=None, is_account_line=False, is_manual_currency=False, is_transfer=False, is_diff=False, is_counterpart=False):
    #     self.ensure_one()
    #     in_draft_mode = self != self._origin
    #     def _create_origin_and_transfer_payment(self, total_balance, account, journal, new_payment_line):
    #         line_values = self._set_fields_detail(total_balance, is_account_line, is_manual_currency, is_counterpart, is_transfer, is_diff, account)
    #         if self.payment_type == 'transfer' and (journal and journal.type == 'bank'):
    #             if journal.bank_account_id and journal.bank_account_id.partner_id:
    #                 line_values.update({
    #                     'partner_id': journal.bank_account_id.partner_id.id
    #                     })
    #         if new_payment_line:
    #             new_payment_line.update(line_values)
    #         else:
    #             line_values.update({
    #                 'company_id': self.company_id and self.company_id.id or False,
    #                 })
    #             create_method = in_draft_mode and self.env['account.payment.detail'].new or self.env['account.payment.detail'].create
    #             new_payment_line = create_method(line_values)

    #         new_payment_line._onchange_to_pay()
    #         new_payment_line._onchange_payment_amount()
    #     journal = self.journal_id
    #     if is_account_line:
    #         existing_account_origin_line = self.payment_line_ids.filtered(lambda line: line.is_account_line)
    #     elif is_counterpart:
    #         existing_account_origin_line = self.payment_line_ids.filtered(lambda line: line.is_counterpart)
    #     elif is_manual_currency:
    #         existing_account_origin_line = self.payment_line_ids.filtered(lambda line: line.is_manual_currency)
    #     elif is_diff:
    #         existing_account_origin_line = self.payment_line_ids.filtered(lambda line: line.is_diff)
    #     elif is_transfer:
    #         existing_account_origin_line = self.payment_line_ids.filtered(lambda line: line.is_transfer)
    #         journal = self.destination_journal_id
    #     if not account_id:
    #         self.payment_line_ids -= existing_account_origin_line
    #         return
    #     if self.currency_id.is_zero(amount):
    #         self.payment_line_ids -= existing_account_origin_line
    #         return

    #     _create_origin_and_transfer_payment(self, amount, account_id.id, journal, existing_account_origin_line)

class PaymentTag(models.Model):
    _name = "account.payment.tag"
    _description = "Programacion de Pagos"
    _order = "sequence, name"

    name = fields.Char(string="Name", required=True, translate=True)
    sequence = fields.Integer(default=10)
    color = fields.Integer(string="Color Index")
    payment_ce__ids = fields.Many2many(
        comodel_name="account.payment.ce",
        string="Programacion de Pagos",
        relation="payment_ce_tag_rel",
        column1="tag_id",
        column2="payment_ce_id",
    )
    payment_count = fields.Integer(
        string="# of Products", compute="_compute_products_count"
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
    )

    _sql_constraints = [
        (
            "name_uniq",
            "unique(name, company_id)",
            "Tag name must be unique inside a company",
        ),
    ]

    @api.depends("payment_ce__ids")
    def _compute_products_count(self):
        tag_id_oayment_count = {}
        if self.ids:
            self.env.cr.execute(
                """SELECT tag_id, COUNT(*)
                FROM payment_ce_tag_rel
                WHERE tag_id IN %s
                GROUP BY tag_id""",
                (tuple(self.ids),),
            )
            tag_id_oayment_count = dict(self.env.cr.fetchall())
        for rec in self:
            rec.payment_count = tag_id_oayment_count.get(rec.id, 0)

class Account_journal(models.Model):
    _inherit = 'account.journal'

    type_file = fields.Selection([
        ('1', 'Archivo Plano'),
        ('2', 'Excel')
    ], string='Archivo a generar',  default='1')
    format_file = fields.Selection([('bancolombia', 'Bancolombia SAP'),
                                    ('bancolombia_pab', 'Bancolombia PAB'),
                                    ('davivienda', 'Banco Davivienda'),
                                    ('bbva', 'Banco BBVA'),
                                    ('bogota', 'Banco Bogota'),
                                    ('agrario', 'Banco Agrario'),
                                    ('occired', 'Occired')
                                    ], string='Tipo de plano',  default='bancolombia')

    account_type_debit = fields.Selection([
        ('S', 'Ahorros'),
        ('D', 'Corriente')
    ], string='Tipo de cuenta a debitar')