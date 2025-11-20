# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError


class GeneralSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    password_expire_enable = fields.Boolean(string='Enable Password Expiration',
                                            config_parameter='access_users_manager.password_expire_enable')

    password_expire_in_days = fields.Integer(string='Password Expire Days',
                                           config_parameter='access_users_manager.password_expire_in_days')

    @api.constrains('password_expire_in_days')
    def check_password_expire_in_days(self):
        """Restrict to set password expiry month zero"""
        if self.password_expire_enable and not self.password_expire_in_days:
            raise UserError(_('Please provide expiry day greater than zero...'))

    @api.model_create_multi
    def create(self, vals_list):
        try:
            config_setting = self.env['res.config.settings'].sudo().search([])
            res = super(GeneralSettings, self).create(vals_list)
            all_users = self.env['res.users'].sudo().search([])
            if not res.password_expire_enable:
                res.password_expire_in_days = 0
                for user in all_users:
                    user.sudo().write({'access_password_expire_date': False, 'access_is_passwd_expired': False})
            elif config_setting:
                last_record = config_setting[len(config_setting) - 1]
                if last_record.password_expire_in_days != res.password_expire_in_days:
                    for user in all_users:
                        user.sudo().write({'access_password_update': datetime.now(),
                                           'access_password_expire_date': datetime.now() + relativedelta(
                                               days=res.password_expire_in_days)})
            else:
                for user in all_users:
                    user.sudo().write({'access_password_update': datetime.now(),
                                       'access_password_expire_date': datetime.now() + relativedelta(
                                           days=res.password_expire_in_days)})
        except Exception as e:
            raise ValidationError(_(e))
        return res
