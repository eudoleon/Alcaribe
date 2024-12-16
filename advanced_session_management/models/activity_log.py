from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.http import request

class activity_log(models.Model):
    _name = 'activity.log'
    _description = 'Activity Log'
    _order = 'id desc'

    name = fields.Char('Record Name')
    login_log_id = fields.Many2one('login.log', 'Session')
    # login_log_read_id = fields.Many2one('login.log', 'Session Read')
    # user_id = fields.Many2one('res.users', 'User', related='login_log_id.user_id', store=True)
    # user_id = fields.Many2one('res.users', 'User', compute='_get_user_id', store=True)
    user_id = fields.Many2one('res.users', 'User')
    model = fields.Char('Model')
    # edit_value_id = fields.Many2one('edit.value', 'Edit Value')
    edit_value_ids = fields.One2many('edit.value', 'activity_log_id', 'Edit Value')
    # res_id = fields.Integer('Record ID')
    res_id = fields.Char('Record IDs')
    action = fields.Selection([('read','Read'),('create','Create'),('edit','Modify'),('delete','Delete')], string='Action')
    value = fields.Html('Changes')
    has_change_view = fields.Boolean('Has Change View', compute='_get_has_change_view')
    url = fields.Char('Url')

    view = fields.Char('View')

    # @api.depends('login_log_id','login_log_id.user_id')
    # def _get_user_id(self):
    #     for record in self:
    #         record.user_id = record.login_log_id.user_id.id

    @api.depends('edit_value_ids')
    def _get_has_change_view(self):
        for record in self:
            record.has_change_view = bool(record.edit_value_ids)

    def unlink(self):
        for record in self:
            try:
                model = request.params['model']
            except:
                model = ''
            if record.login_log_id.user_id.id == self.env.user.id and model != 'base.module.uninstall':
                raise UserError(_("You cant delete your own sessions and activitiy."))
        return super(activity_log, self).unlink()

    def action_open_edit_view(self):
        action = {
            'name': _('Changes'),
            'view_mode': 'form',
            'res_model': 'edit.value',
            'type': 'ir.actions.act_window',
            'res_id': self.edit_value_id.id,
            'target': 'new'
        }
        return action

    def action_open_record(self):
        self.ensure_one()
        if self.action == 'read':
            return {
                'type': 'ir.actions.act_url',
                'target': 'new',
                'url': self.url,
            }
        else:
            action = {
                'name': self.name,
                'view_mode': 'form',
                'res_model': self.model,
                'type': 'ir.actions.act_window',
                'res_id': int(self.res_id),
                'target': 'current',
            }
        return action
