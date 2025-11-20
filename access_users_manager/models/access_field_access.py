# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class accessFieldAccess(models.Model):
    _name = 'field.access'
    _description = 'Field Access'

    access_model_id = fields.Many2one('ir.model', string='Model', domain="[('id', 'in', access_profile_domain_model )]")
    access_field_id = fields.Many2many('ir.model.fields',
                                   string='Field')
    access_field_invisible = fields.Boolean(string='Invisible')
    access_field_readonly = fields.Boolean(string='Readonly')
    access_field_required = fields.Boolean(string='Required')
    access_field_external_link = fields.Boolean(string='Remove External Link')
    access_user_manager_id = fields.Many2one('user.management', string='Management')
    access_profile_domain_model = fields.Many2many('ir.model', related='access_user_manager_id.access_profile_domain_model')

    @api.constrains('access_field_required', 'access_field_readonly', 'access_field_invisible')
    def access_check_field_access(self):
        for rec in self:
            if (rec.access_field_required and rec.access_field_readonly) or (rec.access_field_required and rec.access_field_invisible):
                raise UserError(_('You can not set field as Readonly and Required at same time.'))
