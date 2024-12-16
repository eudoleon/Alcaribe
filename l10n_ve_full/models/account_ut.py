# coding: utf-8
import time
from odoo import fields, models

class AccountUT(models.Model):
    _name = 'account.ut'
    _description = 'Unidad Tributaria'
    _order = 'date desc'

    name = fields.Char(string='Número de referencia', size=64, required=True, readonly=False, default=None,
                       help="Número de referencia según la ley")
    date = fields.Date(string='Fecha', required=True, help="Fecha en la que entra en vigor la nueva Unidad Tributaria Unitaria")
    amount = fields.Float(string='Monto', digits='Amount Bs per UT', help="Monto de la unidad tributaria en bs",
                          required=True)

    def get_amount_ut(self, date=False):
        """ Return the value of
        the tributary unit of the specified date or
        if it's empty return the value to current
        date.
        """
        rate = 0
        date = date or time.strftime('%Y-%m-%d')
        self._cr.execute("""SELECT amount FROM account_ut WHERE date <= '%s'
                   ORDER BY date desc LIMIT 1""" % date)
        if self._cr.rowcount:
            rate = self._cr.fetchall()[0][0]
        return rate

    def compute(self, from_amount, date=False, context=None):
        """ Return the number of tributary
        units depending on an amount of money.
        """
        # if context is None:
        #    context = {}
        result = 0.0
        ut = self.get_amount_ut(date=date)
        if ut:
            result = from_amount / ut
        return result

    def compute_ut_to_money(self, amount_ut, date=False, context=None):
        """ Transforms from tax units into money
        """
        # if context is None:
        #    context = {}
        money = 0.0
        ut = self.get_amount_ut(date)
        if ut:
            money = amount_ut * ut
        return money

    def exchange(self, from_amount, from_currency_id, to_currency_id, exchange_date, context=None):
        if from_currency_id == to_currency_id:
            return from_amount
        rc_obj = self.env['res.currency']
        fci = rc_obj.browse(from_currency_id)
        tci = rc_obj.browse(to_currency_id)
        return rc_obj._compute(fci, tci, from_amount)

    def sxc(self, from_currency_id, to_currency_id, exchange_date, context=None):
        # This is a clousure that allow to use the exchange rate conversion in a
        # short way
        # context = context or {}

        def _xc(from_amount):
            return self.exchange(from_amount, from_currency_id, to_currency_id, exchange_date)
        return _xc
