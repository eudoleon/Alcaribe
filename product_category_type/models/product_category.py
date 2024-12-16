# Copyright 2021 Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = "product.category"

    parent_id = fields.Many2one(domain="[('type', 'in', ('view','familia','seccion','sub-familia')),('hr_department_id','=',hr_department_id)]")

    type = fields.Selection(
        selection=[("view", "View"),("seccion","Seccion"),("familia","Familia"),("sub-familia","Sub Familia") ,("normal", "Normal")], #SECCION,	FAMILIA,	FAMILIA
        string="Category Type",
        default="normal",
        help="A category of the view type is a virtual category"
        " that can be used as the parent of another category"
        " to create a hierarchical structure.",
    )
    hr_department_id = fields.Many2one(
        "hr.department", string="Departmento", required=False
    )

class ProductTemplate(models.Model):
    _inherit = "product.template"

    ve_origen = fields.Selection(
        selection=[("ve", "Nacional"),("ext","Exterior")], #SECCION,	FAMILIA,	FAMILIA
        string="Origen",
        default="ve",
    )
    categ_seccion_id = fields.Many2one('product.category', 'Seccion',domain="[('type', 'in', ('seccion',)),('hr_department_id','=',hr_department_id)]")
    categ_familia_id = fields.Many2one('product.category', 'Familia',domain="[('type', 'in', ('familia',)),('hr_department_id','=',hr_department_id),('parent_id','=',categ_seccion_id)]")
    hr_department_id = fields.Many2one(
        "hr.department", string="Departmento", required=False
    )