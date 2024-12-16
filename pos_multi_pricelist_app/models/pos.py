# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from functools import partial

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT


class currency(models.Model):
    _inherit = 'res.currency'

    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)
    converted_currency = fields.Float('Currency', compute="_onchange_currency")

    @api.depends('company_id')
    def _onchange_currency(self):
        res_currency = self.env['res.currency'].search([])
        company_currency = self.env.user.company_id.currency_id
        for i in self:
            rate = (round(i.rate, 6) / company_currency.rate)
            i.converted_currency = rate


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    converted_currency = fields.Float('Currency', related='currency_id.converted_currency')
    rate = fields.Float('Currency', related='currency_id.rate')


class PosPayment(models.Model):
    _inherit = "pos.payment"

    amount_currency = fields.Float(string="Currency Amount")
    currency = fields.Many2one("res.currency", string="Currency")


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    currency_id = fields.Many2one("res.currency", 'Currency', compute='_compute_currency')

    def _compute_currency(self):
        for pm in self:
            pm.currency_id = pm.company_id.currency_id.id
            if pm.journal_id and pm.journal_id.currency_id:
                pm.currency_id = pm.journal_id.currency_id.id


class POSSession(models.Model):
    _inherit = 'pos.session'

    def _pos_ui_models_to_load(self):
        result = super()._pos_ui_models_to_load()
        result.extend(['product.pricelist.item'])
        return result

    def _loader_params_product_pricelist_item(self):
        return {
            'search_params': {
                'domain': [('pricelist_id', 'in', self.config_id.available_pricelist_ids.ids)],
                'fields': [],
            }
        }

    def _get_pos_ui_product_pricelist_item(self, params):
        return self.env['product.pricelist.item'].search_read(**params['search_params'])

    def load_pos_data(self):
        loaded_data = {}
        self = self.with_context(loaded_data=loaded_data)
        for model in self._pos_ui_models_to_load():
            loaded_data[model] = self._load_model(model)
        self._pos_data_process(loaded_data)
        users_data = self._get_pos_ui_pos_res_currency(self._loader_params_pos_res_currency())
        loaded_data['currencies'] = users_data
        return loaded_data

    def _loader_params_pos_res_currency(self):
        return {
            'search_params': {
                'domain': [],
                'fields': ['name', 'symbol', 'position', 'rounding', 'rate', 'decimal_places', 'converted_currency'],
            },
        }

    def _get_pos_ui_pos_res_currency(self, params):
        currencies = self.env['res.currency'].search_read(**params['search_params'])
        return currencies

    def _loader_params_pos_payment_method(self):
        result = super()._loader_params_pos_payment_method()
        result['search_params']['fields'].append('currency_id')
        return result

    def _loader_params_product_pricelist(self):
        result = super()._loader_params_product_pricelist()
        result['search_params']['fields'].extend(['currency_id','rate' ,'converted_currency'])
        return result


    def _loader_params_product_product(self):
        result = super()._loader_params_product_product()
        result['search_params']['fields'].extend(['company_id'])
        return result


class POSOrder(models.Model):
    _inherit = "pos.order"

    amount_total = fields.Float(string='Total', digits=0, required=True)
    amount_paid = fields.Float(string='Paid', digits=0, required=True)

    def _is_pos_order_paid(self):
        if (abs(self.amount_total - self.amount_paid) < 0.02):
            self.write({'amount_total': self.amount_paid})
            return True
        else:
            return False

    @api.model
    def _payment_fields(self, order, ui_paymentline):
        payment_total = []
        company_id = self.env.user.company_id
        payment_date = ui_paymentline['name']
        payment_date = fields.Date.context_today(self, fields.Datetime.from_string(payment_date))
        price_unit_foreign_curr = 0.0

        price_unit_comp_curr = ui_paymentline['amount'] or 0.0
        currency_id = False

        if order.pricelist_id.currency_id.id != order.currency_id.id:
            # Convert
            price_unit_foreign_curr = ui_paymentline['amount']
            price_unit_comp_curr = order.pricelist_id.currency_id._convert(price_unit_foreign_curr, order.currency_id,
                                                                           order.company_id, payment_date)
            currency_id = order.pricelist_id.currency_id.id
            price_unit_comp_curr = price_unit_comp_curr

        return {
            'amount_currency': price_unit_foreign_curr,
            'currency': currency_id,
            'amount': price_unit_comp_curr or 0.0,
            'payment_date': ui_paymentline['name'],
            'payment_method_id': ui_paymentline['payment_method_id'],
            'card_type': ui_paymentline.get('card_type'),
            'cardholder_name': ui_paymentline.get('cardholder_name'),
            'transaction_id': ui_paymentline.get('transaction_id'),
            'payment_status': ui_paymentline.get('payment_status'),
            'pos_order_id': order.id,
        }

    @api.model
    def _order_fields(self, ui_order):
        amount_total = []
        amt_total = ui_order['amount_total']
        amt_paid = ui_order['amount_paid']

        if ui_order['lines']:
            pos_session = self.env['pos.session'].browse(ui_order.get('pos_session_id'))
            pricelist_id = self.env['product.pricelist'].browse(ui_order.get('pricelist_id'))
            payment_date = fields.Date.today()
            if pos_session.currency_id.id != pricelist_id.currency_id.id:
                for line in ui_order['lines']:
                    price_unit_foreign_curr = line[2].get('price_unit') or 0.0
                    price_unit_comp_curr = pricelist_id.currency_id._convert(price_unit_foreign_curr,
                                                                             pos_session.currency_id,
                                                                             pos_session.company_id, payment_date)
                    price_subtotal_foreign_curr = line[2].get('price_subtotal') or 0.0
                    price_subtotal_comp_curr = pricelist_id.currency_id._convert(price_subtotal_foreign_curr,
                                                                                 pos_session.currency_id,
                                                                                 pos_session.company_id, payment_date)
                    price_subtotal_incl_foreign_curr = line[2].get('price_subtotal_incl') or 0.0
                    price_subtotal_incl_comp_curr = pricelist_id.currency_id._convert(price_subtotal_incl_foreign_curr,
                                                                                      pos_session.currency_id,
                                                                                      pos_session.company_id,
                                                                                      payment_date)
                    line[2].update({
                        'price_unit': price_unit_comp_curr,
                        'price_subtotal': price_subtotal_comp_curr,
                        'price_subtotal_incl': price_subtotal_incl_comp_curr,
                    })
                    amount_total.append(price_subtotal_incl_comp_curr)
                amount_total_foreign_curr = ui_order.get('amount_total')
                amount_total_comp_curr = pricelist_id.currency_id._convert(amount_total_foreign_curr,
                                                                           pos_session.currency_id,
                                                                           pos_session.company_id, payment_date)
                ui_order.update({'amount_total': sum(amount_total)})
                amt_total = sum(amount_total)
                amt_paid = sum(amount_total)
        process_line = partial(self.env['pos.order.line']._order_line_fields, session_id=ui_order['pos_session_id'])
        return {
            'user_id': ui_order['user_id'] or False,
            'session_id': ui_order['pos_session_id'],
            'lines': [process_line(l) for l in ui_order['lines']] if ui_order['lines'] else False,
            'pos_reference': ui_order['name'],
            'sequence_number': ui_order['sequence_number'],
            'partner_id': ui_order['partner_id'] or False,
            'date_order': ui_order['creation_date'].replace('T', ' ')[:19],
            'fiscal_position_id': ui_order['fiscal_position_id'],
            'pricelist_id': ui_order['pricelist_id'],
            'amount_paid': amt_paid,
            'amount_total': amt_total,
            'amount_tax': ui_order['amount_tax'],
            'amount_return': ui_order['amount_return'],
            'company_id': self.env['pos.session'].browse(ui_order['pos_session_id']).company_id.id,
            'to_invoice': ui_order['to_invoice'] if "to_invoice" in ui_order else False,
            'is_tipped': ui_order.get('is_tipped', False),
            'tip_amount': ui_order.get('tip_amount', 0),
        }

    def _process_payment_lines(self, pos_order, order, pos_session, draft):
        """Create account.bank.statement.lines from the dictionary given to the parent function.

        If the payment_line is an updated version of an existing one, the existing payment_line will first be
        removed before making a new one.
        :param pos_order: dictionary representing the order.
        :type pos_order: dict.
        :param order: Order object the payment lines should belong to.
        :type order: pos.order
        :param pos_session: PoS session the order was created in.
        :type pos_session: pos.session
        :param draft: Indicate that the pos_order is not validated yet.
        :type draft: bool.
        """
        prec_acc = order.pricelist_id.currency_id.decimal_places
        pricelist_id = self.env['product.pricelist'].browse(pos_order.get('pricelist_id'))
        order_bank_statement_lines = self.env['pos.payment'].search([('pos_order_id', '=', order.id)])
        order_bank_statement_lines.unlink()
        payment_date = fields.Date.today()
        for payments in pos_order['statement_ids']:
            if not float_is_zero(payments[2]['amount'], precision_digits=prec_acc):
                order.add_payment(self._payment_fields(order, payments[2]))

        order.amount_paid = sum(order.payment_ids.mapped('amount'))

        currency_id = False
        amt_currncy = 0.0
        price_subtotal_comp_curr = pos_order['amount_return']
        if pos_session.currency_id.id != pricelist_id.currency_id.id:
            price_subtotal_comp_curr = pricelist_id.currency_id._convert(pos_order['amount_return'],
                                                                         pos_session.currency_id,
                                                                         pos_session.company_id, payment_date)
            currency_id = order.pricelist_id.currency_id.id
            amt_currncy = -pos_order['amount_return']
        if not draft and not float_is_zero(pos_order['amount_return'], prec_acc):
            cash_payment_method = pos_session.payment_method_ids.filtered('is_cash_count')[:1]
            if not cash_payment_method:
                raise UserError(_("No cash statement found for this session. Unable to record returned cash."))
            return_payment_vals = {
                'name': _('return'),
                'pos_order_id': order.id,
                'amount_currency': amt_currncy,
                'currency': currency_id,
                'amount': -price_subtotal_comp_curr,
                'payment_date': fields.Datetime.now(),
                'payment_method_id': cash_payment_method.id,
                'is_change': True,
            }
            order.add_payment(return_payment_vals)


class POSConfig(models.Model):
    _inherit = 'pos.config'

    @api.constrains('pricelist_id', 'use_pricelist', 'available_pricelist_ids', 'journal_id', 'invoice_journal_id',
                    'payment_method_ids')
    def _check_currencies(self):
        for config in self:
            if config.use_pricelist and config.pricelist_id not in config.available_pricelist_ids:
                raise ValidationError(_("The default pricelist must be included in the available pricelists."))

        if self.invoice_journal_id.currency_id and self.invoice_journal_id.currency_id != self.currency_id:
            raise ValidationError(
                _("The invoice journal must be in the same currency as the Sales Journal or the company currency if that is not set."))

        if any(
                self.payment_method_ids \
                        .filtered(lambda pm: pm.is_cash_count) \
                        .mapped(
                    lambda pm: self.currency_id not in (self.company_id.currency_id | pm.journal_id.currency_id))
        ):
            raise ValidationError(
                _("All payment methods must be in the same currency as the Sales Journal or the company currency if that is not set."))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: