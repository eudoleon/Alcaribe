from odoo import models, fields
from datetime import datetime
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = "stock.picking"

    date_of_transfer = fields.Date(string="Effective Date", default=False, states={
        'draft': [('invisible', False)],
        'waiting': [('invisible', False)],
        'ready': [('invisible', False)],
        'done': [('invisible', True)],
    })