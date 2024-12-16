# coding: utf-8
###############################################################################
#    Module Writen to OpenERP, Open Source Management Solution
#    Copyright (C) OpenERP Venezuela (<http://www.vauxoo.com>).
#    All Rights Reserved
###############################################################################
#    Credits:
#    Coded by: Katherine Zaoral <kathy@vauxoo.com>
#    Planified by: Humberto Arocha <hbto@vauxoo.com>
#    Audited by: Humberto Arocha <hbto@vauxoo.com>
###############################################################################
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
###############################################################################

from odoo import fields, models, api, _
from odoo.exceptions import UserError

class ChangeInvoiceSinCredwizard(models.TransientModel):

    """
    Wizard that changes the invoice sin_cred field.
    """
    _name = 'change.invoice.sin.cred'
    _description = 'Change Invoice Tax Exempt'

    sin_cred = fields.Boolean('Exento de impuestos',default=lambda s: s._context.get('invoice_sin_cred'),
            help='Exento de impuestos')
    sure = fields.Boolean('¿Estas Seguro?')


    def set_sin_cred(self):
        """
        Change the sin cred field in the invoice
        @return
        """
        context = self._context or {}
        ids = isinstance(self.ids, (int, int)) and [self.ids] or self.ids
        inv_obj = self.env['account.move']
        inv_ids = context.get('active_ids', [])
        data = self.browse(ids[0])
        invoice = inv_obj.browse(self._context['active_id'])

        if not data.sure:

            raise UserError("Error! \n Confirme que desea realizar esta accion marcando la opción")
        if inv_ids:
            invoice.write({'sin_cred': self.sin_cred})
        return {}
