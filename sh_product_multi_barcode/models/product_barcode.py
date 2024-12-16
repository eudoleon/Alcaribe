# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ShProductTemplate(models.Model):
    _inherit = 'product.template'

    barcode_line_ids = fields.One2many(
        related='product_variant_ids.barcode_line_ids', readonly=False, ondelete="cascade")

    @api.constrains('barcode','barcode_line_ids')
    def check_uniqe_name(self):
        for rec in self:
            if self.env.company and self.env.company.sh_multi_barcode_unique:
                multi_barcode_id = self.env['product.template.barcode'].search([('name', '=', rec.barcode)])
                if multi_barcode_id:
                    raise ValidationError(_(
                        'Barcode must be unique!'))

    @api.model_create_multi
    def create(self, vals_list):
        ''' Store the initial standard price in order to be able to retrieve the cost of a product template for a given date'''
        templates = super(ShProductTemplate, self).create(vals_list)
        # This is needed to set given values to first variant after creation
        for template, vals in zip(templates, vals_list):
            related_vals = {}
            if vals.get('barcode_line_ids'):
                related_vals['barcode_line_ids'] = vals['barcode_line_ids']
            if related_vals:
                template.write(related_vals)
        return templates
    def _valid_field_parameter(self, field, name):
        return name in ['ondelete'] or super()._valid_field_parameter(field, name)

class ShProduct(models.Model):
    _inherit = 'product.product'

    barcode_line_ids = fields.One2many(
        'product.template.barcode', 'product_id', 'Barcode Lines', ondelete="cascade")

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        res = super(ShProduct, self)._name_search(name=name, args=args,
                                                  operator=operator, limit=limit, name_get_uid=name_get_uid)
        mutli_barcode_search = list(self._search(
            [('barcode_line_ids', '=', name)] + args, limit=limit, access_rights_uid=name_get_uid))
        if mutli_barcode_search:
            return res + mutli_barcode_search
        return res

    @api.constrains('barcode','barcode_line_ids')
    def check_uniqe_name(self):
        for rec in self:
            if self.env.company and self.env.company.sh_multi_barcode_unique:
                multi_barcode_id = self.env['product.template.barcode'].search([('name', '=', rec.barcode)])
                if multi_barcode_id:
                    raise ValidationError(_(
                        'Barcode must be unique!'))
    def _valid_field_parameter(self, field, name):
        return name in ['ondelete'] or super()._valid_field_parameter(field, name)

class ShProductBarcode(models.Model):
    _name = 'product.template.barcode'
    _description = "Product Barcode"

    product_id = fields.Many2one('product.product', 'Product', ondelete="cascade")
    name = fields.Char("Barcode", required=True, ondelete="cascade")

    @api.constrains('name')
    def check_uniqe_name(self):
        for rec in self:
            if self.env.company and self.env.company.sh_multi_barcode_unique:
                product_id = self.env['product.product'].sudo().search(['|',('barcode','=',rec.name),('barcode_line_ids.name','=',rec.name),('id','!=',rec.product_id.id)])
                if product_id:
                    raise ValidationError(_('Barcode must be unique!'))
                else:
                    barcode_id = self.env['product.template.barcode'].search([('name','=',rec.name),('id','!=',rec.id)])
                    if barcode_id:
                        raise ValidationError(_('Barcode must be unique!'))

    def _valid_field_parameter(self, field, name):
        return name in ['ondelete'] or super()._valid_field_parameter(field, name)
