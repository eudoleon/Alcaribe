# Copyright 2021 Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    categ_id = fields.Many2one(domain="[('type', '=', 'normal'),('hr_department_id','=',hr_department_id),('parent_id','=',categ_familia_id)]")
