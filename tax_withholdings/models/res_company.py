from odoo import models, fields, api, _


class ResCompany(models.Model):
    _inherit = "res.company"
    
    withholding_signature = fields.Image('Firma en Comprobante', max_width=200, max_height=200)
    withholding_sello = fields.Image('Sello en Comprobate', max_width=200, max_height=200)
