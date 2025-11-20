# -*- coding: utf-8 -*-
from odoo import models, fields, api
from lxml import etree


class accessFilterGroupAccess(models.Model):
    _name = 'filter.group.access'

    access_model_id = fields.Many2one('ir.model', string='Model', domain="[('id', 'in', access_profile_domain_model )]")
    access_model_name = fields.Char(string='Model Name', related='access_model_id.model', readonly=True, store=True)
    access_hide_filter_ids = fields.Many2many('filter.group.data', string='Hide Filters')
    access_hide_group_ids = fields.Many2many('filter.group.data', 'group_access_rel', 'access_id', 'data_id',
                                         string='Hide Groups')
    access_user_manager_id = fields.Many2one('user.management', string='Rule')
    access_profile_domain_model = fields.Many2many('ir.model', related='access_user_manager_id.access_profile_domain_model')

    @api.onchange('access_model_id')
    def onchange_access_model_id(self):
        """Create filter and group-by records in a custom model."""
        if self.access_model_id and self.access_model_name:
            filter_group_obj = self.env['filter.group.data']
            view_obj = self.env['ir.ui.view']
            for views in view_obj.sudo().search(
                    [('model', '=', self.access_model_name), ('type', '=', 'search')]):
                res = self.env[self.access_model_name].sudo().fields_view_get(view_id=views.id, view_type='search')
                doc = etree.XML(res['arch'])
                filters = doc.xpath("//search/filter")
                groups = doc.xpath("//group//filter")
                if filters:
                    for filter in filters:
                        if filter.get('string'):
                            domain = [('access_filter_group_string', '=', filter.get('string')),
                                      ('access_model_id', '=', self.access_model_id.id), ('access_type', '=', 'filter')]
                            if filter.get('name'):
                                domain += [('access_filter_group_name', '=', filter.get('name'))]
                            filter_exist = filter_group_obj.sudo().search(domain, limit=1)
                            if not filter_exist:
                                filter_group_obj.create({
                                    'access_model_id': self.access_model_id.id,
                                    'access_filter_group_name': filter.get('name'),
                                    'access_filter_group_string': filter.get('string'),
                                    'access_type': 'filter',
                                })
                if groups:
                    for group in groups:
                        group = group.attrib
                        if group.get('string'):
                            domain = [('access_filter_group_string', '=', group.get('string')),
                                      ('access_model_id', '=', self.access_model_id.id), ('access_type', '=', 'group')]
                            if group.get('name'):
                                domain += [('access_filter_group_name', '=', group.get('name'))]
                            group_exist = filter_group_obj.sudo().search(domain, limit=1)
                            if not group_exist:
                                filter_group_obj.create({
                                    'access_model_id': self.access_model_id.id,
                                    'access_filter_group_name': group.get('name'),
                                    'access_filter_group_string': group.get('string'),
                                    'access_type': 'group',
                                })


class accessFilterGroupData(models.Model):
    _name = 'filter.group.data'
    _description = 'Store Filter / Group Data'
    _rec_name = 'access_filter_group_string'

    access_filter_group_name = fields.Char('Name')
    access_model_id = fields.Many2one('ir.model', string='Model', index=True, ondelete='cascade', required=True)
    access_model_name = fields.Char(string='Model Name', related='access_model_id.model', readonly=True, store=True)
    access_type = fields.Selection([('filter', 'Filter'), ('group', 'Group')], string="Type",
                            required=True)
    access_filter_group_string = fields.Char('Filter / Group string', required=True)
