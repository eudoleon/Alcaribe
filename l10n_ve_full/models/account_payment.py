# coding: utf-8
###########################################################################

from odoo import fields, models, api,_
from odoo.exceptions import UserError


class AccountPaymentInnerit(models.Model):
    _inherit = 'account.payment'

    move_itf_id = fields.Many2one('account.move', 'Asiento ITF')

    def action_post(self):
        """Genera la retencion del % después que realiza el pago"""

        res = super().action_post()
        #print(res)
        for pago in self:
            if not pago.move_itf_id:
                idem = pago.check_partner()
                itf_bool = pago._get_company_itf()
                type_bool = pago.check_payment_type()
                if idem and itf_bool and type_bool:
                    pago.register_account_move_payment()
            else:
                if pago.move_itf_id.state == 'draft':
                    pago.move_itf_id.action_post()


    def register_account_move_payment(self):
        '''Este método realiza el asiento contable de la comisión según el porcentaje que indica la compañia'''


        #self.env['ir.sequence'].with_context(ir_sequence_date=self.date_advance).next_by_code(sequence_code)
        vals = {
            'date': self.date,
            'journal_id': self.journal_id.id,
            'line_ids': False,
            'state': 'draft',
            'move_type': 'entry',
        }


        porcentage_itf= self._get_company().wh_porcentage
        #calculo del 2% del pago

        #amount_itf = self.compute_itf()
        if self.currency_id.id == 2:
            currency = False
            amount_currency = 0.0
            amount_itf = round(float(self.amount) * float((porcentage_itf / 100.00)), 2)
        else:
            currency = self.currency_id.id
            amount_currency = self.amount
            tasa = self.env['res.currency'].search([('id', '=', 2)]).inverse_rate
            if tasa:
                amount_itf = round(float(self.amount*tasa) * float((porcentage_itf / 100.00)), 2)
            else:
                raise UserError(_('Por favor Registrar la tasa para poder hacer la respectiva conversion y poder continuar'))
        move_id = self.env['account.move'].create(vals)
        asiento = {
            'account_id': self.journal_id.default_account_id.id,
            'company_id': self._get_company().id,
            'currency_id': currency,
            'date_maturity': False,
            'ref': "Comisión ITF del %s %% del pago %s" % (porcentage_itf,self.name),
            'date': self.date,
            'partner_id': self.partner_id.id,
            'move_id': move_id.id,
            'name': "Comisión ITF del %s %% del pago %s" % (porcentage_itf, self.name),
            'journal_id': self.journal_id.id,
            'credit': float(amount_itf),
            'debit': 0.0,
            'amount_currency': -amount_currency,
        }

        move_line_obj = self.env['account.move.line']
        move_line_id1 = move_line_obj.with_context(check_move_validity=False).create(asiento)
        asiento['amount_currency'] = amount_currency
        asiento['account_id'] = self._get_company().account_wh_itf_id.id
        asiento['credit'] = 0.0
        asiento['debit'] = float(amount_itf)

        move_line_id2 = move_line_obj.create(asiento)

        if move_line_id1 and move_line_id2:
            res = {'move_itf_id': asiento['move_id']}
            self.write(res)
            move_id.action_post()
        return True

    @api.model
    def _get_company(self):
        '''Método que busca el id de la compañia'''
        company_id = self.env['res.users'].browse(self.env.uid).company_id
        return company_id

    def _get_company_itf(self):
        '''Método que retorna verdadero si la compañia debe retener el impuesto ITF'''
        company_id = self._get_company()
        if company_id.calculate_wh_itf:
            return True
        return False

    @api.model
    def check_payment_type(self):
        '''metodo que chequea que el tipo de pago si pertenece al tipo outbound'''
        type_bool = False
        for pago in self:
            type_payment = pago.payment_type
            if type_payment == 'outbound':
                type_bool = True
        return type_bool


    @api.model
    def check_partner(self):
        '''metodo que chequea el rif de la empresa y la compañia si son diferentes
        retorna True y si son iguales retorna False'''
        idem = False
        company_id = self._get_company()
        for pago in self:
            if not pago.journal_id.permitir_itf:
                idem = False
                return idem
            elif (pago.partner_id.vat != company_id.partner_id.vat) and pago.partner_id.company_type == 'company' :
                idem = True
                return idem
            elif (pago.partner_id.identification_id != company_id.partner_id.vat) and pago.partner_id.company_type == 'person':
                idem = True
                return idem
        return idem


    # def get_name_itf(self):
    #     '''metodo que crea el name del asiento contable si la secuencia no esta creada crea una con el
    #     nombre: 'l10n_account_withholding_itf'''
    #
    #     self.ensure_one()
    #     SEQUENCE_CODE = 'account.itf'
    #     company_id = self._get_company()
    #     IrSequence = self.env['ir.sequence'].with_company(company_id)
    #     name = IrSequence.next_by_code(SEQUENCE_CODE)
    #     return name


    # def cancel(self):
    #     """Calcela el movimiento contable si se cancela el pago de las facturas"""
    #     res = super(AccountPaymentInnerit, self).cancel()
    #     date = fields.Datetime.now()
    #     for pago in self:
    #         if pago.state == 'cancelled':
    #             for move in pago.move_itf_id:
    #                 move_reverse = move._reverse_moves([{'date': date, 'ref': _('Reversal of %s') % move.name}],
    #                                cancel=True)
    #                 if len(move_reverse) == 0:
    #                     raise UserError(_('No se reversaron los asientos asociados'))
    #     return res

    def action_draft(self):
        ''' posted -> draft '''
        res = super().action_draft()
        if self.move_itf_id:
            self.move_itf_id.button_draft()

    def action_cancel(self):
        ''' draft -> cancelled '''
        res = super().action_cancel()
        if self.move_itf_id:
            self.move_itf_id.button_cancel()