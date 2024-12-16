# -*- coding: utf-8 -*-
# from odoo import http


# class PurchaseQtyAvailable(http.Controller):
#     @http.route('/purchase_qty_available/purchase_qty_available/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/purchase_qty_available/purchase_qty_available/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('purchase_qty_available.listing', {
#             'root': '/purchase_qty_available/purchase_qty_available',
#             'objects': http.request.env['purchase_qty_available.purchase_qty_available'].search([]),
#         })

#     @http.route('/purchase_qty_available/purchase_qty_available/objects/<model("purchase_qty_available.purchase_qty_available"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('purchase_qty_available.object', {
#             'object': obj
#         })
