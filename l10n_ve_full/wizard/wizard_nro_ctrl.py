# coding: utf-8

from odoo import models, fields, _
from odoo.exceptions import UserError


class WizNroctrl(models.TransientModel):
    _name = 'wiz.nroctrl'
    _description = "Wizard que cambia el número de control de la factura."

    name = fields.Char(string='Número de Control', required=True)
    sure = fields.Boolean(string='¿Estas seguro?')

    def set_noctrl(self):
        """ Change control number of the invoice
        """
        account_move = self.env['account.move'].search([])
        if not self.sure:
            raise UserError("Error! \nConfirme que desea hacer esto marcando la casilla opción")
        inv_obj = self.env['account.move']
        n_ctrl = self.name
        for noctrl in account_move:
            if noctrl.nro_ctrl == n_ctrl:
                raise UserError("Error! \nEl Numero de Control ya Existe")
        active_ids = self._context.get('active_ids', [])
        inv_obj.browse(active_ids).write({'nro_ctrl': n_ctrl})
        return {}
