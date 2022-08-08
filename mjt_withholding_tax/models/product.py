# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError, ValidationError

    
class ProductTemplate(models.Model):
    _inherit = "product.template"

    apply_withholding = fields.Boolean(string="Apply Withholding Tax")
    withholding_tax_id = fields.Many2one('account.tax', string="Withholding Tax", domain=[("withholding_tax", "=", True)])
