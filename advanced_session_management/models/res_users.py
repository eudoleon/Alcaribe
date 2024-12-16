from odoo import fields, models, api, _

class res_users(models.Model):
    _inherit = 'res.users'

    login_log_ids = fields.One2many('login.log', 'user_id', 'Sessions')

    def action_kill_all_session(self):
        for record in self:
            return record.login_log_ids.logout_button()