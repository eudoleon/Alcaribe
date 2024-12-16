from odoo import fields, models, api, _

class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    currency_id = fields.Many2one('res.currency', string='Currency', related='journal_id.currency_id', store=True)
