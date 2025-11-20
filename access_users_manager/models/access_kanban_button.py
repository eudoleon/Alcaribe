from odoo import fields, models, api, _
from odoo.exceptions import UserError

class KanbanButtonHide(models.Model):
    _name = 'kanban.button.hide'
    _description = 'Kanban Buttons to Hide'

    access_name = fields.Char(string='Button Name')
    access_tab_button_string = fields.Char(string='Button Label')
    access_button_type = fields.Selection([
        ('edit', 'Edit'),
        ('set_cover', 'Set Cover'),
        ('other', 'Other'),
    ], string='Button Type')
    button_access_id = fields.Many2one('button.tab.access', string='Button Access Ref')
    kanban_button_access_id = fields.Many2one('button.tab.access', string='Kanban Button Access Ref')
