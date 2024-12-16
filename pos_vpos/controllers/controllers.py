# -*- coding: utf-8 -*-
# from odoo import http


# class PosVpos(http.Controller):
#     @http.route('/pos_vpos/pos_vpos', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/pos_vpos/pos_vpos/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('pos_vpos.listing', {
#             'root': '/pos_vpos/pos_vpos',
#             'objects': http.request.env['pos_vpos.pos_vpos'].search([]),
#         })

#     @http.route('/pos_vpos/pos_vpos/objects/<model("pos_vpos.pos_vpos"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('pos_vpos.object', {
#             'object': obj
#         })
