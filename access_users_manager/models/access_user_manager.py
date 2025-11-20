# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.http import request
from odoo.exceptions import UserError


class accessAccessManagement(models.Model):
    _name = 'user.management'
    _description = 'User Access Management'

    color = fields.Integer(string='Color')

    def access_default_profile_ids(self):
        return self.env['user.profiles'].sudo().search([('implied_ids', '=', self.env.ref('base.group_system').id)]).ids

    name = fields.Char(string='Name')
    active = fields.Boolean(string='Active', default=True, invisible=True)
    access_readonly = fields.Boolean(string="Readonly",
                                 help='Make the whole database readonly for the users added in this profile.')
    access_hide_chatter = fields.Boolean(string="Hide Chatter", help="Hide all chatter's for the selected user")
    access_disable_debug_mode = fields.Boolean(string='Disable Developer Mode',
                                           help="Deactivate debug mode for the selected users.")
    access_user_ids = fields.Many2many('res.users', 'user_management_users_rel', 'user_management_id', 'user_id',
                                   'Users')
    access_user_rel_ids = fields.Many2many('res.users', 'res_user_store_rel', string='Store user profiles',
                                       compute='access_compute_profile_ids')
    access_profile_ids = fields.Many2many('user.profiles', string='Profiles', required=True)
    access_company_ids = fields.Many2many('res.company', string='Companies', required=True)
    access_hide_menu_ids = fields.Many2many('ir.ui.menu', string='Menu')
    access_model_access_line = fields.One2many('model.access', 'access_user_manager_id', string='Model Access')
    access_hide_field_line = fields.One2many('field.access', 'access_user_manager_id', string='Field Access')
    access_domain_access_line = fields.One2many('domain.access', 'access_user_manager_id', string='Domain Access')
    access_button_tab_access_line = fields.One2many('button.tab.access', 'access_user_manager_id', string='Button Access')
    access_users_count = fields.Integer(string='Users Count', compute='_compute_users_count')
    access_hide_filters_groups_line = fields.One2many('filter.group.access', 'access_user_manager_id', string='Filter Group')
    access_ir_model_access = fields.Many2many('ir.model.access', string='Access Rights', readonly=True)
    access_ir_rule = fields.Many2many('ir.rule', string='Record Rules', readonly=True)
    access_profile_domain_model = fields.Many2many('ir.model')
    access_profile_based_menu = fields.Many2many('ir.ui.menu', 'related_menu_for_profiles', 'profile_ids', 'menu_ids',
                                             compute='_compute_profile_based_menu', store=True)
    is_profile = fields.Boolean(string='Profile Exist')

    @api.onchange('is_profile', 'access_profile_ids')
    def onchange_is_profile(self):
        """ Onchange that the profile is selected inside profile management."""
        if self.access_profile_ids:
            self.is_profile = True
        else:
            self.is_profile = False
        self.access_user_ids = [(6, 0, self.access_profile_ids.mapped('access_user_ids').ids)]
        self.access_user_rel_ids = [(6, 0, self.access_profile_ids.mapped('access_user_ids').ids)]
        access_rights = []
        record_rules = []
        model_ids = []
        for profile in self.access_profile_ids:
            while True:
                access_rights += profile.mapped('implied_ids').model_access.ids
                record_rules += profile.mapped('implied_ids').rule_groups.ids
                model_ids.extend(profile.mapped('implied_ids').model_access.mapped('model_id').ids)
                if profile.implied_ids:
                    profile = profile.implied_ids
                else:
                    break
        record_rules += self.env['res.groups'].sudo().search([('custom', '=', True)]).mapped('rule_groups').ids
        self.access_ir_model_access = [(6, 0, access_rights)]
        self.access_ir_rule = [(6, 0, record_rules)]
        self.access_profile_domain_model = [(6, 0, model_ids)]

    @api.constrains('name')
    def check_name(self):
        """Restrict admin to create rule as same name which is exist"""
        for rec in self:
            student = self.env['user.management'].sudo().search([('name', '=', rec.name), ('id', '!=', rec.id)])
            if student:
                raise UserError('Name must be unique for managements.')

    @api.model_create_multi
    def create(self, vals_list):
        res = super(accessAccessManagement, self).create(vals_list)
        return res

    @api.depends('access_users_count')
    def _compute_users_count(self):
        """Compute total user which is selected inside selected profiles"""
        for rec in self:
            rec.access_users_count = len(self.access_user_ids)

    @api.depends('access_profile_based_menu', 'access_profile_ids')
    def _compute_profile_based_menu(self):
        """Compute menu which is for the selected profile"""
        visible_menu_ids = []
        for rec in self.access_profile_ids:
            last_group = rec.implied_ids
            while True:
                if last_group:
                    visible_menu_ids.extend(last_group.menu_access.ids)
                    last_group = last_group.implied_ids
                else:
                    break
        self.sudo().write({'access_profile_based_menu': [(6, 0, list(set(visible_menu_ids)))]})

    @api.depends('access_profile_ids', 'access_profile_ids.access_user_ids')
    def access_compute_profile_ids(self):
        """Compute profiles users and access rights and domain for selected profile model"""
        for rec in self:
            rec.access_user_ids = [(6, 0, rec.access_profile_ids.mapped('access_user_ids').ids)]
            rec.access_user_rel_ids = [(6, 0, rec.access_profile_ids.mapped('access_user_ids').ids)]
            access_rights = []
            record_rules = []
            model_ids = []
            for profile in rec.access_profile_ids:
                while True:
                    access_rights += profile.mapped('implied_ids').model_access.ids
                    record_rules += profile.mapped('implied_ids').rule_groups.ids
                    model_ids.extend(profile.mapped('implied_ids').model_access.mapped('model_id').ids)
                    if profile.implied_ids:
                        profile = profile.implied_ids
                    else:
                        break
            record_rules += self.env['res.groups'].sudo().search([('custom', '=', True)]).mapped('rule_groups').ids
            rec.access_ir_model_access = [(6, 0, access_rights)]
            rec.access_ir_rule = [(6, 0, record_rules)]
            self.access_profile_domain_model = [(6, 0, model_ids)]

    def write(self, vals):
        res = super(accessAccessManagement, self).write(vals)
        self.clear_caches()
        if vals.get('access_user_ids'):
            for domain in self.access_domain_access_line:
                users = self.env['res.users'].sudo().search(
                    [('access_user_manager_id', '=', self.id),
                     ('access_user_manager_id.active', '=', True)])
                domain.access_rule_id.groups.users = [(6, 0, users.ids)]
        return res

    def unlink(self):
        for domain in self.access_domain_access_line:
            domain.unlink()
        res = super(accessAccessManagement, self).unlink()
        self.clear_caches()
        return res

    def access_activate_rule(self):
        """ Activate User Management Rule."""
        self.active = True
        users = self.env['res.users'].sudo().search(
            [('access_user_manager_id', '=', self.id), ('access_user_manager_id.active', '=', True)])
        for domain in self.access_domain_access_line:
            domain.access_rule_id.groups.users = [(6, 0, users.ids)]

    def access_deactivate_rule(self):
        """ Deactivate User Management Rule."""
        self.active = False
        users = self.env['res.users'].sudo().search(
            [('access_user_manager_id', '=', self.id), ('access_user_manager_id.active', '=', True)])
        for domain in self.access_domain_access_line:
            domain.access_rule_id.groups.users = [(6, 0, users.ids)]

    def access_view_profile_users(self):
        """Open users tree view"""
        return {
            'name': _('Profile Users'),
            'type': 'ir.actions.act_window',
            'view_type': 'list',
            'view_mode': 'list',
            'res_model': 'res.users',
            'view_id': self.env.ref('base.view_users_tree').id,
            'target': 'current',
            'domain': [('id', 'in', self.access_user_ids.ids)],
            'context': {'create': False},

        }

    def access_view_profile_record_rules(self):
        """ Open record rules tree view"""
        action = self.env["ir.actions.actions"]._for_xml_id("base.action_rule")
        action["domain"] = [("id", "in", self.access_ir_rule.ids)]
        return action

    def access_view_profile_access_rights(self):
        """" Open Access rights tree view"""
        action = self.env["ir.actions.actions"]._for_xml_id("base.ir_access_act")
        action["domain"] = [("id", "in", self.access_ir_model_access.ids)]
        return action

    def access_search_action_button(self, model):
        """Hide archive/unarchive and export buttons for selected user based on models."""
        hide_element = []
        lst = [int(x) for x in request.httprequest.cookies.get('cids').split(',')]
        is_archive_hide = self.env['model.access'].sudo().search(
            [('access_model_id.model', '=', model), ('access_user_manager_id.active', '=', True),
             ('access_user_manager_id.access_company_ids', 'in', lst),
             ('access_user_manager_id.access_user_ids', 'in', self.env.user.id), ('access_hide_archive_unarchive', '=', True)], limit=1)
        is_export_hide = self.env['model.access'].sudo().search(
            [('access_model_id.model', '=', model), ('access_user_manager_id.active', '=', True),
             ('access_user_manager_id.access_company_ids', 'in', lst),
             ('access_user_manager_id.access_user_ids', 'in', self.env.user.id), ('access_hide_export', '=', True)], limit=1)
        if is_archive_hide:
            hide_element = hide_element + ['Archive', 'Unarchive']
        if is_export_hide:
            hide_element = hide_element + ['Export']
        return hide_element


class ResCompany(models.Model):
    _inherit = 'res.company'

    color = fields.Integer(string='Color')
