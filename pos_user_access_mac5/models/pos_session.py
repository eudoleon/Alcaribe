from odoo import api, models

NEW_USER_FIELDS = [
    'pos_access_close',
    'pos_access_decrease_quantity',
    'pos_access_delete_order',
    'pos_access_delete_orderline',
    'pos_access_discount',
    'pos_access_payment',
    'pos_access_price',
]


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _pos_ui_models_to_load(self):
        result = super()._pos_ui_models_to_load()
        if result and 'res.users.all' not in result:
            result.append('res.users.all')
        return result

    def _loader_params_res_users(self):
        result = super()._loader_params_res_users()
        result['search_params']['fields'] += NEW_USER_FIELDS
        return result

    def _loader_params_res_users_all(self):
        result = self._loader_params_res_users()
        result['search_params']['domain'] = []
        return result

    def _get_pos_ui_res_users_all(self, params):
        return self.env['res.users'].search_read(**params['search_params'])
