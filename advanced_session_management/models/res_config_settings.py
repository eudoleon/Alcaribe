from odoo import api, fields, models, _
from datetime import datetime, timedelta


class res_config_settings(models.TransientModel):
    _inherit = 'res.config.settings'

    remove_sesions = fields.Integer("Scheduled remove old sessions", default=7)
    send_mail = fields.Boolean('Send Mail When New Session Start', default=True)
    session_timeout_interval_number = fields.Integer('Interval Number', default=0)
    # session_timeout_interval_type = fields.Selection([('minutes', 'Minutes'),
    #                                   ('hours', 'Hours'),
    #                                   ('days', 'Days')], string='Interval Unit', default='hours')
    session_timeout_active = fields.Selection([('none','None'),('active','Active'),('inactive','Inactive')], string='Do not timeout active session', default='none')

    @api.model
    def get_values(self):
        res = super(res_config_settings, self).get_values()
        config_parameter_obj = self.env['ir.config_parameter'].sudo()
        res['remove_sesions'] = int(config_parameter_obj.get_param('advanced_session_management.remove_sesions', default=7))
        res['send_mail'] = config_parameter_obj.get_param('advanced_session_management.send_mail', default='False') == 'True'
        
        res['session_timeout_interval_number'] = int(config_parameter_obj.get_param('advanced_session_management.session_timeout_interval_number', default=0))
        # res['session_timeout_interval_type'] = config_parameter_obj.get_param('advanced_session_management.session_timeout_interval_type', default='')
        res['session_timeout_active'] = config_parameter_obj.get_param('advanced_session_management.session_timeout_active', default='none')

        return res

    @api.model
    def set_values(self):
        config_parameter_obj = self.env['ir.config_parameter'].sudo()

        if self.remove_sesions <= 0:
            remove_sesions = 7 
        else:
            remove_sesions = self.remove_sesions
        config_parameter_obj.set_param('advanced_session_management.remove_sesions', remove_sesions)
        config_parameter_obj.set_param('advanced_session_management.send_mail', str(self.send_mail))
        active_timeout = config_parameter_obj.get_param('advanced_session_management.session_timeout_active') or 'none'
        timeout = 0
        if self.session_timeout_interval_number > 2160:
            timeout = 2160
        else:
            timeout = self.session_timeout_interval_number
        if timeout != active_timeout:
            login_logs = self.env['login.log'].sudo().search([('state','=','active')])
            if self.session_timeout_active in ['active', 'inactive']:
                for login_log in login_logs:
                    login_log.timeout_date = datetime.now() + timedelta(hours=self.session_timeout_interval_number)
            if self.session_timeout_active == 'none':
                for login_log in login_logs:
                    login_log.timeout_date = False
        
        
        config_parameter_obj.set_param('advanced_session_management.session_timeout_interval_number', str(timeout))
        config_parameter_obj.set_param('advanced_session_management.session_timeout_active', self.session_timeout_active)

        return super(res_config_settings, self).set_values()


class ir_config_parameter(models.Model):
    _inherit = 'ir.config_parameter'

    def delete_record_ao(self):
        self.search([('key','=','disable_log')],limit=1).unlink()

