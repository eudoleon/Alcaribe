from email.policy import default
from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
import base64
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_round
from odoo.exceptions import Warning

class HRContractRate(models.Model):
    _name = 'hr.contract.rate'
    _description = 'Tasa de Cambio para Contratos'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    rate = fields.Float(string='Tipo de Cambio', default='0.00', tracking=True, digits=(12,4))
    date = fields.Date(string='Fecha', default=lambda self: fields.datetime.now(), tracking=True)
    state = fields.Selection([('draft', 'Borrador'), ('confirmed', 'Confirmado'), ('done', 'Realizado'), ('cancel', 'Cancelado')], default='draft', tracking=True)
    
    def button_cancel(self):
        self.state='cancel'

    def button_confirmed(self):
        self.state='confirmed'

    def button_done(self):
        contract = self.env['hr.contract'].search([('state','=','open')])
        for salary in contract:
            neto = self.rate*salary.wage_div
            values = {
            'wage': neto,
            }
            salary.write(values)
        self.state='done'