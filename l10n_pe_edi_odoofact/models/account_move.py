# -*- coding: utf-8 -*-
###############################################################################
#
#    Copyright (C) 2019-TODAY OPeru.
#    Author      :  Grupo Odoo S.A.C. (<http://www.operu.pe>)
#
#    This program is copyright property of the author mentioned above.
#    You can`t redistribute it and/or modify it.
#
###############################################################################

import logging
from datetime import datetime
from num2words import num2words

from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError


_logger = logging.getLogger(__name__)

CURRENCY = {
    "PEN": 1,        # Soles
    "USD": 2,        # Dollars
    "EUR": 3,        # Euros
}

class AccountMove(models.Model): 
    _inherit = "account.move"
  
    l10n_pe_edi_operation_type = fields.Selection(
        [
            ("1", "INTERNAL SALE"),
            ("2", "EXPORTATION"),
            ("3", "NON-DOMICILED"),
            ("4", "INTERNAL SALE - ADVANCES"),
            ("5", "ITINERANT SALE"),
            ("6", "GUIDE INVOICE"),
            ("7", "SALE PILADO RICE"),
            ("8", "INVOICE - PROOF OF PERCEPTION"),
            ("10", "INVOICE - SENDING GUIDE"),
            ("11", "INVOICE - CARRIER GUIDE"),
            ("12", "SALES TICKET - PROOF OF PERCEPTION"),
            ("13", "NATURAL PERSON DEDUCTIBLE EXPENSE"),
        ],
        string="Transaction type",
        help="Default 1, the others are for very special types of operations, do not hesitate to consult with us for more information",
        default="1"
    )
    l10n_latam_document_type_id = fields.Many2one(copy=True, compute='_get_l10n_latam_document_type_id', readonly=False, store=True, help="Select the Journal account to change the document type.")
    l10n_pe_edi_internal_type = fields.Selection(
        [('invoice', 'Invoices'), ('debit_note', 'Debit Notes'), ('credit_note', 'Credit Notes')], index=True, compute='_get_l10n_pe_edi_internal_type', help='Analog to odoo account.move.type but with more options allowing to identify the kind of document we are'
        ' working with. (not only related to account.move, could be for documents of other models like stock.picking)', store=True)
    l10n_pe_edi_reversal_type_id = fields.Many2one('l10n_pe_edi.catalog.09', string='Credit note type', help='Catalog 09: Type of Credit note')
    l10n_pe_edi_debit_type_id = fields.Many2one('l10n_pe_edi.catalog.10', string='Debit note type', help='Catalog 10: Type of Debit note')  
    l10n_pe_edi_cancel_reason = fields.Char(
        string="Cancel Reason", copy=False,
        help="Reason given by the user to cancel this move")    
    l10n_pe_edi_ose_accepted = fields.Boolean('Sent to PSE/OSE', related='l10n_pe_edi_request_id.ose_accepted', store=True)
    l10n_pe_edi_request_id = fields.Many2one('l10n_pe_edi.request', string='PSE/OSE request', copy=False)
    l10n_pe_edi_response = fields.Text('Response', related='l10n_pe_edi_request_id.response', store=True) 
    l10n_pe_edi_multishop = fields.Boolean('Multi-Shop', related='company_id.l10n_pe_edi_multishop')
    l10n_pe_edi_cron_count = fields.Integer('Cron count available', default=5, help='Number of attempts available for sending electronic invoices by the Cron')
    l10n_pe_edi_shop_id = fields.Many2one('l10n_pe_edi.shop', string='Shop', related='journal_id.l10n_pe_edi_shop_id', store=True)
    l10n_pe_edi_sunat_accepted = fields.Boolean('Accepted by SUNAT', related='l10n_pe_edi_request_id.sunat_accepted', store=True) 
    
    # ==== Business fields ====
    l10n_pe_edi_serie = fields.Char(string='E-invoice Serie', compute='_get_einvoice_number', store=True)
    l10n_pe_edi_number = fields.Integer(string='E-invoice Number', compute='_get_einvoice_number', store=True)
    l10n_pe_edi_service_order = fields.Char(string='Purchase/Service order', help='This Purchase/service order will be shown on the electronic invoice')
    l10n_pe_edi_picking_number_ids = fields.One2many('l10n_pe_edi.picking.number', 'invoice_id', string='Picking numbers')
    l10n_pe_edi_reversal_type = fields.Selection([("1","Factura"),("2","Boleta")], string='Document type', help='Used for Credit and debit note', readonly=False)
    l10n_pe_edi_reversal_serie = fields.Char(string='Document serie', help='Used for Credit and debit note', readonly=False)
    l10n_pe_edi_reversal_number = fields.Char(string='Document number', help='Used for Credit and debit note', readonly=False)
    l10n_pe_edi_reversal_date = fields.Date(string='Document date', help='Date of the Credit or debit note', readonly=False)
    l10n_pe_edi_is_advance = fields.Boolean(string='Is Advance', compute='_get_is_advance', store=True)
    l10n_pe_edi_is_sale_credit = fields.Boolean(string="Sale on Credit", compute='_get_is_sale_credit', store=True)
    l10n_pe_edi_dues_ids = fields.One2many('l10n_pe_edi.dues', 'move_id', string='Dues', copy=False)

    # === Amount fields ===
    l10n_pe_edi_amount_subtotal = fields.Monetary(string='Subtotal',store=True, readonly=True, compute='_compute_edi_amount', compute_sudo=True, tracking=True, help='Total without discounts and taxes')
    l10n_pe_edi_amount_discount = fields.Monetary(string='Total Discount', store=True, readonly=True, compute='_compute_edi_amount', compute_sudo=True, tracking=True)    
    l10n_pe_edi_amount_base = fields.Monetary(string='Base Amount', store=True, readonly=True, compute='_compute_edi_amount', compute_sudo=True, tracking=True, help='Total with discounts and before taxes')
    l10n_pe_edi_amount_advance = fields.Monetary(string='Advance Amount', store=True, readonly=True, compute='_compute_edi_amount', compute_sudo=True, tracking=True)
    l10n_pe_edi_amount_exonerated = fields.Monetary(string='Exonerated  Amount', store=True, compute='_compute_edi_amount', compute_sudo=True, tracking=True)
    l10n_pe_edi_amount_free = fields.Monetary(string='Free Amount', store=True, compute='_compute_edi_amount', compute_sudo=True, tracking=True)
    l10n_pe_edi_amount_unaffected = fields.Monetary(string='Unaffected Amount', store=True, compute='_compute_edi_amount', compute_sudo=True, tracking=True)      
    l10n_pe_edi_amount_untaxed = fields.Monetary(string='Total before taxes', store=True, compute='_compute_edi_amount', compute_sudo=True, tracking=True, help='Total before taxes, all discounts included')   
    l10n_pe_edi_global_discount = fields.Monetary(string='Global discount', store=True, readonly=True, compute='_compute_edi_amount', compute_sudo=True, tracking=True)  
    l10n_pe_edi_amount_in_words = fields.Char(string="Amount in Words", compute='_l10n_pe_edi_amount_in_words')
    
    # ==== Tax fields ====
    l10n_pe_edi_igv_percent = fields.Integer(string="Percentage IGV", compute='_get_percentage_igv')
    l10n_pe_edi_amount_icbper = fields.Monetary(string='ICBPER Amount', compute='_compute_edi_amount', compute_sudo=True, tracking=True)
    l10n_pe_edi_amount_igv = fields.Monetary(string='IGV Amount', compute='_compute_edi_amount', compute_sudo=True, tracking=True)
    l10n_pe_edi_amount_isc = fields.Monetary(string='ISC Amount', store=True, compute='_compute_edi_amount', compute_sudo=True, tracking=True)
    l10n_pe_edi_amount_others = fields.Monetary(string='Other charges', compute='_compute_edi_amount', compute_sudo=True, tracking=True)  
    l10n_pe_edi_is_einvoice = fields.Boolean('Is E-invoice', related='journal_id.l10n_pe_edi_is_einvoice', store=True)

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.company_id.country_id.code == 'PE' and self.partner_id.country_id and self.partner_id.country_id.code != 'PE':
            self.l10n_pe_edi_operation_type = '2'
        else:
            self.l10n_pe_edi_operation_type = '1'
        return super(AccountMove, self)._onchange_partner_id()
    
    @api.depends('move_type','journal_id')
    def _get_l10n_latam_document_type_id(self):
        for move in self:
            if move.move_type in ['out_invoice','out_refund'] and move.journal_id:    
                move.l10n_latam_document_type_id = move.journal_id.l10n_latam_document_type_id
            else:
                move.l10n_latam_document_type_id = False
    
    @api.depends('l10n_latam_document_type_id','journal_id')
    def _get_l10n_pe_edi_internal_type(self):
        for move in self:
            if move.move_type in ['out_invoice','out_refund'] and move.l10n_latam_document_type_id:
                move.l10n_pe_edi_internal_type = move.l10n_latam_document_type_id.internal_type
            else:
                move.l10n_pe_edi_internal_type = False

    @api.depends(
        'line_ids.debit',
        'line_ids.credit',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.l10n_pe_edi_regularization_advance',
        'amount_by_group')
    def _compute_edi_amount(self):
        for move in self:
            total_untaxed = 0.0
            total_untaxed_currency = 0.0
            l10n_pe_edi_global_discount = 0.0
            l10n_pe_edi_amount_discount = 0.0
            l10n_pe_edi_amount_subtotal = 0.0
            l10n_pe_edi_amount_advance = 0.0
            #~ E-invoice amounts
            l10n_pe_edi_amount_free = 0.0
            currencies = set()

            if move.move_type == 'entry' or move.is_outbound():
                sign = 1
            else:
                sign = -1

            for line in move.line_ids:
                if line.currency_id:
                    currencies.add(line.currency_id)
                if move.is_invoice(include_receipts=True):
                    # === Invoices ===
                    # If the amount is negative, is considerated as global discount
                    l10n_pe_edi_global_discount += not line.l10n_pe_edi_regularization_advance and line.l10n_pe_edi_price_base < 0 and abs(line.l10n_pe_edi_price_base) or 0.0
                    # If the product is not free, it calculates the amount discount 
                    l10n_pe_edi_amount_discount += line.l10n_pe_edi_free_product == False and (line.l10n_pe_edi_price_base * line.discount)/100 or 0.0
                    # If the price_base is > 0, sum to the total without taxes and discounts
                    l10n_pe_edi_amount_subtotal += line.l10n_pe_edi_price_base > 0 and line.l10n_pe_edi_price_base or 0.0
                    # Free product amount
                    l10n_pe_edi_amount_free += line.l10n_pe_edi_amount_free
                    # If regularization advance is true, is considerated as advance
                    l10n_pe_edi_amount_advance += line.l10n_pe_edi_regularization_advance and line.l10n_pe_edi_price_base or 0.0
                # Affected by IGV
                if not line.exclude_from_invoice_tab and any(tax.l10n_pe_edi_tax_code in ['1000'] for tax in line.tax_ids):
                    # Untaxed amount.
                    total_untaxed += line.balance
                    total_untaxed_currency += line.amount_currency
            move.l10n_pe_edi_amount_base = sign * (total_untaxed_currency if len(currencies) == 1 else total_untaxed)
            # move.l10n_pe_edi_amount_base = sum([x[2] for x in move.amount_by_group if x[0] not in ['INA','EXO','EXP']])
            # Sum of Amount base of the lines where it has any Tax with code '9997'  (Exonerated)
            move.l10n_pe_edi_amount_exonerated = sum([x.l10n_pe_edi_price_base for x in move.invoice_line_ids if any(tax.l10n_pe_edi_tax_code in ['9997'] for tax in x.tax_ids)])
            # Sum of Amount base of the lines where it has any Tax with code in ['9998','9995']  (Unaffected and exportation)
            move.l10n_pe_edi_amount_unaffected = sum([x.l10n_pe_edi_price_base for x in move.invoice_line_ids if any(tax.l10n_pe_edi_tax_code in ['9998','9995'] for tax in x.tax_ids)])
            move.l10n_pe_edi_amount_igv = sum([x[1] for x in move.amount_by_group if x[0] == 'IGV'])
            move.l10n_pe_edi_amount_isc = sum([x[1] for x in move.amount_by_group if x[0] == 'ISC'])
            move.l10n_pe_edi_amount_icbper = sum([x[1] for x in move.amount_by_group if x[0] == 'ICBPER'])
            move.l10n_pe_edi_amount_others = sum([x[1] for x in move.amount_by_group if x[0] == 'OTROS'])
            move.l10n_pe_edi_amount_untaxed = move.l10n_pe_edi_amount_base - move.l10n_pe_edi_amount_free
            # TODO Global discount
            move.l10n_pe_edi_amount_advance = l10n_pe_edi_amount_advance
            move.l10n_pe_edi_global_discount = l10n_pe_edi_global_discount
            move.l10n_pe_edi_amount_discount = l10n_pe_edi_global_discount + l10n_pe_edi_amount_discount
            move.l10n_pe_edi_amount_subtotal = l10n_pe_edi_amount_subtotal
            move.l10n_pe_edi_amount_free = l10n_pe_edi_amount_free

    @api.depends('amount_total','currency_id')
    def _l10n_pe_edi_amount_in_words(self):
        """Transform the amount to text
        """
        for move in self:
            amount_base, amount = divmod(move.amount_total, 1)
            amount = round(amount, 2)
            amount = int(round(amount * 100, 2))

            lang_code = self.env.context.get('lang') or self.env.user.lang
            lang = self.env['res.lang'].search([('code', '=', lang_code)])
            words = num2words(amount_base, lang=lang.iso_code)
            result = _('%(words)s WITH %(amount)02d/100 %(currency_label)s') % {
                'words': words,
                'amount': amount,
                'currency_label': move.currency_id.name == 'PEN' and 'SOLES' or move.currency_id.currency_unit_label,
            }
            move.l10n_pe_edi_amount_in_words = result.upper()

    @api.depends('name')
    def _get_einvoice_number(self):
        for move in self:
            if move.name and move.move_type in ['out_invoice','out_refund']:
                inv_number = move.name.split('-')
                if len(inv_number) == 2:
                     move.l10n_pe_edi_serie = inv_number[0]
                     move.l10n_pe_edi_number = inv_number[1]
        return True
    
    @api.depends('invoice_line_ids', 'invoice_line_ids.product_id')
    def _get_is_advance(self):
        self.l10n_pe_edi_is_advance = False
        for move in self:
            for line in move.invoice_line_ids:
                if line.product_id and line.product_id.l10n_pe_edi_is_for_advance:
                    move.l10n_pe_edi_is_advance = True
                    break
    
    @api.depends('invoice_payment_term_id', 'invoice_date', 'invoice_date_due')
    def _get_is_sale_credit(self):
        for move in self:
            l10n_pe_edi_is_sale_credit = False
            if move.l10n_latam_document_type_id.code == '01' and move.move_type == 'out_invoice':
                if any(
                    line.date_maturity > (move.invoice_date or fields.Date.today())
                    for line in move.line_ids.filtered(lambda x: x.exclude_from_invoice_tab and x.date_maturity)
                ):
                    l10n_pe_edi_is_sale_credit = True
            move.l10n_pe_edi_is_sale_credit = l10n_pe_edi_is_sale_credit
    
    @api.onchange('l10n_pe_edi_is_sale_credit')    
    def _get_dues_ids(self):
        if self.l10n_pe_edi_is_sale_credit:
            self.l10n_pe_edi_dues_ids = False
            number = 0
            dues = []
            for line in self.line_ids.filtered(lambda x: x.exclude_from_invoice_tab and x.date_maturity != False and x.debit > 0.0):
                number += 1
                amount = abs(line.amount_currency)
                vals = {
                    'move_id': self.id,
                    'dues_number': number,
                    'paid_date': line.date_maturity,
                    'amount': amount,
                }
                dues.append((0,0,vals))
            self.l10n_pe_edi_dues_ids = dues
    
    def _onchange_after_recompute_dynamic_lines(self):
        self._get_dues_ids()
    
    @api.onchange('line_ids', 'invoice_payment_term_id', 'invoice_date_due', 'invoice_date', 'invoice_cash_rounding_id', 'invoice_vendor_bill_id')
    def _onchange_recompute_dynamic_lines(self):
        super(AccountMove, self)._onchange_recompute_dynamic_lines()
        self._onchange_after_recompute_dynamic_lines()
    
    @api.depends('amount_by_group')
    def _get_percentage_igv(self):
        for move in self:
            igv = 0.0
            tax_igv_group_id = self.env['account.tax.group'].search([('name','=','IGV')], limit=1)
            if tax_igv_group_id:
                tax_id = self.env['account.tax'].search([('tax_group_id','=',tax_igv_group_id.id)], limit=1)
                if tax_id:
                    igv = int(tax_id.amount)
            move.l10n_pe_edi_igv_percent = igv
        return True
    
    def get_reversal_origin_data(self):    
        for move in self: 
            if move.move_type in ['out_invoice','out_refund']:
                if move.debit_origin_id:
                        move.l10n_pe_edi_reversal_type = move.debit_origin_id.l10n_pe_edi_serie and move.debit_origin_id.l10n_pe_edi_serie[0] == "F" and "1" or "2"
                        move.l10n_pe_edi_reversal_serie = move.debit_origin_id.l10n_pe_edi_serie
                        move.l10n_pe_edi_reversal_number = move.debit_origin_id.l10n_pe_edi_number
                        move.l10n_pe_edi_reversal_date = move.debit_origin_id.invoice_date
                if move.reversed_entry_id:
                        move.l10n_pe_edi_reversal_type = move.reversed_entry_id.l10n_pe_edi_serie and move.reversed_entry_id.l10n_pe_edi_serie[0] == "F" and "1" or "2"
                        move.l10n_pe_edi_reversal_serie = move.reversed_entry_id.l10n_pe_edi_serie
                        move.l10n_pe_edi_reversal_number = move.reversed_entry_id.l10n_pe_edi_number
                        move.l10n_pe_edi_reversal_date = move.reversed_entry_id.invoice_date                      

    def action_post(self):
        # Restart the Number of attempts available for sending electronic invoices by the Cron
        for move in self:
            move.l10n_pe_edi_cron_count = 5
            if move.move_type in ['out_invoice', 'out_refund', 'out_receipt'] and move.l10n_pe_edi_is_einvoice:
                if move.amount_total > 700 and not move.partner_id.vat:
                    raise UserError(_('Please Define the Customer Document Number.'))
                
                if move.l10n_pe_edi_is_advance and move.l10n_pe_edi_operation_type != '4':
                    raise UserError(_('The field Transaction Type must be advance because you are using an advance type product.'))
        super(AccountMove, self).action_post()

    def _get_invoice_values_odoofact(self):
        """
        Prepare the dict of values to create the request for electronic invoice. Valid for Nubefact.
        """
        if not self.l10n_latam_document_type_id:
            raise UserError(_('Please define Edocument type on this invoice.'))
        currency = CURRENCY.get(self.currency_id.name, False)
        if not currency:
            raise UserError(_('Currency \'%s, %s\' is not available for Electronic invoice. Contact to the Administrator.') %(self.currency_id.name, self.currency_id.currency_unit_label))
        currency_exchange = self.currency_id.with_context(date=self.invoice_date)._get_conversion_rate(self.company_id.currency_id, self.currency_id, self.env.user.company_id,self.invoice_date)
        if currency_exchange == 0:
            raise UserError(_('The currency rate should be different to 0.0, Please check the rate at %s' ) % self.invoice_date) 
        values = {
            'company_id': self.company_id.id,
            'l10n_pe_edi_shop_id': self.l10n_pe_edi_shop_id and self.l10n_pe_edi_shop_id.id or False,
            'invoice_id': self.id,
            "operacion": "generar_comprobante",
            'tipo_de_comprobante': self.l10n_latam_document_type_id.type_of,
            'serie': self.l10n_pe_edi_serie, 
            'numero': str(self.l10n_pe_edi_number),
            'sunat_transaction': int(self.l10n_pe_edi_operation_type),
            'cliente_tipo_de_documento': self.partner_id.commercial_partner_id.l10n_latam_identification_type_id and self.partner_id.commercial_partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code or '1',
            'cliente_numero_de_documento': self.partner_id.commercial_partner_id.vat and self.partner_id.commercial_partner_id.vat or '00000000',
            'cliente_denominacion': self.partner_id.commercial_partner_id.name or self.partner_id.commercial_partner_id.name,
            'cliente_direccion': (self.partner_id.street_name or '') \
                                + (self.partner_id.street_number or '') \
                                + (self.partner_id.street_number2 or '') \
                                + (self.partner_id.street2 or '') \
                                + (self.partner_id.l10n_pe_district and ', ' + self.partner_id.l10n_pe_district.name or '') \
                                + (self.partner_id.city_id and ', ' + self.partner_id.city_id.name or '') \
                                + (self.partner_id.state_id and ', ' + self.partner_id.state_id.name or '') \
                                + (self.partner_id.country_id and ', ' + self.partner_id.country_id.name or ''),
            'cliente_email': self.partner_id.email and self.partner_id.email or self.partner_id.email,
            'fecha_de_emision': datetime.strptime(str(self.invoice_date), "%Y-%m-%d").strftime("%d-%m-%Y"),
            'fecha_de_vencimiento': self.invoice_date_due and datetime.strptime(str(self.invoice_date_due), "%Y-%m-%d").strftime("%d-%m-%Y") or '',
            'moneda': currency,
            'tipo_de_cambio': round(1/currency_exchange,3),
            'porcentaje_de_igv': self.l10n_pe_edi_igv_percent,
            'descuento_global': abs(self.l10n_pe_edi_global_discount),
            'total_descuento': abs(self.l10n_pe_edi_amount_discount),
            'total_anticipo': abs(self.l10n_pe_edi_amount_advance),
            'total_gravada': abs(self.l10n_pe_edi_amount_base),
            'total_inafecta': abs(self.l10n_pe_edi_amount_unaffected),
            'total_exonerada': abs(self.l10n_pe_edi_amount_exonerated),
            'total_igv': abs(self.l10n_pe_edi_amount_igv),
            'total_gratuita': abs(self.l10n_pe_edi_amount_free),
            'total_otros_cargos': abs(self.l10n_pe_edi_amount_others),
            'total_isc': abs(self.l10n_pe_edi_amount_isc),
            'total': abs(self.amount_total),
            'total_impuestos_bolsas': abs(self.l10n_pe_edi_amount_icbper),
            'observaciones': self.narration or '',
            'documento_que_se_modifica_tipo': self.l10n_pe_edi_reversal_type and int(self.l10n_pe_edi_reversal_type) or '',
            'documento_que_se_modifica_serie': self.l10n_pe_edi_reversal_serie or '',
            'documento_que_se_modifica_numero': self.l10n_pe_edi_reversal_number or '',
            'tipo_de_nota_de_credito': self.l10n_pe_edi_reversal_type_id and int(self.l10n_pe_edi_reversal_type_id.code) or '',
            'tipo_de_nota_de_debito': self.l10n_pe_edi_debit_type_id and int(self.l10n_pe_edi_debit_type_id.code) or '',
            'enviar_automaticamente_al_cliente': self.journal_id.l10n_pe_edi_send_to_client and 'true' or 'false',
            'codigo_unico': '%s|%s|%s-%s' %('odoo',self.company_id.partner_id.vat,self.l10n_pe_edi_serie,str(self.l10n_pe_edi_number)),
            'condiciones_de_pago': self.invoice_payment_term_id and self.invoice_payment_term_id.name or '',
            'medio_de_pago': self.l10n_pe_edi_is_sale_credit and 'venta_al_credito' or '',
            "orden_compra_servicio": self.l10n_pe_edi_service_order or '',
            "generado_por_contingencia": self.journal_id.l10n_pe_edi_contingency and 'true' or 'false',
            'items': getattr(self,'_get_invoice_line_values_%s' % self._get_ose_supplier())(self.invoice_line_ids),
            'guias': getattr(self,'_get_invoice_picking_values_%s' % self._get_ose_supplier())(self.l10n_pe_edi_picking_number_ids),
            'venta_al_credito': getattr(self,'_get_dues_values_%s' % self._get_ose_supplier())(self.l10n_pe_edi_dues_ids),
            'provider': 'odoo',
            }
        return values
    
    def _get_invoice_line_values_odoofact(self, lines):
        """
        Prepare the dict of values to create the request lines for electronic invoice. Valid for Nubefact.
        """
        res = []
        for line in lines:
            if line.display_type == False:
                # sign = line.move_id.move_type in ['in_refund', 'out_refund'] and -1 or 1
                if line.price_subtotal < 0 and not line.l10n_pe_edi_regularization_advance:
                    continue
                values = {
                    'unidad_de_medida': line.product_uom_id and 
                                        (line.product_uom_id.l10n_pe_edi_uom_code_id and line.product_uom_id.l10n_pe_edi_uom_code_id.code or False) or 
                                        (line.product_id and (line.product_id.type != 'service' and 'NIU' or 'ZZ') or 'ZZ'),
                    'codigo': line.product_id and line.product_id.default_code or '',
                    'descripcion': line.name,
                    'cantidad': abs(line.quantity),
                    'valor_unitario': abs(line.l10n_pe_edi_price_unit_excluded),
                    'precio_unitario': abs(line.l10n_pe_edi_price_unit_included),
                    'descuento': abs(line.l10n_pe_edi_amount_discount),
                    'subtotal': abs(line.l10n_pe_edi_amount_free if line.l10n_pe_edi_free_product else line.price_subtotal),
                    'tipo_de_igv': line.l10n_pe_edi_igv_type.code_of,
                    'igv': abs(line.l10n_pe_edi_igv_amount),
                    "impuesto_bolsas": abs(line.l10n_pe_edi_icbper_amount),
                    'total': abs(line.l10n_pe_edi_amount_free if line.l10n_pe_edi_free_product else line.price_total),
                    'anticipo_regularizacion': line.l10n_pe_edi_regularization_advance and 'true' or 'false',
                    'anticipo_documento_serie': line.l10n_pe_edi_regularization_advance and line.l10n_pe_edi_advance_serie or '',
                    'anticipo_documento_numero': line.l10n_pe_edi_regularization_advance and str(line.l10n_pe_edi_advance_number) or '',
                    'codigo_producto_sunat': line.product_id.l10n_pe_edi_product_code_id and line.product_id.l10n_pe_edi_product_code_id.code or '',
                    "tipo_de_isc": line.l10n_pe_edi_isc_type and line.l10n_pe_edi_isc_type.code or '',
                    "isc": abs(line.l10n_pe_edi_isc_amount),
                    }
                res.append(values)
        return res
    
    def _get_invoice_picking_values_odoofact(self, pick_numbers):
        data = []
        for pick in pick_numbers:
            values = {
                'guia_tipo': int(pick.type),
                'guia_serie_numero': pick.name
            }
            data.append(values)
        return data
    
    def _get_dues_values_odoofact(self, dues):
        data = []
        if self.l10n_pe_edi_is_sale_credit:
            for due in dues:
                data.append({
                    'cuota': due.dues_number,
                    'fecha_de_pago': datetime.strptime(str(due.paid_date), "%Y-%m-%d").strftime("%d-%m-%Y"),
                    'importe': abs(due.amount),
                })
        return data
    
    def _get_ose_supplier(self):
        """
        Get the PSE/OSE provider code for the electronic invoice. Example: 'odoofact' for Nubefact
        :returns: supplier code
        """
        if not self.company_id.l10n_pe_edi_ose_id:
            raise RedirectWarning(_('Please select a PSE/OSE supplier for the company %s')%(self.company_id.name,),
                                                    self.env.ref('base.action_res_company_form').id,
                                                    _('Congifure company'),)
        return self.company_id.l10n_pe_edi_ose_id.code
    
    def action_document_send(self):
        """ 
        This method creates the request to PSE/OSE provider 
        """
        for move in self:
            if not move.company_id.l10n_pe_edi_send_invoice:
                raise UserError(_('The company %s is not active for send electronic invoices. Please check the configuration.')%(move.company_id.name))
            if not move.l10n_pe_edi_is_einvoice:
                raise UserError(_('The invoice is not a Electronic document' ))
        
            if move.state == 'draft':
                continue
            if move.company_id.l10n_pe_edi_multishop and not move.l10n_pe_edi_shop_id:
                raise UserError(_("Review the Journal configuration and select a shop: \n Journal: %s")% (move.journal_id.name))
            
            # Get invoice data depending of PSE/OSE supplier
            ose_supplier = move._get_ose_supplier()
            vals = getattr(move,'_get_invoice_values_%s' % ose_supplier)()
            if not move.l10n_pe_edi_request_id:
                l10n_pe_edi_request_id = move.env['l10n_pe_edi.request'].create({
                    'company_id': move.company_id.id,
                    'document_number': move.name, 
                    'l10n_pe_edi_shop_id': move.l10n_pe_edi_shop_id and move.l10n_pe_edi_shop_id.id or False,
                    'model': move._name, 
                    'res_id': move.id, 
                    'type': 'invoice', 
                    'document_date': move.invoice_date})
                move.write({'l10n_pe_edi_request_id': l10n_pe_edi_request_id})
            else:
                l10n_pe_edi_request_id = move.l10n_pe_edi_request_id
            if not move.l10n_pe_edi_ose_accepted:
                l10n_pe_edi_request_id.action_api_connect(vals)
            else:
                move.action_document_check()
    
    def _get_invoice_values_check_odoofact(self):
        """
        Prepare the dict of values to create the request for checking the document status. Valid for Nubefact.
        """
        self.ensure_one()
        values = {
            'company_id': self.company_id.id,
            'l10n_pe_edi_shop_id': self.l10n_pe_edi_shop_id and self.l10n_pe_edi_shop_id.id or False,
            'operacion': 'consultar_comprobante',                
            'tipo_de_comprobante': self.l10n_latam_document_type_id.type_of,
            'serie': self.l10n_pe_edi_serie,
            'numero': str(self.l10n_pe_edi_number)
        }
        return values
    
    def _get_invoice_cancel_values_odoofact(self):
        """
        Prepare the dict of values to create the request for cancelation the document status. Valid for Nubefact.
        """
        self.ensure_one()
        values = {
            'company_id': self.company_id.id,
            'l10n_pe_edi_shop_id': self.l10n_pe_edi_shop_id and self.l10n_pe_edi_shop_id.id or False,
            'operacion': 'generar_anulacion',
            'tipo_de_comprobante': self.l10n_latam_document_type_id.type_of,
            'motivo': self._context.get('reason',_('Null document')), 
            'serie': self.l10n_pe_edi_serie,
            'numero': str(self.l10n_pe_edi_number), 
            'codigo_unico': '%s|%s|%s-%s' %('odoo',self.company_id.partner_id.vat,self.l10n_pe_edi_serie,str(self.l10n_pe_edi_number)),
        }
        return values
    
    def action_document_send_cancel(self):
        ''' Cancel the invoice and send the cancelation request for electronic invoice '''
        for move in self:
            ose_supplier = move._get_ose_supplier()
            # Send invoice if it hasn't sent
            if not move.l10n_pe_edi_request_id:
                move.action_document_send()
            if move.payment_state == 'paid':
                raise UserError(_("It's not possible to cancel a paid invoice. Please add a credit note or cancel the payments before."))
            # Send cancelled invoice
            vals = getattr(move,'_get_invoice_cancel_values_%s' % ose_supplier)() 
            move.l10n_pe_edi_request_id.action_api_connect(vals)          
            # Check invoice status 
            if move.l10n_pe_edi_request_id.with_context(check_cancel=True).ose_accepted:
                move.action_document_check(cancel=True) 
            if move.l10n_pe_edi_ose_accepted and move.l10n_pe_edi_sunat_accepted:       
                move.write({'l10n_pe_edi_cancel_reason': self._context.get('reason',_('Null document'))}) 
                # Cancel invoice (Odoo method)
                move.button_cancel() 
            if move.state == 'cancel':
                message = _("Invoice <span style='color: #21b799;'>%s-%s</span> nulled by SUNAT") % (move.l10n_pe_edi_serie,str(move.l10n_pe_edi_number))
                move.message_post(body=message)
            else:
                raise UserError(_("It's not possible to cancel the invoice. Please check the log details \n Invoice: %s-%s \n Error: %s")% (move.l10n_pe_edi_serie,str(move.l10n_pe_edi_number), move.l10n_pe_edi_response))
            return True
    
    def _get_invoice_cancel_values_check_odoofact(self):
        """
        Prepare the dict of values to create the request for checking the cancelation status. Valid for Nubefact.
        """
        self.ensure_one()
        values = {    
            'company_id': self.company_id.id,
            'l10n_pe_edi_shop_id': self.l10n_pe_edi_shop_id and self.l10n_pe_edi_shop_id.id or False,
            'operacion': 'consultar_anulacion',                
            'tipo_de_comprobante': self.l10n_latam_document_type_id.type_of,
            'serie': self.l10n_pe_edi_serie,
            'numero': str(self.l10n_pe_edi_number)
        }
        return values    
    
    def action_document_check(self, cancel=False):
        """
        Send the request for Checking document status for electronic invoices
        """
        for move in self:
            # For canceled Invoices 
            ose_supplier = move._get_ose_supplier()
            if cancel:
                vals = getattr(move,'_get_invoice_cancel_values_check_%s' % ose_supplier)()
            else:
                vals = getattr(move,'_get_invoice_values_check_%s' % ose_supplier)()
            if move.l10n_pe_edi_request_id:
                move.l10n_pe_edi_request_id.action_api_connect(vals)
            elif not move.l10n_pe_edi_is_einvoice:
                continue
            else:
                move.action_document_send()
    
    # ==== Inherited methods ====
    def _reverse_move_vals(self, default_values, cancel=True):
        move_vals = super(AccountMove, self)._reverse_move_vals(default_values, cancel)        
        l10n_pe_edi_reversal_type_id = self._context.get('l10n_pe_edi_reversal_type_id', False)            
        l10n_latam_document_type_id = self._context.get('l10n_latam_document_type_id', False)
        move_vals.update(l10n_latam_document_type_id=l10n_latam_document_type_id, l10n_pe_edi_reversal_type_id=l10n_pe_edi_reversal_type_id)
        return move_vals
    
    def action_invoice_sent(self):
        """ Open a window to compose an email, with the edi invoice template
            message loaded by default
        """
        res = super(AccountMove, self).action_invoice_sent()
        template = self.env.ref('l10n_pe_edi_odoofact.email_template_edi_invoice', raise_if_not_found=False)
        if template:
            res['context'].update({'default_template_id': template and template.id or False})
        return res

    # Onchange deprecated
    def onchange_l10n_latam_document_type_id(self):  
        pass              
    
    # Onchange deprecated
    @api.onchange('l10n_latam_document_type_id', 'l10n_latam_document_number')
    def _inverse_l10n_latam_document_number(self):
        pass
    
    # Computed replaced
    @api.depends('journal_id', 'partner_id', 'company_id', 'move_type')
    def _compute_l10n_latam_available_document_types(self):
        self.l10n_latam_available_document_type_ids = self.env['l10n_latam.document.type'].search([])

    def _compute_invoice_taxes_by_group(self):
        return super(AccountMove, self)._compute_invoice_taxes_by_group()

    # Get document number
    def _get_starting_sequence(self):
        """ Create a new starting sequence using the hournal code and the
        journal document number with a 6 padding number
        Set the format F001-000001  """
        self.ensure_one()
        if self.move_type in ('entry', 'in_invoice','in_refund','in_receipt'):
            return super(AccountMove, self)._get_starting_sequence()

        starting_sequence = "%s-%06d" % (self.journal_id.code, 0)
        if self.journal_id.refund_sequence and self.move_type in ('out_refund'):
            starting_sequence = "NC" + starting_sequence
        return starting_sequence

    # For the resequence method Wizard
    def _deduce_sequence_number_reset(self, name):
        # FIXED for avoid error in sequences
        # if self.env.company.country_id.code == "PE":
        if self.env.company.country_id.code == "PE" and self.move_type not in ('entry', 'in_invoice','in_refund','in_receipt'):        
            return 'never'
        return super(AccountMove, self)._deduce_sequence_number_reset(name)
    
    def action_open_edi_request(self):
        """ 
        This method opens the EDI request 
        """
        self.ensure_one()
        if self.l10n_pe_edi_request_id:
            return {
                'name': _('EDI Request'),
                'view_mode': 'form',
                'res_model': 'l10n_pe_edi.request',
                'res_id': self.l10n_pe_edi_request_id.id,
                'type': 'ir.actions.act_window',
            }
        return True
    
    # Default invoice report for Electronic invoice
    def _get_name_invoice_report(self):
        self.ensure_one()
        if self.company_id.country_id.code == 'PE':
            return 'l10n_pe_edi_odoofact.report_invoice_document'
        return super()._get_name_invoice_report()
        
class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    
    def _get_igv_type(self):
        return self.env['l10n_pe_edi.catalog.07'].search([('code','=','10')], limit=1)
    
    # ==== Business fields ====
    l10n_pe_edi_price_base = fields.Monetary(string='Subtotal without discounts', store=True, readonly=True, currency_field='currency_id', help="Total amount without discounts and taxes")
    l10n_pe_edi_price_unit_excluded = fields.Float(string='Price unit excluded', store=True, readonly=True, digits='Product Price', help="Price unit without taxes")
    l10n_pe_edi_price_unit_included = fields.Float(string='Price unit IGV included', store=True, readonly=True, digits='Product Price', help="Price unit with IGV included")
    l10n_pe_edi_amount_discount = fields.Monetary(string='Amount discount before taxes', store=True, readonly=True, currency_field='currency_id', help='Amount discount before taxes')
    l10n_pe_edi_amount_free = fields.Float(string='Amount free', store=True, readonly=True, digits='Product Price', help='amount calculated if the line id for free product')
    l10n_pe_edi_free_product = fields.Boolean('Free', store=True, readonly=True, default=False, help='Is free product?')
    l10n_pe_edi_regularization_advance = fields.Boolean(string='Regularization Advance')
    l10n_pe_edi_advance_serie = fields.Char(string='Advance Serie')
    l10n_pe_edi_advance_number = fields.Integer(string='Advance Number')
    
    # ==== Tax fields ====    
    l10n_pe_edi_igv_type = fields.Many2one('l10n_pe_edi.catalog.07', string="Type of IGV", compute='_compute_igv_type', store=True, readonly=False)
    l10n_pe_edi_isc_type = fields.Many2one('l10n_pe_edi.catalog.08', string="Type of ISC", compute='_compute_isc_type', store=True, readonly=False)
    l10n_pe_edi_igv_amount = fields.Monetary(string='IGV amount',store=True, readonly=True, currency_field='currency_id', help="Total IGV amount")
    l10n_pe_edi_isc_amount = fields.Monetary(string='ISC amount',store=True, readonly=True, currency_field='currency_id', help="Total ISC amount")
    l10n_pe_edi_icbper_amount = fields.Monetary(string='ICBPER amount',store=True, readonly=True, currency_field='currency_id', help="Total ICBPER amount")
    
    @api.depends('tax_ids','l10n_pe_edi_free_product')
    def _compute_igv_type(self):
        for line in self:
            if line.discount >= 100.0:  
                # Discount >= 100% means the product is free and the IGV type should be 'No onerosa' and 'taxed'
                tax_free = self.env['account.tax'].search([('l10n_pe_edi_tax_code','=','9996')], limit=1)
                if tax_free:
                    tax_id = tax_free.id
                    line.tax_ids = [(6,0,[tax_id])]
                line.l10n_pe_edi_igv_type = self.env['l10n_pe_edi.catalog.07'].search([('code','=','15')], limit=1).id
                
            elif any(tax.l10n_pe_edi_tax_code in ['1000'] for tax in line.tax_ids):
                # Tax with code '1000' is IGV
                line.l10n_pe_edi_igv_type = self.env['l10n_pe_edi.catalog.07'].search([('code','=','10')], limit=1).id
            elif all(tax.l10n_pe_edi_tax_code in ['9997'] for tax in line.tax_ids):
                # Tax with code '9997' is Exonerated
                line.l10n_pe_edi_igv_type = self.env['l10n_pe_edi.catalog.07'].search([('type','=','exonerated')], limit=1).id
            elif all(tax.l10n_pe_edi_tax_code in ['9998'] for tax in line.tax_ids):
                # Tax with code '9998' is Unaffected
                line.l10n_pe_edi_igv_type = self.env['l10n_pe_edi.catalog.07'].search([('type','=','unaffected')], limit=1).id
            elif all(tax.l10n_pe_edi_tax_code in ['9995'] for tax in line.tax_ids):
                # Tax with code '9995' is for Exportation
                line.l10n_pe_edi_igv_type = self.env['l10n_pe_edi.catalog.07'].search([('type','=','exportation')], limit=1).id
            else:
                line.l10n_pe_edi_igv_type = self.env['l10n_pe_edi.catalog.07'].search([('code','=','10')], limit=1).id
    
    @api.depends('tax_ids')
    def _compute_isc_type(self):
        for line in self:
            if any(tax.l10n_pe_edi_tax_code in ['2000'] for tax in line.tax_ids):
                line.l10n_pe_edi_isc_type = line.tax_ids.filtered(lambda r: r.l10n_pe_edi_tax_code == '2000')[0].l10n_pe_edi_isc_type
            else:
                line.l10n_pe_edi_isc_type = False

    @api.model
    def _get_price_total_and_subtotal_model(self, price_unit, quantity, discount, currency, product, partner, taxes, move_type):
        ''' This method is used to compute 'price_total' & 'price_subtotal'.
        '''
        res = super(AccountMoveLine, self)._get_price_total_and_subtotal_model(price_unit, quantity, discount, currency, product, partner, taxes, move_type)
        l10n_pe_edi_price_base = quantity * price_unit
        l10n_pe_edi_price_unit_excluded = price_unit
        l10n_pe_edi_price_unit_included = price_unit
        l10n_pe_edi_igv_amount = 0.0
        l10n_pe_edi_isc_amount = 0.0
        l10n_pe_edi_icbper_amount = 0.0
        if taxes:
            # Compute taxes for all line
            taxes_res = taxes._origin.compute_all(price_unit , quantity=quantity, currency=currency, product=product, partner=partner, is_refund=move_type in ('out_refund', 'in_refund'))
            l10n_pe_edi_price_unit_excluded = l10n_pe_edi_price_unit_excluded_signed = quantity != 0 and taxes_res['total_excluded']/quantity or 0.0
            res['l10n_pe_edi_price_unit_excluded'] = l10n_pe_edi_price_unit_excluded   
            # Price unit whit all taxes included
            l10n_pe_edi_price_unit_included = l10n_pe_edi_price_unit_included_signed = quantity != 0 and taxes_res['total_included']/quantity or 0.0
            res['l10n_pe_edi_price_unit_included'] = l10n_pe_edi_price_unit_included     

            # Amount taxes after dicounts, return a dict with all taxes applied with discount incluided
            taxes_discount = taxes.compute_all(price_unit * (1 - (discount or 0.0) / 100.0), currency, quantity, product=product, partner=partner, is_refund=move_type in ('out_refund', 'in_refund'))  
            
            #~ With IGV taxes
            igv_taxes_ids = taxes.filtered(lambda r: r.tax_group_id.name == 'IGV')
            if igv_taxes_ids:
                # Compute taxes per unit
                l10n_pe_edi_price_unit_included = l10n_pe_edi_price_unit_included_signed = quantity != 0 and taxes_res['total_included']/quantity or 0.0 if igv_taxes_ids else price_unit
                res['l10n_pe_edi_price_unit_included'] = l10n_pe_edi_price_unit_included
                #~ IGV amount after discount for all line
                l10n_pe_edi_igv_amount = sum( r['amount'] for r in taxes_discount['taxes'] if r['id'] in igv_taxes_ids.ids)
            l10n_pe_edi_price_base = l10n_pe_edi_price_base_signed = taxes_res['total_excluded']
            res['l10n_pe_edi_price_base'] = l10n_pe_edi_price_base 

            #~ With ISC taxes
            isc_taxes_ids = taxes.filtered(lambda r: r.tax_group_id.name == 'ISC')
            if isc_taxes_ids:
                #~ ISC amount after discount for all line
                l10n_pe_edi_isc_amount = sum( r['amount'] for r in taxes_discount['taxes'] if r['id'] in isc_taxes_ids.ids) 

            #~ With ICBPER taxes
            icbper_taxes_ids = taxes.filtered(lambda r: r.tax_group_id.name == 'ICBPER')
            if icbper_taxes_ids:
                #~ ISC amount after discount for all line
                l10n_pe_edi_icbper_amount = sum( r['amount'] for r in taxes_discount['taxes'] if r['id'] in icbper_taxes_ids.ids) 

        #~ Free amount
        if discount >= 100.0:  
            l10n_pe_edi_igv_amount = 0.0   # When the product is free, igv = 0
            l10n_pe_edi_isc_amount = 0.0   # When the product is free, isc = 0
            l10n_pe_edi_icbper_amount = 0.0   # When the product is free, icbper = 0
            l10n_pe_edi_amount_discount = 0.0  # Although the product has 100% discount, the amount of discount in a free product is 0             
            l10n_pe_edi_free_product = True
            l10n_pe_edi_amount_free = l10n_pe_edi_price_unit_included * quantity
        else:
            l10n_pe_edi_amount_discount = (l10n_pe_edi_price_unit_excluded * discount * quantity) / 100
            l10n_pe_edi_free_product = False
            l10n_pe_edi_amount_free = 0.0
        res['l10n_pe_edi_amount_discount'] = l10n_pe_edi_amount_discount
        res['l10n_pe_edi_amount_free'] = l10n_pe_edi_amount_free
        res['l10n_pe_edi_free_product'] = l10n_pe_edi_free_product
        res['l10n_pe_edi_igv_amount'] = l10n_pe_edi_igv_amount
        res['l10n_pe_edi_isc_amount'] = l10n_pe_edi_isc_amount
        res['l10n_pe_edi_icbper_amount'] = l10n_pe_edi_icbper_amount
        return res   
