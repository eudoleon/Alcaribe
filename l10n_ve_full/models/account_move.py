# coding: utf-8
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.exceptions import Warning
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime, date
from dateutil import relativedelta

_DATETIME_FORMAT = "%Y-%m-%d"


class AccountMove(models.Model):
    _inherit = 'account.move'

    supplier_invoice_number = fields.Char(string='Supplier Invoice Number', store=True,
                                          help="The reference of this invoice as provided by the supplier.")

    sin_cred = fields.Boolean(string='Excluir este documento del libro fiscal', readonly=False,
                              help="Configúrelo verdadero si la factura está exenta de IVA (exención de impuestos)")

    date_document = fields.Date(string='Document Date', states={'draft': [('readonly', False)]},
                                help="Fecha administrativa, generalmente es la fecha impresa en factura, esta fecha se"
                                     " utiliza para mostrar en la compra fiscal libro")
    invoice_printer = fields.Char(string='Número de factura de impresora fiscal', size=64, required=False,
                                  help="Fiscal printer invoice number, is the number of the invoice"
                                       " on the fiscal printer")
    invoice_reverse_purchase_id = fields.Many2one('account.move', string="Reversal invoice purchase", copy=False)
    fiscal_printer = fields.Char(string='Número Impresora Fiscal', size=64, required=False,
                                 help="Fiscal printer number, generally is the id number of the printer.")

    comment_paper = fields.Char(string='Comentario')
    paper_anu = fields.Boolean(string='Papel Dañado', default=False)
    marck_paper = fields.Boolean(default=False)
    maq_fiscal_p = fields.Boolean(string='Maquina Fiscal', default=False)

    nro_ctrl = fields.Char(string='Número de Control', size=32,
                           help="Número utilizado para gestionar facturas preimpresas, por ley Necesito poner aquí este"
                                " número para poder declarar Informes fiscales correctamente.", copy=False, store=True,
                           domain="['|',('move_type', '=', 'out_invoice'),('move_type', '=', 'out_refund')]")

    # Campos proveedores##########################
    nro_planilla_impor = fields.Char(string='Nro de Planilla de Importacion')
    nro_expediente_impor = fields.Char(string='Nro de Expediente de Importacion')
    fecha_importacion = fields.Date(string='Fecha de la planilla de Importación')
    supplier_rank1 = fields.Integer(related='partner_id.supplier_rank')
    # Campos clientes##########################
    customer_rank1 = fields.Integer(related='partner_id.customer_rank')
    # Campos para ambas retenciones##########################
    partner_id = fields.Many2one('res.partner', readonly=True,
                                 domain="['|',('customer_rank', '>=', 0),('supplier_rank', '>=', 0)]",
                                 string='Partner')
    rif = fields.Char(string="RIF", related='partner_id.rif', store=True, states={'draft': [('readonly', True)]})
    identification_id1 = fields.Char(string='Documento de Identidad', related='partner_id.identification_id',
                                     store=True, states={'draft': [('readonly', True)]})
    nationality1 = fields.Selection([('V', 'Venezolano'), ('E', 'Extranjero'), ('P', 'Pasaporte')],
                                    string="Tipo Documento", related='partner_id.nationality', store=True,
                                    states={'draft': [('readonly', True)]})
    people_type_company1 = fields.Selection([('pjdo', 'PJDO Persona Jurídica Domiciliada'),
                                             ('pjnd', 'PJND Persona Jurídica No Domiciliada')],
                                            string='Tipo de Persona compañía val')
    people_type_individual1 = fields.Selection([('pnre', 'PNRE Persona Natural Residente'),
                                                ('pnnr', 'PNNR Persona Natural No Residente')],
                                               string='Tipo de Persona individual val')
    company_type1 = fields.Selection(string='Company Type',
                                     selection=[('person', 'Individual'), ('company', 'Company')])
    create_invoice = fields.Boolean(string='Crear factura', default=False)

    ### retencion de Iva##########################
    rela_wh_iva = fields.Many2one('account.wh.iva', copy=False)
    wh_iva = fields.Boolean('¿Ya se ha retenido esta factura con el IVA?',
                            # compute='_compute_retenida',
                            copy=False, help="Los movimientos de la cuenta de la factura han sido retenidos con "
                                             "movimientos de cuenta de los pagos.",tracking=True)
    wh_iva_id = fields.Many2one(
        'account.wh.iva', string='Documento de Retención de IVA',
        compute='_compute_wh_iva_id', store=True,
        help="Este es el documento de retención de IVA donde en esta factura "
             "está siendo retenida.",tracking=True, copy=False)
    vat_apply = fields.Boolean(
        string='Excluir este documento de la retención del IVA',
        states={'draft': [('readonly', False)]},
        help="Esta selección indica si generar la factura "
             "documento de retención",tracking=True)

    islr_wh_doc_id = fields.Many2one(
        'account.wh.islr.doc', string='Documento de retención de ingresos',
        help="Documentación de la retención de ingresos del impuesto generado a partir de esta factura",tracking=True, copy=False)

    wh_xml_id = fields.Many2one('account.wh.islr.xml.line',string='XML Id',default=0,help="XML withhold line id",tracking=True)

    status = fields.Selection([
        ('pro', 'Retención procesada, línea xml generada'),
        ('no_pro', 'Retención no procesada'),
        ('tasa', 'No exceda la tasa, línea xml generada'),
    ], string='Estatus retención ISLR', readonly=True, default='no_pro',
        help=''' * La \'Retención procesada, línea xml generada\'
               es usada cuando el usuario procesa la Retencion de ISLR.
               * La 'Retencion no Procesada\' state es cuando un usuario realiza una factura y se genera el documento de retencion de islr y aun no esta procesado.
               * \'No exceda la tasa, línea XML generada\' se utiliza cuando el usuario crea la factura, una factura no supera la tarifa mínima.''',tracking=True)

    fb_id = fields.Many2one('account.fiscal.book', 'Fiscal Book',
                            help='Libro fiscal donde esta línea está relacionada con')
    issue_fb_id = fields.Many2one('account.fiscal.book', 'Fiscal Book',
                                  help='Libro fiscal donde se debe agregar esta factura')

    alicuota_line_ids = fields.One2many('account.move.line.resumen', 'invoice_id', string='Resumen')

    iva_number_asignado = fields.Char(string="Número retención IVA", copy=False)
    islr_number_asignado = fields.Char(string="Número retención ISLR", copy=False)

    invoice_import_id = fields.Many2one('account.move', string='Factura SENIAT', copy=False)

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        super(AccountMove, self)._onchange_journal_id()
        for rec in self:
            if rec.journal_id.eliminar_impuestos:
                for l in rec.invoice_line_ids:
                    l.tax_ids = [(5)]

    def _get_company(self):
        res_company = self.env['res.company'].search([('id', '=', self.company_id.id)])
        return res_company

    def action_post(self):
        var = super(AccountMove, self).action_post()
        # for rec in self:
        #     if rec.move_type in ['out_invoice', 'out_refund']:
        #         if not rec.nro_ctrl:
        #             rec.nro_ctrl = rec._get_sequence_code()
        #             rec.write({'nro_ctrl': rec.nro_ctrl})
        #         #buscar numero de control en todas confirmadas
        #         numeros_control_usados = self.env['account.move'].search([('move_type','in',['out_invoice', 'out_refund']),('nro_ctrl','=',rec.nro_ctrl),('state','=','posted'),('id','!=',rec.id)])
        #         print(numeros_control_usados)
        #         if numeros_control_usados:
        #             raise UserError(_('El número de control ya se encuentra asignado a un factura confirmada.'))
        monto_tax = 0
        for res in self:
            if not res.journal_id.eliminar_impuestos:
                resul = res._withholdable_tax()
                for inv in res.line_ids:
                    if len(res.line_ids.tax_ids) == 1:
                        for tax in inv.tax_ids:
                            if tax.amount == 0:
                                monto_tax = 2000

            for concep in res.invoice_line_ids:
                if concep.product_id.concept_id:
                    concep.concept_id = concep.product_id.concept_id
            if not res.journal_id.eliminar_impuestos:
                if res.company_id.partner_id.wh_iva_agent and res.partner_id.wh_iva_agent and resul and monto_tax == 0:
                    if res.state == 'posted':
                        for ilids in res.invoice_line_ids:
                            res.check_document_date()
                            res.check_invoice_dates()
                            apply = res.check_wh_apply()
                            if apply:
                                res.check_withholdable()
                                res.action_wh_iva_supervisor()
                                res.action_wh_iva_create()

                if res.company_id.partner_id.islr_withholding_agent and res.partner_id.islr_withholding_agent:
                    for concep in res.invoice_line_ids:
                        if concep.concept_id.withholdable == True:
                            if res.state == 'posted' and not res.islr_wh_doc_id:
                                for ilids in res.invoice_line_ids:
                                    res.check_invoice_type()
                                    res.check_withholdable_concept()
                                    islr_wh_doc_id = res._create_islr_wh_doc()
                                    islr_wh_doc_id and res.write({'islr_wh_doc_id': islr_wh_doc_id.id})
                res.suma_alicuota_iguales_iva()
        return var

    def _get_sequence_code(self):
        # metodo que crea la secuencia del número de control, si no esta creada crea una con el
        # nombre: 'l10n_nro_control
        self.ensure_one()
        sequence_code = 'l10n_nro_control_sale'
        company_id = self._get_company()
        #ir_sequence = self.env['ir.sequence'].with_context(force_company=company_id.id)
        ir_sequence = self.env['ir.sequence'].with_company(company_id)
        self.nro_ctrl = ir_sequence.next_by_code(sequence_code)
        return self.nro_ctrl

    @api.model
    def _get_default_invoice_date(self):
        return fields.Date.today() if self._context.get('default_move_type', 'entry') in \
                                      ('in_invoice', 'in_refund', 'in_receipt') else False

    def button_cancel(self):
        super().button_cancel()
        self.suma_alicuota_iguales_iva()
        self.state='cancel'

    def generate_islr(self):
        for rec in self:
            for concep in rec.invoice_line_ids:
                if concep.product_id.concept_id:
                    concep.concept_id = concep.product_id.concept_id

            for concep in rec.invoice_line_ids:
                if concep.concept_id.withholdable:
                    if self.state == 'posted' and not rec.islr_wh_doc_id:
                        for ilids in self.invoice_line_ids:
                            self.check_invoice_type()
                            self.check_withholdable_concept()
                            islr_wh_doc_id = self._create_islr_wh_doc()
                            islr_wh_doc_id and self.write({'islr_wh_doc_id': islr_wh_doc_id.id})

    @api.model_create_multi
    def create(self, values):
        # if values:
        #     for val in values:
        #         module_dual_currency = self.env['ir.module.module'].sudo().search(
        #             [('name', '=', 'account_dual_currency'), ('state', '=', 'installed')])
        #         if module_dual_currency:
        #             val.update({'tax_today': 1 / self.env['res.currency'].search([('name', '=', 'USD')], limit=1).rate})
        #     if values[0].get('invoice_origin'):
        #         purchase_order = self.env['purchase.order'].search([('name', '=', values[0].get('invoice_origin'))])
        #         if purchase_order:
        #             values[0].update({'partner_id': purchase_order.partner_id.id})
        #
        #     if values[0].get('partner_id'):
        #         partner_id = values[0].get('partner_id')
        #         partner_obj = self.env['res.partner'].search([('id', '=', partner_id)])

        res = super(AccountMove, self).create(values)
        for r in res:
            if r.invoice_date and r.date:
                if r.invoice_date > r.date:
                    raise Warning(_('La fecha contable no puede ser menor a la fecha de la factura'))
        return res

    def write(self, vals):
        for move_account in self:
            if move_account.move_type == 'in_invoice' and move_account.invoice_origin:
                order_purchase = self.env['purchase.order'].search([('name', '=', self.invoice_origin)])
                if order_purchase:
                    vals.update({'partner_id': order_purchase.partner_id.id})
        if vals.get('partner_id'):
            partner_id = vals.get('partner_id')
            partner_obj = self.env['res.partner'].search([('id', '=', partner_id)])
            if partner_obj.company_type == 'person' and not partner_obj.identification_id:
                raise UserError("Advertencia! \nEl Proveedor no posee Documento Fiscal. Por favor diríjase a la configuación de %s, y realice el registro correctamente para poder continuar" % (partner_obj.name))
            if partner_obj.company_type == 'company':
                if partner_obj.people_type_company == 'pjdo' and not partner_obj.rif:
                    raise UserError("Advertencia! \nEl Proveedor no posee Documento Fiscal. Por favor diríjase a la configuación de %s, y realice el registro correctamente para poder continuar" % (partner_obj.name))
        if vals.get('move_type') in ('out_invoice', 'out_refund') and \
                vals.get('date') and not vals.get('date_document'):
            vals['date_document'] = vals['date']
        if vals.get('supplier_invoice_number', False):
            supplier_invoice_number_id = self._unique_invoice_per_partner('supplier_invoice_number',
                                                                          vals.get('supplier_invoice_number', False))
            if not supplier_invoice_number_id:
                self.supplier_invoice_number = False
                return {'warning': {'title': "Advertencia!",
                                    'message': "  El Numero de la Factura del Proveedor ya Existe  "}}
        if vals.get('nro_ctrl', False):
            if not self.maq_fiscal_p:
                nro_ctrl_id = self._unique_invoice_per_partner('nro_ctrl', vals.get('nro_ctrl', False))
                if not nro_ctrl_id:
                    self.nro_ctrl = False
                    return {'warning': {'title': "Advertencia!",
                                        'message': "  El Numero de control de la Factura del Proveedor ya Existe  "}}
        if not vals.get('check_fiscal'):
            if vals.get('invoice_date') and isinstance(vals.get('invoice_date'), str):
                fecha_factura = datetime.strptime(vals.get('invoice_date'), '%Y-%m-%d').date()
            else:
                if vals.get('invoice_date'):
                    fecha_factura = vals.get('invoice_date')
                elif len(self) < 2:
                    fecha_factura = self.invoice_date
                else:
                    fecha_factura = False
            if vals.get('date') and isinstance(vals.get('invoice_date'), str):
                fecha = datetime.strptime(vals.get('date'), '%Y-%m-%d').date()
            else:
                if vals.get('date'):
                    fecha = vals.get('date')
                elif len(self) < 2:
                    fecha = self.date
                else:
                    fecha = False
            if fecha and fecha_factura:
                if fecha_factura > fecha:
                    raise Warning(_('La fecha contable no puede ser menor a la fecha de la factura'))
        else:
            del vals['check_fiscal']
        return super(AccountMove, self).write(vals)

    def _get_journal(self, context):
        """ Return the journal which is
        used in the current user's company, otherwise
        it does not exist, return false
        """
        context = context or {}
        res = super(AccountMove, self)._get_journal(context)
        if res:
            return res
        type_inv = context.get('type', 'sale')
        if type_inv in ('sale_debit', 'purchase_debit'):
            user = self.env['res.users'].browse(context)
            company_id = context.get('company_id', user.company_id.id)
            journal_obj = self.env['account.journal']
            domain = [('company_id', '=', company_id), ('type', '=', type_inv)]
            res = journal_obj.search(domain, limit=1)
        return res and res[0] or False

    def _unique_invoice_per_partner(self, field, value):
        """ Return false when it is found
        that the bill is not out_invoice or out_refund,
        and it is not unique to the partner.
        """
        ids_ivo = []
        for inv in self:
            ids_ivo.append(inv.id)
            if inv.move_type in ('out_invoice', 'out_refund'):
                return True
            inv_ids = (self.search([(field, '=', value), ('move_type', '=', inv.move_type), ('partner_id', '=', inv.partner_id.id),('state','=','posted')]))

            if [True for i in inv_ids if i not in ids_ivo] and inv_ids:
                return False
        return True

    # Validaciónn de Fecha
    @api.onchange('date_document')
    def onchange_date_document(self):
        fecha = self.date_document
        if fecha:
            fecha2 = str(fecha)
            age = self._calculate_date(fecha2)
            if age:
                if age.days >= 0 and age.months >= 0 and age.years >= 0:
                    self.date_document = fecha
                else:
                    self.date_document = False
                    return {'warning': {'title': "Advertencia!",
                                        'message': "La fecha ingresada es mayor que la fecha actual"}}

    @staticmethod
    def _calculate_date(value):
        age = 0
        if value:
            ahora = datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT)

            age = relativedelta.relativedelta(datetime.strptime(ahora, _DATETIME_FORMAT),
                                              datetime.strptime(value, _DATETIME_FORMAT))
        return age

    # def copy(self, default=None):
    #     res = super(AccountMove, self).copy(default)
    #     return res

    @api.onchange('supplier_invoice_number')
    def onchange_supplier_invoice_number(self):
        if self.supplier_invoice_number:
            supplier_invoice_number_id = self._unique_invoice_per_partner('supplier_invoice_number', self.supplier_invoice_number)
            if not supplier_invoice_number_id:
                self.supplier_invoice_number = False
                return {'warning': {'title': "Advertencia!",
                                    'message': "  El Numero de la Factura del Proveedor ya Existe  "}}

    @api.onchange('nro_ctrl')
    def onchange_nro_ctrl(self):
        if self.nro_ctrl:
            if not self.maq_fiscal_p:
                nro_ctrl_id = self._unique_invoice_per_partner('nro_ctrl', self.nro_ctrl)
                if not nro_ctrl_id:
                    self.nro_ctrl = False
                    return {'warning': {'title': "Advertencia!",
                                        'message': "  El Numero de control de la Factura del Proveedor ya Existe  "}}

    @api.onchange('partner_id')
    def _compute_partner(self):
        # self.people_type = self.partner_id.people_type_company
        self.customer_rank1 = self.partner_id.customer_rank
        self.supplier_rank1 = self.partner_id.supplier_rank
        self.people_type_company1 = self.partner_id.people_type_company
        self.people_type_individual1 = self.partner_id.people_type_individual
        self.company_type1 = self.partner_id.company_type
        return

    def ret_and_reconcile(self, pay_amount, pay_account_id,
                          pay_journal_id, writeoff_acc_id,
                          writeoff_journal_id, date,
                          name, to_wh,type_retencion):
        """ Make the payment of the invoice
        """
        module_dual_currency = self.env['ir.module.module'].sudo().search([('name','=','account_dual_currency'),('state','=','installed')])
        rp_obj = self.env['res.partner']
        move_obj = self.env['account.move']
        if self.ids:
            assert len(self.ids) == 1, "Solo puede pagar una factura a la vez"
        else:
            assert len(to_wh) == 1, "Solo puede pagar una factura a la vez"
        invoice = self.browse(self.ids)
        src_account_id = pay_account_id.id

        # Take the seq as name for move
        types = {'out_invoice': -1,
                 'in_invoice': 1,
                 'out_refund': 1, 'in_refund': -1}
        direction = types[invoice.move_type]
        l1 = {
            'debit': direction * pay_amount > 0 and direction * pay_amount,
            'credit': direction * pay_amount < 0 and - direction * pay_amount,
            'account_id': src_account_id,
            'partner_id': rp_obj._find_accounting_partner(
                invoice.partner_id).id,
            'ref': invoice.name,
             'date': date,
            'currency_id': invoice.company_id.currency_id.id,
            'name': name
             }
        if module_dual_currency:
            l1['amount_residual_usd'] = direction * (pay_amount / invoice.tax_today)
        lines = [(0, 0, l1)]

        if type_retencion == 'wh_iva':
            l2 = self._get_move_lines1(to_wh, pay_journal_id, writeoff_acc_id,
                                      writeoff_journal_id, date, name)
        if type_retencion == 'wh_islr':
            l2 = self._get_move_lines2(to_wh, pay_journal_id, writeoff_acc_id,
                                      writeoff_journal_id, date, name)
        if type_retencion == 'wh_muni':
            l2 = self._get_move_lines3(to_wh, pay_journal_id, writeoff_acc_id,
                                      writeoff_journal_id, date, name)

        if not l2:
            raise UserError("Advertencia! \nNo se crearon movimientos contables.\n Por favor, verifique si hay impuestos / conceptos para retener en las facturas!")

        deb = l2[0][2]['debit']
        cred = l2[0][2]['credit']
        if deb < 0: l2[0][2].update({'debit': deb * direction})
        if cred < 0: l2[0][2].update({'credit': cred * direction})
        if module_dual_currency:
            l2[0][2]['amount_residual_usd'] = direction * ((deb if deb > 0 else cred) / invoice.tax_today)
        lines += l2

        move = {'ref': name + 'de '+ str(invoice.name),
                'line_ids': lines,
                'journal_id': pay_journal_id,
                'date': date,
                'state': 'draft',
                'type_name': 'entry'
                }
        if module_dual_currency:
            move['tax_today'] = invoice.tax_today

        move_id = move_obj.create(move)
        if module_dual_currency:
            for line in move_id.line_ids:
                line._onchange_amount_currency()
        move_id._post(soft=False)
        to_reconcile = invoice.line_ids.filtered_domain([('account_id', '=', src_account_id), ('reconciled', '=', False)])
        payment_lines = move_id.line_ids.filtered_domain([('account_id', '=', src_account_id), ('reconciled', '=', False)])
        if module_dual_currency:
            payment_lines.amount_residual_usd = payment_lines.amount_residual / invoice.tax_today
            self.env.context = dict(self.env.context, tasa_factura=invoice.tax_today)
        results = (payment_lines + to_reconcile).reconcile()
        if module_dual_currency:
            if 'partials' in results:
                if results['partials'].amount_usd == 0:
                    monto_usd = abs(payment_lines.amount_residual_usd)
                    results['partials'].write({'amount_usd': monto_usd})
                    payment_lines._compute_amount_residual_usd()
            self.env.context = dict(self.env.context, tasa_factura=None)
        return move_id

    @api.depends('wh_iva_id.wh_lines')
    def _compute_wh_iva_id(self):
        for record in self:
            lines = self.env['account.wh.iva.line'].search([
                ('invoice_id', '=', record.id)])
            record.wh_iva_id = lines and lines[0].retention_id.id or False

    def already_posted_iva(self):
        monto_tax = 0
        if self:
            #  self._compute_retenida()
            resul = self._withholdable_tax()
            for inv in self.line_ids:
                if len(self.line_ids.tax_ids) == 1:
                    for tax in inv.tax_ids:
                        if tax.amount == 0:
                            monto_tax = 2000

        if self.company_id.partner_id.wh_iva_agent and self.partner_id.wh_iva_agent and resul and monto_tax == 0:
            if self.state == 'posted':
                for ilids in self.invoice_line_ids:
                    self.check_document_date()
                    self.check_invoice_dates()
                    apply = self.check_wh_apply()
                    if apply == True:
                        self.check_withholdable()
                        self.action_wh_iva_supervisor()
                        self.action_wh_iva_create()

    def check_document_date(self):
        """
        check that the invoice in open state have the document date defined.
        @return True or raise an orm exception.
        """
        for inv_brw in self:
            if (inv_brw.move_type in ('in_invoice', 'in_refund', 'out_invoice', 'out_refund') and
                    inv_brw.state == 'posted' and not inv_brw.date):
                raise UserError("Advertencia \nLa fecha del documento no puede estar vacía cuando la factura se encuentra en estado publicado.")
        return True


    def check_invoice_dates(self):
        """
        check that the date document is less or equal than the date invoice.
        @return True or raise and osv exception.
        """
        for inv_brw in self:
            if (inv_brw.move_type in ('in_invoice', 'in_refund', 'out_invoice', 'out_refund') and
                    inv_brw.date and not inv_brw.invoice_date <= inv_brw.date):
                raise UserError("Warning \nThe document date must be less or equal than the invoice date.")
        return True

    def wh_iva_line_create(self):
        """ Creates line with iva withholding
        """
        wil_obj = self.env['account.wh.iva.line']
        partner = self.env['res.partner']
        values = {}
        type_invoice = ''
        for inv_brw in self:
            wh_iva_rate = (
                inv_brw.move_type in ('in_invoice', 'in_refund', 'out_refund', 'out_invoice') and
                partner._find_accounting_partner(
                    inv_brw.partner_id).wh_iva_rate or
                partner._find_accounting_partner(
                    inv_brw.company_id.partner_id).wh_iva_rate)
            if inv_brw.move_type in ('in_invoice', 'out_invoice', 'out_refund', 'in_refund'):
                if inv_brw.debit_origin_id and inv_brw.move_type == 'out_invoice':
                    type_invoice = 'out_debit'
                elif inv_brw.move_type == 'in_invoice' and  inv_brw.debit_origin_id:
                    type_invoice = 'in_debit'
                elif not inv_brw.debit_origin_id and inv_brw.move_type in ('out_invoice','in_invoice','in_refund','out_refund') :
                    type_invoice = inv_brw.move_type

            values = {'name':_('IVA WH - ORIGIN %s' % (inv_brw.name)),
                      'invoice_id': inv_brw.id,
                      'wh_iva_rate': wh_iva_rate,
                      'type': type_invoice,
                      }

        return values and wil_obj.create(values)


    def action_wh_iva_supervisor(self):
        """ Validate the currencys are equal
        """
        for inv in self:
            if inv.amount_total == 0.0:
                raise UserError(
                    _('Acción Invalida!\nEsta factura tiene una cantidad total% s% s verifique el '
                      'precio de los productos') % (inv.amount_total,
                                            inv.currency_id.symbol))
        return True


    def get_fortnight_wh_id(self):
        """ Returns the id of the acc.wh.iva in draft state that correspond to
        the invoice fortnight. If not exist return False.
        """
        wh_iva_obj = self.env['account.wh.iva']
        partner = self.env['res.partner']
        for inv_brw in self:
            invoice_date = inv_brw.invoice_date
            acc_part_id = partner._find_accounting_partner(inv_brw.partner_id)
            #inv_period, inv_fortnight = period.find_fortnight(invoice_date)
            ttype = (inv_brw.move_type in ["in_refund", "out_refund"])

            for wh_iva in wh_iva_obj.search([
                    ('state', '=', 'draft'), ('type', '=', ttype), '|',
                    ('partner_id', '=', acc_part_id.id),
                    ('partner_id', 'child_of', acc_part_id.id)]):
                    #('fortnight', '=', inv_fortnight):
                return wh_iva.id
        return False


    def create_new_wh_iva(self):
        """ Create a Withholding VAT document.
        @param ids: only one id.
        @return id of the new wh vat document created.
        """
        ret_iva = []
        wh_iva_obj = self.env['account.wh.iva']
        rp_obj = self.env['res.partner']
        values = {}
        acc_id = 0
        for inv_brw in self:
            acc_id = 0
            acc_part_id = rp_obj._find_accounting_partner(inv_brw.partner_id)
            if inv_brw.move_type in ('out_invoice', 'out_refund','_out_debit'):
                acc_id = acc_part_id.property_account_receivable_id.id
                wh_type = 'out_invoice'
            else:
                acc_id = acc_part_id.property_account_payable_id.id
                wh_type = 'in_invoice'
                if not acc_id:
                    raise UserError(
                        _('Accion Invalida\nSe debe configurar el partner'
                          'Con las Cuentas Contables'))
            values = {'name': _('IVA WH - ORIGIN %s' % (inv_brw.name)),
                      'type': wh_type,
                      'account_id': acc_id,
                      'partner_id': acc_part_id.id,
                      }
                # 'date_ret': inv_brw.invoice_date,
                # 'period_id': inv_brw.invoice_date,
                # 'date': inv_brw.invoice_date,

            if inv_brw.company_id.propagate_invoice_date_to_vat_withholding:
                ret_iva['date'] = inv_brw.invoice_date
                ret_iva['date_ret'] = ret_iva['date']
                ret_iva['period_id'] = ret_iva['date']
        return values and wh_iva_obj.create(values)


    def action_wh_iva_create(self):
        """ Create withholding objects """
        ret_iva = []
        for inv in self:
            if inv.wh_iva_id:
                if inv.wh_iva_id.state == 'draft':
                    pass
                    #inv.wh_iva_id.compute_amount_wh()
                else:
                    raise UserError(
                        _('Advertencia!\nYa tiene un documento de retención asociado a '
                          'su factura, pero este documento de retención no está en'
                          'estado cancelado.'))
            else:
                # Create Lines Data
                ret_id = {}
                journal = 0
                acc_id = 0
                ret_line_id = inv.wh_iva_line_create()
                fortnight_wh_id = inv.get_fortnight_wh_id()
                # Add line to a WH DOC
                if fortnight_wh_id:
                    # Add to an exist WH Doc
                    ret_id = fortnight_wh_id
                    if not ret_id:
                        raise UserError(
                            _('Error!\nNo se puede encontrar el documento de retención'))
                    wh_iva = self.env['account.wh.iva'].browse(ret_id)
                    wh_iva.write({'wh_lines': [(4, ret_line_id.id)]})
                else:
                    # Create a New WH Doc and add line
                    type_invoice = ''
                    wh_iva_obj = self.env['account.wh.iva']
                    rp_obj = self.env['res.partner']
                    values = {}

                    for inv_brw in self:
                        acc_part_id = rp_obj._find_accounting_partner(inv_brw.partner_id)
                        if inv_brw.move_type in ('out_invoice', 'out_refund', '_out_debit'):
                            acc_id = acc_part_id.property_account_receivable_id.id
                        elif inv_brw.move_type in ('in_invoice', 'in_refund', '_in_debit'):
                            acc_id = acc_part_id.property_account_payable_id.id

                        if inv_brw.move_type in ('out_invoice', 'out_refund'):
                            if inv_brw.debit_origin_id and inv_brw.move_type == 'out_invoice':
                                type_invoice = 'out_debit'
                                journal = acc_part_id.purchase_sales_id.id
                            elif not inv_brw.debit_origin_id and inv_brw.move_type in ('out_invoice', 'out_refund'):
                                type_invoice = inv_brw.move_type
                                journal = acc_part_id.purchase_sales_id.id
                            values = {'name': _('IVA WH CLIENTE - ORIGIN %s' % (inv_brw.name)),
                                      'type': type_invoice,
                                      'account_id': acc_id,
                                      'partner_id': acc_part_id.id,
                                      'journal_id': journal,
                                      'date_ret': inv_brw.date,
                                      'period_id': inv_brw.date,
                                      'date': inv_brw.date,
                                      }
                        else:
                            if inv_brw.move_type in ('in_invoice', 'in_refund'):
                                if inv_brw.move_type == 'in_invoice' and inv_brw.debit_origin_id:
                                    type_invoice = 'in_debit'
                                    journal = acc_part_id.purchase_journal_id.id
                                elif not inv_brw.debit_origin_id and inv_brw.move_type in ('in_refund', 'in_invoice'):
                                    type_invoice = inv_brw.move_type
                                    journal = acc_part_id.purchase_journal_id.id

                            if not acc_id:
                                raise UserError(
                                    _('Invalid Action !\nYou need to configure the partner with'
                                      ' withholding accounts!'))
                            values = {'name': _('IVA WH - ORIGIN %s' % (inv_brw.supplier_invoice_number)),
                                      'type': type_invoice,
                                      'account_id': acc_id,
                                      'journal_id': journal,
                                      'partner_id': acc_part_id.id,
                                      'date_ret': inv_brw.date,
                                      'period_id': inv_brw.date,
                                      'date': inv_brw.date,
                                     }
                        if inv_brw.company_id.propagate_invoice_date_to_vat_withholding:
                            ret_iva['date'] = inv_brw.invoice_date
                            ret_iva['date_ret'] = ret_iva['date']
                            ret_iva['period_id'] = ret_iva['date']


                    ret_id =  wh_iva_obj.create(values)


                    ret_id.write({'wh_lines': [(4, ret_line_id.id)]})
                    if hasattr(ret_id, 'id'): ret_id = ret_id.id
                    if ret_id:
                        inv.write({'wh_iva_id': ret_id})
                        inv.wh_iva_id.compute_amount_wh()

        return True


    def button_reset_taxes_ret(self):
        """ Recalculate taxes in invoice
        """
        account_invoice_tax = self.env['account.tax']
        for inv in self:
            compute_taxes_ret = account_invoice_tax.compute_amount_ret(inv)
            for tax in account_invoice_tax.browse(compute_taxes_ret.keys()):
                tax.write(compute_taxes_ret[tax.id])
        return True


    def button_reset_taxes(self):
        """ It makes two function calls related taxes reset
        """
        res = super(AccountMove, self).button_reset_taxes()
        self.button_reset_taxes_ret()
        return res


    def _withholding_partner(self):
        """ I verify that the provider retains or not
        """
        # No VAT withholding Documents are created for customer invoice &
        # refunds
        for inv in self:
            if inv.move_type in ('in_invoice', 'in_refund', 'out_invoice', 'out_refund') and \
                    self.env['res.partner']._find_accounting_partner(
                        inv.company_id.partner_id).wh_iva_agent:
                return True
        return False


    def _withholdable_tax(self):
        """ Verify that existing withholding in invoice
        """
        is_withholdable = False
        for inv in self.line_ids:
            for tax in inv.tax_ids:
                if tax.type_tax == 'iva':
                    is_withholdable = True
        return is_withholdable
        #for inv in self:
        #    if inv.tax_line_ids.tax_id.type_tax == 'iva':
        #        return True
        #return False


    def check_withholdable(self):
        """ This will test for Refund invoice trying to find out
        if its regarding parent is in the same fortnight.

        return True if invoice is type 'in_invoice'
        return True if invoice is type 'in_refund' and parent_id invoice
                are both in the same fortnight.
        return False otherwise
        """
        #period = self.env['account.period']
        for inv in self:
            if inv.move_type == 'in_invoice':
                return True
            if inv.move_type == 'out_invoice':
                return True

            '''
            if inv.move_type == 'in_refund' and inv.parent_id:
                dt_refund = inv.invoice_date or time.strftime('%Y-%m-%d')
                dt_invoice = inv.parent_id.invoice_date
                return period.find_fortnight(dt_refund) == period.find_fortnight(dt_invoice)
            '''
        return False


    def check_wh_apply(self):
        """ Apply withholding to the invoice
        """
        wh_apply = []
        for inv in self:
            if inv.vat_apply or inv.sin_cred:
                return False
            wh_apply.append(inv._withholdable_tax())
            wh_apply.append(inv._withholding_partner())
        return all(wh_apply)

    def _get_move_lines1(self, to_wh, journal_id, writeoff_account_id, writeoff_journal_id,
                          date,name):
        """ Generate move lines in corresponding account
        @param to_wh: whether or not withheld
        @param period_id: Period
        @param pay_journal_id: pay journal of the invoice
        @param writeoff_acc_id: account where canceled
        @param writeoff_period_id: period where canceled
        @param writeoff_journal_id: journal where canceled
        @param date: current date
        @param name: description
        """

        # res = super(AccountMove, self)._get_move_lines(to_wh, journal_id, writeoff_account_id, writeoff_journal_id, date,name)
        res = []
        acc = None
        for invoice in self:
            acc_part_id = \
                self.env['res.partner']._find_accounting_partner(
                    invoice.partner_id)

            types = {'out_invoice': -1,
                     'in_invoice': 1,
                     'out_refund': 1,
                     'in_refund': -1}
            direction = types[invoice.move_type]

            amount_ret2 = 0
            for tax_brw in to_wh:
                #if 'in_invoice' in invoice.move_type:
                    #acc = (tax_brw.tax_id.account_id and
                     #      tax_brw.tax_id.account_id.id or
                     #      False)
                    #acc = (tax_brw.wh_vat_line_id.retention_id.journal_id.default_iva_account.id and
                    #       tax_brw.wh_vat_line_id.retention_id.journal_id.default_iva_account.id or
                    #      False)
                #elif 'in_refund' in invoice.move_type:
                acc = (tax_brw.wh_vat_line_id.retention_id.journal_id.default_iva_account.id and
                           tax_brw.wh_vat_line_id.retention_id.journal_id.default_iva_account.id or
                           False)
                if not acc:
                    raise UserError(
                        ("¡Falta una cuenta en impuestos!\n El impuesto [% s] tiene una cuenta faltante. Por favor, complete el "
                          "campos faltantes") % (tax_brw.name))
                amount_ret2 += tax_brw.amount_ret
            res.append((0, 0, {
                'debit':
                    direction * amount_ret2 < 0 and
                    direction * amount_ret2,
                'credit':
                    direction * amount_ret2 > 0 and
                    direction * amount_ret2,
                'account_id': acc,
                'partner_id': acc_part_id.id,
                'ref': invoice.name,
                'date': date,
                'name': name,
                'amount_residual': direction * amount_ret2,
                'currency_id': invoice.company_id.currency_id.id,
            }))
            #self.residual = self.residual - tax_brw.amount_ret
            #self.residual_company_signed = self.residual_company_signed - tax_brw.amount_ret
        return res

    def validate_wh_iva_done(self):
        """ Method that check if wh vat is validated in invoice refund.
        @params: ids: list of invoices.
        return: True: the wh vat is validated.
                False: the wh vat is not validated.
        """
        for inv in self:
            if inv.move_type in ('out_invoice', 'out_refund') and not inv.wh_iva_id:
                riva = True
            else:
                riva = (not inv.wh_iva_id and True or
                        inv.wh_iva_id.state in ('posted') and True or False)
                if not riva:
                    raise UserError(
                        _('Error !\n¡La retención de IVA "% s" no está validada!' %
                          inv.wh_iva_id.code))
        return True


    def button_generate_wh_doc(self):
        context = dict(self._context)
        partner = self.env['res.partner']
        res = {}
        for inv in self:
            view_id = self.env['ir.ui.view'].search([
                ('name', '=', 'account.move._invoice,'
                              'wh.iva.customer')])
            context.update({
                'invoice_id': inv.id,
                'type': inv.move_type,
                'default_partner_id': partner._find_accounting_partner(
                    inv.partner_id).id,
                'default_name': inv.name,
                'view_id': view_id.id,
                'date_ret': inv.invoice_date,
                'date': inv.date,
            })
            res = {
                'name': _('Withholding vat customer'),
                'type': 'ir.actions.act_window',
                'res_model': 'account.wh.iva',
                'view_type': 'form',
                'view_id': False,
                'view_mode': 'form',
                'nodestroy': True,
                'target': 'current',
                'domain': "[('type', '=', '" + inv.move_type + "')]",
                'context': context
            }
        return res


    def action_cancel(self):
        """ Verify first in the invoice have a fiscal book associated and if
                        the state of the book is in cancel. """

        for inv_brw in self.browse():
            if not (not inv_brw.fb_id or (inv_brw.fb_id and inv_brw.fb_id.state == 'cancel')):
                raise UserError(
                    "Error! \n No puede cancelar una factura cargada en un Libro Fiscal procesado (%s). Necesitas ir a Libro fiscal y configure el libro en Cancelar. Entonces se podría cancelar la factura." % (
                        inv_brw.fb_id.state))


        """ Verify first if the invoice have a non cancel withholding iva doc.
        If it has then raise a error message. """
        for inv in self:
            if ((not inv.wh_iva_id) or (
                    inv.wh_iva_id and
                    inv.wh_iva_id.state == 'cancel')):
                super(AccountMove, self).action_cancel()
            else:
                raise UserError(
                    _("Error!\nNo puede cancelar una factura que no se encuentra cancelado"
                      "el doocumento de retención. Primero debe cancelar la factura"
                      "documento de retención y luego puede cancelar esto"
                      "factura"))
        return True

    # BEGIN OF REWRITING ISLR
    def check_invoice_type(self):
        """ This method check if the given invoice record is from a supplier
        """
        context = self._context or {}
        ids = isinstance(self.ids, (int)) and [self.ids] or self.ids
        inv_brw = self.browse(ids)
        return inv_brw.move_type in ('in_invoice', 'in_refund')

    def check_withholdable_concept(self):
        """ Check if the given invoice record is ISLR Withholdable
        """
        context = self._context or {}
        ids = isinstance(self.ids, (int)) and [self.ids] or self.ids
        '''Generate a new windows to change the income wh concept in current
        invoice line'''
        iwdi_obj = self.env['account.wh.islr.doc.invoices']
        return iwdi_obj._get_concepts(ids)

    @api.model
    def _create_doc_invoices(self, islr_wh_doc_id):
        """ This method link the invoices to be withheld
        with the withholding document.
        """
        # TODO: CHECK IF THIS METHOD SHOULD BE HERE OR IN THE ISLR WH DOC
        context = self._context or {}
        ids = isinstance(self.ids, (int)) and [self.ids] or self.ids
        doc_inv_obj = self.env['account.wh.islr.doc.invoices']
        iwhdi_ids = []
        for inv_id in ids:
            iwhdi_ids.append(doc_inv_obj.create(
                {'invoice_id': inv_id,
                 'islr_wh_doc_id': islr_wh_doc_id.id}))
        return iwhdi_ids

    @api.model
    def _create_islr_wh_doc(self):
        """ Function to create in the model islr_wh_doc
        """
        context = dict(self._context or {})
        ids = isinstance(self.ids, (int)) and [self.ids] or self.ids

        wh_doc_obj = self.env['account.wh.islr.doc']
        rp_obj = self.env['res.partner']

        # row = self.browse(ids)
        acc_part_id = rp_obj._find_accounting_partner(self.partner_id)

        res = False
        if not (self.move_type in ('out_invoice', 'in_invoice','out_refund', 'in_refund') and rp_obj._find_accounting_partner(
                self.company_id.partner_id).islr_withholding_agent):
            return True

        context['type'] = self.move_type
        wh_ret_code = wh_doc_obj.retencion_seq_get()

        if wh_ret_code:
            journal = wh_doc_obj._get_journal(self.partner_id)

            acc_part_id = rp_obj._find_accounting_partner(self.partner_id)
            if self.move_type in ('out_invoice', 'out_refund'):
                acc_id = acc_part_id.property_account_receivable_id.id
                wh_type = 'out_invoice'
            else:
                acc_id = acc_part_id.property_account_payable_id.id
                wh_type = 'in_invoice'
            values = {
                'name': wh_ret_code,  # TODO (REVISAR)_('IVA WH - ORIGIN %s' %(inv_brw.number)),
                'partner_id': acc_part_id.id,
                #   'period_id': row.period_id.id,
                'account_id': acc_id,
                'type': self.move_type,
                'journal_id': journal.id,
                'date_uid': self.date,
                'company_id': self.company_id.id,
                'date_ret': self.date
            }
            if self.company_id.propagate_invoice_date_to_income_withholding:
                values['date_uid'] = self.invoice_date

            islr_wh_doc_id = wh_doc_obj.create(values)
            iwdi_id = self._create_doc_invoices(islr_wh_doc_id)

            self.env['account.wh.islr.doc'].compute_amount_wh([islr_wh_doc_id])

            if self.company_id.automatic_income_wh is True:
                wh_doc_obj.write(
                    {'automatic_income_wh': True})
        else:
            raise UserError("Invalid action! \nNo se ha encontrado el numero de secuencia.")

        return islr_wh_doc_id

    def _refund_cleanup_lines(self, lines):
        """ Initializes the fields of the lines of a refund invoice
        """
        result = super(AccountMove, self)._refund_cleanup_lines(lines)
        for i, line in enumerate(lines):
            for name, field in line._fields.items():
                if name == 'concept_id' or name == 'apply_wh' or name == 'wh_xml_id':
                    result[i][2][name] = False
                # if name == 'apply_wh':
                #    result[i][2][name] = False
                # if name == 'wh_xml_id':
                #    result[i][2][name] = False
        # for xres, yres, zres in result:
        #    if 'concept_id' in zres:
        #        zres['concept_id'] = zres.get(
        #            'concept_id', False) and zres['concept_id']
        #    if 'apply_wh' in zres:
        #        zres['apply_wh'] = False
        #    if 'wh_xml_id' in zres:
        #        zres['wh_xml_id'] = 0
        #    result.append((xres, yres, zres))
        return result

    def validate_wh_income_done(self):
        """ Method that check if wh income is validated in invoice refund.
        @params: ids: list of invoices.
        return: True: the wh income is validated.
                False: the wh income is not validated.
        """
        for inv in self.browse():
            if inv.move_type in ('out_invoice', 'out_refund') \
                    and not inv.islr_wh_doc_id:
                rislr = True
            else:
                rislr = not inv.islr_wh_doc_id and True or \
                        inv.islr_wh_doc_id.state in (
                            'done') and True or False
                if not rislr:
                    raise UserError(
                        "Error! \nThe Document you are trying to refund has a income withholding %s which is not yet validated!" % (
                            inv.islr_wh_doc_id.code))
        return True

    @api.model
    def _get_move_lines2(self,
                         to_wh,
                         pay_journal_id,
                         writeoff_acc_id,
                         writeoff_journal_id,
                         date,
                         name):
        """ Generate move lines in corresponding account
        @param to_wh: whether or not withheld
        @param period_id: Period
        @param pay_journal_id: pay journal of the invoice
        @param writeoff_acc_id: account where canceled
        @param writeoff_period_id: period where canceled
        @param writeoff_journal_id: journal where canceled
        @param date: current date
        @param name: description
        """
        context = self._context or {}
        rp_obj = self.env['res.partner']
        ids = isinstance(self.ids, (int)) and [self.ids] or self.ids
        # res = super(AccountMove, self)._get_move_lines(to_wh,
        #                                                   pay_journal_id,
        #                                                   writeoff_acc_id,
        #                                                   writeoff_journal_id,
        #                                                   date,
        #                                                   name)
        res = []
        if not context.get('income_wh', False):
            return res

        inv_brw = self.browse(ids)
        acc_part_id = rp_obj._find_accounting_partner(inv_brw.partner_id)

        types = {'out_invoice': -1, 'in_invoice': 1, 'out_refund': 1,
                 'in_refund': -1, 'entry': 1}
        direction = types[inv_brw.move_type]

        for iwdl_brw in to_wh:
            rec = iwdl_brw.islr_wh_doc_id.journal_id.default_islr_account
            # concept_id.property_retencion_islr_receivable
            pay = iwdl_brw.islr_wh_doc_id.journal_id.default_islr_account
            if inv_brw.move_type in ('out_invoice', 'out_refund'):
                acc = rec and rec.id or False
            else:
                acc = pay and pay.id or False
            if not acc:
                raise UserError(
                    "Falta la cuenta en el impuesto! \nEl diario de [%s] tiene las cuentas faltantes. Por favor, rellene los campos que faltan para poder continuar" % (
                        iwdl_brw.islr_wh_doc_id.journal_id.name))

            res.append((0, 0, {
                'debit': direction * iwdl_brw.amount < 0 and - direction *
                         iwdl_brw.amount,
                'credit': direction * iwdl_brw.amount > 0 and direction *
                          iwdl_brw.amount,
                'account_id': acc,
                'partner_id': acc_part_id.id,
                'ref': inv_brw.display_name,
                'date': date,
                'currency_id': inv_brw.company_id.currency_id.id,
                'name': name.strip() + ' - ISLR: ' + iwdl_brw.iwdi_id.islr_wh_doc_id.name.strip()
            }))
        return res

    # # REMPLAZANDO EL ORIGINAL PARA PREVALECER EL CONCEPTO DE ISLR AL GUARDAR
    # @api.model
    # def _move_autocomplete_invoice_lines_create(self, vals_list):
    #     ''' During the create of an account.move with only 'invoice_line_ids' set and not 'line_ids', this method is called
    #     to auto compute accounting lines of the invoice. In that case, accounts will be retrieved and taxes, cash rounding
    #     and payment terms will be computed. At the end, the values will contains all accounting lines in 'line_ids'
    #     and the moves should be balanced.
    #
    #     :param vals_list:   The list of values passed to the 'create' method.
    #     :return:            Modified list of values.
    #     '''
    #     print('entra por aquiiiiiii')
    #     new_vals_list = []
    #     for vals in vals_list:
    #         vals = dict(vals)
    #         if vals.get('invoice_line_ids'):
    #             if vals.get('line_ids'):
    #                 list = []
    #                 lines = vals.get('line_ids')
    #                 invoices = vals.get('invoice_line_ids')
    #                 for line in lines:
    #                     for inv in invoices:
    #                         if inv[1] == line[1]:
    #                             list.append(inv)
    #                         else:
    #                             var = 0
    #                             for li in list:
    #                                 if li[1] == line[1]:
    #                                     var = 1
    #                             if var != 1:
    #                                 var2 = 0
    #                                 for a in invoices:
    #                                     if a[1] == line[1]:
    #                                         var2 = 1
    #                                 if var2 != 1:
    #                                     list.append(line)
    #                 vals['line_ids'] = list
    #         if vals.get('invoice_date') and not vals.get('date'):
    #             vals['date'] = vals['invoice_date']
    #
    #         default_move_type = vals.get('move_type') or self._context.get('default_move_type')
    #         ctx_vals = {}
    #         if default_move_type:
    #             ctx_vals['default_move_type'] = default_move_type
    #         if vals.get('journal_id'):
    #             ctx_vals['default_journal_id'] = vals['journal_id']
    #         self_ctx = self.with_context(**ctx_vals)
    #         vals = self_ctx._add_missing_default_values(vals)
    #
    #         is_invoice = vals.get('move_type') in self.get_invoice_types(include_receipts=True)
    #
    #         if 'line_ids' in vals:
    #             vals.pop('invoice_line_ids', None)
    #             new_vals_list.append(vals)
    #             continue
    #
    #         if is_invoice and 'invoice_line_ids' in vals:
    #             vals['line_ids'] = vals['invoice_line_ids']
    #
    #         vals.pop('invoice_line_ids', None)
    #
    #         move = self_ctx.new(vals)
    #         new_vals_list.append(move._move_autocomplete_invoice_lines_values())
    #
    #     return new_vals_list

    def llenar(self):
        temporal = self.env['account.move.line.resumen'].search([])
        temporal.with_context(force_delete=True).unlink()

        movimientos = self.env['account.move'].search([('move_type', '!=', 'entry'), ('state', '=', 'posted')])
        for det_m in movimientos:

            if det_m.move_type == 'in_invoice' or det_m.move_type == 'in_refund' or det_m.move_type == 'in_receipt':
                type_tax_use = 'purchase'
                porcentaje_ret = det_m.company_id.partner_id.wh_iva_rate
            if det_m.move_type == 'out_invoice' or det_m.move_type == 'out_refund' or det_m.move_type == 'out_receipt':
                type_tax_use = 'sale'
                porcentaje_ret = det_m.partner_id.wh_iva_rate
            if det_m.move_type == 'in_invoice' or det_m.move_type == 'out_invoice':
                tipo_doc = "01"
            if det_m.move_type == 'in_refund' or det_m.move_type == 'out_refund':
                tipo_doc = "03"
            if det_m.move_type == 'in_receipt' or det_m.move_type == 'out_receipt':
                tipo_doc = "02"

            if det_m.move_type in ('in_invoice', 'in_refund', 'in_receipt', 'out_receipt', 'out_refund', 'out_invoice'):
                lista_impuesto = det_m.env['account.tax'].search([('type_tax_use', '=', type_tax_use)])
                # ('aliquot','not in',('general','exempt')
                base = 0
                total = 0
                total_impuesto = 0
                total_exento = 0
                alicuota_adicional = 0
                alicuota_reducida = 0
                alicuota_general = 0
                base_general = 0
                base_reducida = 0
                base_adicional = 0
                retenido_general = 0
                retenido_reducida = 0
                retenido_adicional = 0
                valor_iva = 0

                for det_tax in lista_impuesto:
                    tipo_alicuota = det_tax.appl_type

                    # raise UserError(_('tipo_alicuota: %s')%tipo_alicuota)
                    det_lin = det_m.invoice_line_ids.search([('tax_ids', '=', det_tax.id), ('move_id', '=', det_m.id)])
                    if det_lin:
                        for det_fac in det_lin:  # USAR AQUI ACOMULADORES
                            if det_m.state != "cancel":
                                base = base + det_fac.price_subtotal
                                total = total + det_fac.price_total
                                id_impuesto = det_fac.tax_ids.id
                                total_impuesto = total_impuesto + (det_fac.price_total - det_fac.price_subtotal)
                                if tipo_alicuota == "general":
                                    alicuota_general = alicuota_general + (det_fac.price_total - det_fac.price_subtotal)
                                    base_general = base_general + det_fac.price_subtotal
                                    valor_iva = det_fac.tax_ids.amount
                                if tipo_alicuota == "exento":
                                    total_exento = total_exento + det_fac.price_subtotal
                                if tipo_alicuota == "reducido":
                                    alicuota_reducida = alicuota_reducida + (
                                                det_fac.price_total - det_fac.price_subtotal)
                                    base_reducida = base_reducida + det_fac.price_subtotal
                                if tipo_alicuota == "adicional":
                                    alicuota_adicional = alicuota_adicional + (
                                                det_fac.price_total - det_fac.price_subtotal)
                                    base_adicional = base_adicional + det_fac.price_subtotal
                        total_ret_iva = (total_impuesto * porcentaje_ret) / 100
                        retenido_general = (alicuota_general * porcentaje_ret) / 100
                        retenido_reducida = (alicuota_reducida * porcentaje_ret) / 100
                        retenido_adicional = (alicuota_adicional * porcentaje_ret) / 100
                if det_m.move_type == 'in_refund' or det_m.move_type == 'out_refund':
                    base = -1 * base
                    total = -1 * total
                    total_impuesto = -1 * total_impuesto
                    alicuota_general = -1 * alicuota_general
                    valor_iva = -1 * valor_iva
                    total_exento = -1 * total_exento
                    alicuota_reducida = -1 * alicuota_reducida
                    alicuota_adicional = -1 * alicuota_adicional
                    total_ret_iva = -1 * total_ret_iva
                    base_adicional = -1 * base_adicional
                    base_reducida = -1 * base_reducida
                    base_general = -1 * base_general
                    retenido_general = -1 * retenido_general
                    retenido_reducida = -1 * retenido_reducida
                    retenido_adicional = -1 * retenido_adicional

                values = {
                    'total_con_iva': total,
                    'total_base': base,
                    'total_valor_iva': total_impuesto,
                    'tax_id': det_fac.tax_ids.id,
                    'invoice_id': det_m.id,
                    'vat_ret_id': det_m.vat_ret_id.id,
                    'nro_comprobante': det_m.vat_ret_id.name,
                    'porcentaje_ret': porcentaje_ret,
                    'total_ret_iva': total_ret_iva,
                    'type': det_m.move_type,
                    'state': det_m.state,
                    'state_voucher_iva': det_m.vat_ret_id.state,
                    'tipo_doc': tipo_doc,
                    'total_exento': total_exento,
                    'alicuota_reducida': alicuota_reducida,
                    'alicuota_adicional': alicuota_adicional,
                    'alicuota_general': alicuota_general,
                    'fecha_fact': det_m.date,
                    'fecha_comprobante': det_m.vat_ret_id.voucher_delivery_date,
                    'base_adicional': base_adicional,
                    'base_reducida': base_reducida,
                    'base_general': base_general,
                    'retenido_general': retenido_general,
                    'retenido_reducida': retenido_reducida,
                    'retenido_adicional': retenido_adicional,
                }
                det_m.env['account.move.line.resumen'].create(values)

    def suma_alicuota_iguales_iva(self):
        # raise UserError(_('xxx = %s')%self.wh_iva_id)
        for rec in self:
            if rec.move_type == 'in_invoice' or rec.move_type == 'in_refund' or rec.move_type == 'in_receipt':
                type_tax_use = 'purchase'
                porcentaje_ret = self.company_id.partner_id.wh_iva_rate
            if rec.move_type == 'out_invoice' or rec.move_type == 'out_refund' or rec.move_type == 'out_receipt':
                type_tax_use = 'sale'
                porcentaje_ret = self.partner_id.wh_iva_rate
            if rec.move_type == 'in_invoice' or rec.move_type == 'out_invoice':
                tipo_doc = "01"
            if rec.move_type == 'in_refund' or rec.move_type == 'out_refund':
                tipo_doc = "03"
            if rec.move_type == 'in_receipt' or rec.move_type == 'out_receipt':
                tipo_doc = "02"

            if rec.move_type in ('in_invoice', 'in_refund', 'in_receipt', 'out_receipt', 'out_refund', 'out_invoice'):
                # ****** AQUI VERIFICA SI LAS LINEAS DE FACTURA TIENEN ALICUOTAS *****
                verf = self.invoice_line_ids.filtered(
                lambda line: line.display_type not in ('line_section', 'line_note'))
                # raise UserError(_('verf= %s')%verf)
                for det_verf in verf:
                    # raise UserError(_('det_verf.tax_ids.id= %s')%det_verf.tax_ids.id)
                    if not det_verf.tax_ids:
                        raise UserError(_('Las Lineas de la Factura deben tener un tipo de alicuota o impuestos'))
                # ***** FIN VERIFICACION
                lista_impuesto = self.env['account.tax'].search([('type_tax_use', '=', type_tax_use),('type_tax','=','iva')])
                # ('aliquot','not in',('general','exempt')
                base = 0
                total = 0
                total_impuesto = 0
                total_exento = 0
                alicuota_adicional = 0
                alicuota_reducida = 0
                alicuota_general = 0
                base_general = 0
                base_reducida = 0
                base_adicional = 0
                retenido_general = 0
                retenido_reducida = 0
                retenido_adicional = 0
                valor_iva = 0

                for det_tax in lista_impuesto:
                    tipo_alicuota = det_tax.appl_type

                    # raise UserError(_('tipo_alicuota: %s')%tipo_alicuota)
                    if det_tax.type_tax == 'iva':
                        det_lin = self.invoice_line_ids.search([('tax_ids', 'in', det_tax.id)])
                        if det_lin:
                            for det_fac in det_lin:  # USAR AQUI ACOMULADORES
                                if self.state != "cancel":
                                    base = base + det_fac.price_subtotal
                                    total = total + det_fac.price_total
                                    total_impuesto = total_impuesto + (det_fac.price_total - det_fac.price_subtotal)
                                    if tipo_alicuota == "general":
                                        alicuota_general = alicuota_general + (det_fac.price_total - det_fac.price_subtotal)
                                        base_general = base_general + det_fac.price_subtotal
                                        valor_iva = det_tax.amount
                                    if tipo_alicuota == "exento":
                                        total_exento = total_exento + det_fac.price_subtotal
                                    if tipo_alicuota == "reducido":
                                        alicuota_reducida = alicuota_reducida + (det_fac.price_total - det_fac.price_subtotal)
                                        base_reducida = base_reducida + det_fac.price_subtotal
                                    if tipo_alicuota == "adicional":
                                        alicuota_adicional = alicuota_adicional + (det_fac.price_total - det_fac.price_subtotal)
                                        base_adicional = base_adicional + det_fac.price_subtotal
                            total_ret_iva = (total_impuesto * porcentaje_ret) / 100
                            retenido_general = (alicuota_general * porcentaje_ret) / 100
                            retenido_reducida = (alicuota_reducida * porcentaje_ret) / 100
                            retenido_adicional = (alicuota_adicional * porcentaje_ret) / 100

                            if self.move_type == 'in_refund' or self.move_type == 'out_refund':
                                base = -1 * base
                                total = -1 * total
                                total_impuesto = -1 * total_impuesto
                                alicuota_general = -1 * alicuota_general
                                valor_iva = -1 * valor_iva
                                total_exento = -1 * total_exento
                                alicuota_reducida = -1 * alicuota_reducida
                                alicuota_adicional = -1 * alicuota_adicional
                                total_ret_iva = -1 * total_ret_iva
                                base_adicional = -1 * base_adicional
                                base_reducida = -1 * base_reducida
                                base_general = -1 * base_general
                                retenido_general = -1 * retenido_general
                                retenido_reducida = -1 * retenido_reducida
                                retenido_adicional = -1 * retenido_adicional

                            values = {
                                'total_con_iva': total,  # listo
                                'total_base': base,  # listo
                                'total_valor_iva': total_impuesto,  # listo
                                'tax_id': det_tax.id,
                                'invoice_id': self.id,
                                'vat_ret_id': self.wh_iva_id.id,
                                'nro_comprobante': self.wh_iva_id.name,
                                'porcentaje_ret': porcentaje_ret,
                                'total_ret_iva': total_ret_iva,
                                'type': self.move_type,
                                'state': self.state,
                                'state_voucher_iva': self.wh_iva_id.state,
                                'tipo_doc': tipo_doc,
                                'total_exento': total_exento,  # listo
                                'alicuota_reducida': alicuota_reducida,  # listo
                                'alicuota_adicional': alicuota_adicional,  # listo
                                'alicuota_general': alicuota_general,  # listo
                                'fecha_fact': self.date,
                                'fecha_comprobante': self.wh_iva_id.date,
                                'base_adicional': base_adicional,  # listo
                                'base_reducida': base_reducida,  # listo
                                'base_general': base_general,  # listo
                                'retenido_general': retenido_general,
                                'retenido_reducida': retenido_reducida,
                                'retenido_adicional': retenido_adicional,
                            }
                            self.env['account.move.line.resumen'].create(values)

                # raise UserError(_('valor_iva= %s')%valor_iva)

    def button_draft(self):
        super().button_draft()
        for selff in self:
            temporal = selff.env['account.move.line.resumen'].search([('invoice_id', '=', selff.id)])
            temporal.with_context(force_delete=True).unlink()
