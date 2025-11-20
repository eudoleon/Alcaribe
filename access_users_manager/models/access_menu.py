# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.http import request


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        """Hide menu which is selected inside User management only for the selected users"""
        menu_ids = super(IrUiMenu, self).search(args, offset=0, limit=None, order=order, count=False)
        current_user = self.env.user
        company_ids = request.httprequest.cookies.get('cids') if request.httprequest.cookies.get('cids') else False
        current_user.clear_caches()
        if company_ids:
            lst = [int(x) for x in request.httprequest.cookies.get('cids').split(',')]
            access_hide_menu_ids = self.env['user.management'].sudo().search(
                [('access_user_ids', 'in', current_user.ids), ('active', '=', True), ('access_company_ids', 'in', lst)]).mapped(
                'access_hide_menu_ids')
        else:
            access_hide_menu_ids = self.env['user.management'].search(
                [('access_user_ids', 'in', current_user.ids), ('active', '=', True)]).mapped(
                'access_hide_menu_ids')
        menu_ids = menu_ids - access_hide_menu_ids
        return menu_ids
