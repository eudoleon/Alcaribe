# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools, http, exceptions
from odoo.api import call_kw
from odoo.http import request
from odoo.models import check_method_name


class accessDatasetInherit(http.Controller):

    @http.route(['/web/dataset/call_kw', '/web/dataset/call_kw/<path:path>'], type='json', auth="user")
    def call_kw(self, model, method, args, kwargs, path=None):
        # If system is readonly then restrict rpc calls
        if method in ['create', 'write', 'unlink'] and request.env['user.management'].sudo().search(
                [('access_readonly', '=', True),
                 ('access_user_ids', '=', request.context.get('uid')),
                 ('active', '=', True)]):
            return None

        profile_management = request.env['model.access'].sudo().search(
            [('access_model_id.model', '=', model),
             ('access_user_manager_id.access_user_ids', '=', request.context.get('uid')),
             ('access_user_manager_id.active', '=', True)], limit=1)

        if method == 'create' and profile_management.access_hide_create:
            return None
        elif method == 'write' and profile_management.access_hide_edit:
            return None
        elif method == 'unlink' and profile_management.access_hide_delete:
            return None
        return self._call_kw(model, method, args, kwargs)

    def _call_kw(self, model, method, args, kwargs):
        check_method_name(method)
        return call_kw(request.env[model], method, args, kwargs)


class accessRemoveAction(models.Model):
    _name = 'model.access'
    _description = 'Remove Action from model'

    access_model_id = fields.Many2one('ir.model', string='Model', domain="[('id', 'in', access_profile_domain_model)]")
    access_server_action_ids = fields.Many2many('report.action.data', 'server_action_data_rel_ah',
                                            'action_action_id', 'server_action_id', 'Hide Actions',
                                            domain="[('access_action_id.binding_model_id','=',access_model_id),('access_action_id.type','!=','ir.actions.report')]")
    access_report_action_ids = fields.Many2many('report.action.data', 'remove_action_report_action_data_rel_ah',
                                            'action_action_id', 'report_action_id', 'Hide Reports',
                                            domain="[('access_action_id.binding_model_id','=',access_model_id),('access_action_id.type','=','ir.actions.report')]")

    access_model_readonly = fields.Boolean('Read-only')
    access_hide_create = fields.Boolean(string='Hide Create')
    access_hide_edit = fields.Boolean(string='Hide Edit')
    access_hide_delete = fields.Boolean(string='Hide Delete')
    access_hide_archive_unarchive = fields.Boolean(string='Hide Archive/Unarchive')
    access_hide_duplicate = fields.Boolean(string='Hide Duplicate')
    access_hide_export = fields.Boolean(string='Hide Export')
    access_user_manager_id = fields.Many2one('user.management', string='Management Id')
    access_profile_domain_model = fields.Many2many('ir.model', related='access_user_manager_id.access_profile_domain_model')


class accessRemoveActionData(models.Model):
    _name = 'report.action.data'
    _description = "Store Action Button Data"

    name = fields.Char(string='Name')
    access_action_id = fields.Many2one('ir.actions.actions', string='Action')
