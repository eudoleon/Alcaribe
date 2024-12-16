from odoo import fields, models, api, _

class edit_value(models.Model):
    _name = 'edit.value'
    _description = 'Edit Value'

    name = fields.Char('Name')
    old = fields.Char('Old Changes')
    new = fields.Char('New Changes')
    activity_log_id = fields.Many2one('activity.log', 'Activity Log')
    

    