from odoo import fields,models,api,_
from lxml import etree

class hide_filters_groups(models.Model):
    _name = 'hide.filters.groups'
    _description = 'Hide Filters Groups'

    model_id = fields.Many2one('ir.model', string='Model', index=True, required=True, ondelete='cascade')
    model_name = fields.Char(string='Model Name', related='model_id.model', readonly=True, store=True)

    filters_store_model_nodes_ids = fields.Many2many('store.filters.groups', 'filters_hide_filters_groups_store_filters_groups_rel',
                                 'hide_id', 'store_id', string='Hide Filters', domain="[('node_option','=','filter')]")
    groups_store_model_nodes_ids = fields.Many2many('store.filters.groups', 'groups_hide_filters_groups_store_filters_groups_rel',
                                 'hide_id', 'store_id', string='Hide Groups', domain="[('node_option','=','group')]")

    access_management_id = fields.Many2one('access.management', 'Access Management')


    @api.model
    @api.onchange('model_id')
    def _get_filter_groups(self):
        store_filters_groups_obj = self.env['store.filters.groups']
        view_obj = self.env['ir.ui.view']

        if self.model_id and self.model_name:

            view_list = ['search']
            for view in view_list:
                for views in view_obj.search([('model', '=', self.model_name),('type', '=', view)]): #
                    res = self.env[self.model_name].sudo().fields_view_get(view_id=views.id, view_type=view)
                    doc = etree.XML(res['arch'])

                    object_groups = doc.xpath("//group")
                    for obj_group in object_groups:
                        for group in obj_group:

                            ## Group By records
                            if group.get('name', False) and group.get('string', False) and group.get('context', False):
                                domain = [('attribute_name','=',group.get('name')),('model_id','=',self.model_id.id),('node_option','=','group')]
                                if not store_filters_groups_obj.search(domain):
                                    store_filters_groups_obj.create({
                                        'model_id' : self.model_id.id,
                                        'node_option' : 'group',
                                        'attribute_name' : group.get('name'),
                                        'attribute_string': group.get('string')
                                    })

                        object_filters = doc.xpath("//filter")
                        for filter in object_filters:

                            ## Filters By records
                            if filter.get('name', False) and filter.get('string', False) and \
                                    (not (filter.get('invisible',False) == '1' or filter.get('invisible',False) == 1) ) and (not filter.get('context', False)):

                                domain = [('attribute_name', '=', filter.get('name')),
                                          ('model_id', '=', self.model_id.id), ('node_option', '=', 'filter')]

                                if not store_filters_groups_obj.search(domain):
                                    store_filters_groups_obj.create({
                                        'model_id': self.model_id.id,
                                        'node_option': 'filter',
                                        'attribute_name': filter.get('name'),
                                        'attribute_string': filter.get('string')
                                    })


class store_model_nodes(models.Model):
    _name = 'store.filters.groups'
    _description = 'Store Filters Groups'
    _rec_name = 'attribute_string'

    model_id = fields.Many2one('ir.model', string='Model', index=True, ondelete='cascade', required=True)
    node_option = fields.Selection([('filter','Filter') , ('group','Groups')], string="Node Option",required=True)
    attribute_name = fields.Char('Attribute Name')
    attribute_string = fields.Char('Attribute String', required=True)

    def name_get(self):
        result = []
        for rec in self:
            name = rec.attribute_string
            if rec.attribute_name:
                name = name +' (' + rec.attribute_name + ')'
            result.append((rec.id, name))
        return result
