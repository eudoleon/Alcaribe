# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import groupby
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.misc import formatLang
from odoo.tools import html2plaintext
import odoo.addons.decimal_precision as dp

class ResUsers(models.Model):
    _inherit = 'res.users'

    pos_security_pin = fields.Char(string='Security PIN', size=32, help='A Security PIN used to protect sensible functionality in the Point of Sale')

    @api.constrains('pos_security_pin')
    def _check_pin(self):
        if self.pos_security_pin and not self.pos_security_pin.isdigit():
            raise UserError(_("Security PIN can only contain digits"))


class PosConfigInherit(models.Model):
	_inherit = 'pos.config'

	user_id = fields.Many2one('res.users',string='Manager')
	close_pos = fields.Boolean(string='Closing Of POS')
	order_delete = fields.Boolean(string='Order Deletion')
	order_line_delete = fields.Boolean(string='Order Line Deletion')
	qty_detail = fields.Boolean(string='Add/Remove Quantity')
	discount_app = fields.Boolean(string='Apply Discount')
	payment_perm = fields.Boolean(string='Payment')
	price_change = fields.Boolean(string='Price Change')
	one_time_valid = fields.Boolean(string='One Time Password for an Order')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_user_id = fields.Many2one(related='pos_config_id.user_id', readonly=False)
    pos_close_pos = fields.Boolean(related='pos_config_id.close_pos', readonly=False)
    pos_order_delete = fields.Boolean(related='pos_config_id.order_delete', readonly=False)
    pos_order_line_delete = fields.Boolean(related='pos_config_id.order_line_delete', readonly=False)
    pos_qty_detail = fields.Boolean(related='pos_config_id.qty_detail', readonly=False)
    pos_discount_app = fields.Boolean(related='pos_config_id.discount_app', readonly=False)
    pos_payment_perm = fields.Boolean(related='pos_config_id.payment_perm', readonly=False)
    pos_price_change = fields.Boolean(related='pos_config_id.price_change', readonly=False)
    pos_one_time_valid = fields.Boolean(related='pos_config_id.one_time_valid', readonly=False)


class POSSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_res_users(self):
        result = super()._loader_params_res_users()
        result['search_params']['fields'].append('pos_security_pin')
        return result

    def load_pos_data(self):
        loaded_data = {}
        self = self.with_context(loaded_data=loaded_data)
        for model in self._pos_ui_models_to_load():
            loaded_data[model] = self._load_model(model)
        self._pos_data_process(loaded_data)        
        users_data = self._get_pos_ui_pos_res_users(self._loader_params_pos_res_users())
        loaded_data['users'] = users_data
        return loaded_data

    def _loader_params_pos_res_users(self):
        return {
            'search_params': {
                'domain': [],
                'fields': ['name', 'groups_id', 'pos_security_pin'],
            },
        }

    def _get_pos_ui_pos_res_users(self, params):
        users = self.env['res.users'].search_read(**params['search_params'])
        return users