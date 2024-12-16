# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.payment'

    tax_today = fields.Float(string="Tasa", default=lambda self: self._get_default_tasa(), digits='Dual_Currency_rate')
    currency_id_dif = fields.Many2one("res.currency",
                                      string="Divisa de Referencia",
                                      default=lambda self: self.env.company.currency_id_dif )
    currency_id_company = fields.Many2one("res.currency",
                                      string="Divisa compañia",
                                      default=lambda self: self.env.company.currency_id )
    amount_local = fields.Monetary(string="Importe local", currency_field='currency_id_company')
    amount_ref = fields.Monetary(string="Importe referencia", currency_field='currency_id_dif' )
    currency_equal = fields.Boolean(compute="_currency_equal")
    move_id_dif = fields.Many2one(
        'account.move', 'Asiento contable diferencia',  # required=True,
        readonly=True,
        help="Asiento contable de diferencia en tipo de cambio")

    currency_id_name = fields.Char(related="currency_id.name")
    journal_igtf_id = fields.Many2one('account.journal', string='Diario IGTF', check_company=True)
    aplicar_igtf_divisa = fields.Boolean(string="Aplicar IGTF")
    igtf_divisa_porcentage = fields.Float('% IGTF', related='company_id.igtf_divisa_porcentage')

    mount_igtf = fields.Monetary(currency_field='currency_id', string='Importe IGTF', readonly=True,
                                 digits='Dual_Currency')

    amount_total_pagar = fields.Monetary(currency_field='currency_id', string="Total Pagar(Importe + IGTF):",
                                         readonly=True)

    move_id_igtf_divisa = fields.Many2one(
        'account.move', 'Asiento IGTF Divisa',
        readonly=True)

    def _get_default_tasa(self):
        return self.env.company.currency_id_dif.inverse_rate

    @api.onchange("date")
    def onchange_date_change_tax_today(self):
        currency_USD = self.env['res.currency'].search([('name', '=', 'USD')], limit=1)
        company_currency = self.env.company.currency_id
        self.tax_today = company_currency._get_conversion_rate(currency_USD, company_currency, self.env.company, self.date)


    @api.depends('currency_id_dif','currency_id','amount','tax_today')
    def _currency_equal(self):
        for rec in self:
            currency_equal = rec.currency_id_company != rec.currency_id
            if currency_equal:
                rec.amount_local = rec.amount * rec.tax_today
                rec.amount_ref = rec.amount
            else:
                rec.amount_local = rec.amount
                rec.amount_ref = (rec.amount / rec.tax_today) if rec.amount > 0 and rec.tax_today > 0 else 0
            rec.currency_equal = currency_equal

            if rec.aplicar_igtf_divisa:
                if rec.currency_id.name == 'USD':
                    rec.mount_igtf = rec.amount * rec.igtf_divisa_porcentage / 100
                    rec.amount_total_pagar = rec.mount_igtf + rec.amount
                else:
                    rec.mount_igtf = 0
                    rec.amount_total_pagar = rec.amount
            else:
                rec.mount_igtf = 0
                rec.amount_total_pagar = rec.amount

    def action_draft(self):
        ''' posted -> draft '''
        res = super().action_draft()
        self.move_id_dif.button_draft()
        if self.move_id_igtf_divisa:
            if self.move_id_igtf_divisa.state == 'done':
                self.move_id_igtf_divisa.button_draft()


    def action_cancel(self):
        ''' draft -> cancelled '''
        res = super().action_cancel()
        self.move_id_dif.button_cancel()
        if self.move_id_igtf_divisa:
            self.move_id_igtf_divisa.button_cancel()

    def action_post(self):
        res = super().action_post()
        ''' draft -> posted '''
        self.move_id_dif._post(soft=False)
        """Genera la retencion IGTF """
        for pago in self:
            if not pago.move_id_igtf_divisa:
                if pago.aplicar_igtf_divisa:
                    pago.register_move_igtf_divisa_payment()
            else:
                if pago.move_id_igtf_divisa.state == 'draft':
                    pago.move_id_igtf_divisa.action_post()


    def register_move_igtf_divisa_payment(self):
        '''Este método realiza el asiento contable de la comisión según el porcentaje que indica la compañía'''
        diario = self.journal_igtf_id or self.journal_id
        if not diario:
            raise ValueError(_("No se ha configurado un diario para el IGTF."))

        # Crear el asiento contable sin líneas
        vals = {
            'date': self.date,
            'journal_id': diario.id,
            'currency_id': self.currency_id.id,
            'state': 'draft',
            'tax_today': self.tax_today,
            'ref': self.ref,
            'move_type': 'entry',
        }

        move_id = self.env['account.move'].with_context(check_move_validity=False).create(vals)

        # Crear las líneas contables
        line_ids = [
            (0, 0, {
                'account_id': diario.company_id.account_journal_payment_debit_account_id.id if self.payment_type == 'inbound' else diario.company_id.account_journal_payment_credit_account_id.id,
                'company_id': self.company_id.id,
                'currency_id': self.currency_id.id,
                'ref': "Comisión IGTF Divisa",
                'date': self.date,
                'partner_id': self.partner_id.id,
                'name': "Comisión IGTF Divisa",
                'journal_id': diario.id,
                'credit': float(self.mount_igtf * self.tax_today) if not self.payment_type == 'inbound' else 0.0,
                'debit': float(self.mount_igtf * self.tax_today) if self.payment_type == 'inbound' else 0.0,
                'amount_currency': -self.mount_igtf if not self.payment_type == 'inbound' else self.mount_igtf,
            }),
            (0, 0, {
                'account_id': self.company_id.account_debit_wh_igtf_id.id if self.payment_type == 'inbound' else self.company_id.account_credit_wh_igtf_id.id,
                'company_id': self.company_id.id,
                'currency_id': self.currency_id.id,
                'ref': "Comisión IGTF Divisa",
                'date': self.date,
                'name': "Comisión IGTF Divisa",
                'journal_id': diario.id,
                'credit': float(self.mount_igtf * self.tax_today) if self.payment_type == 'inbound' else 0.0,
                'debit': float(self.mount_igtf * self.tax_today) if not self.payment_type == 'inbound' else 0.0,
                'amount_currency': -self.mount_igtf if self.payment_type == 'inbound' else self.mount_igtf,
            })
        ]

        # Asignar las líneas al movimiento
        move_id.write({'line_ids': line_ids})

        # Validar y registrar el movimiento
        move_id.action_post()
        self.write({'move_id_igtf_divisa': move_id.id})

        return True


