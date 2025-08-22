# -*- coding: utf-8 -*-
# from odoo import http


# class TaxWithholdings(http.Controller):
#     @http.route('/tax_withholdings/tax_withholdings', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/tax_withholdings/tax_withholdings/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('tax_withholdings.listing', {
#             'root': '/tax_withholdings/tax_withholdings',
#             'objects': http.request.env['tax_withholdings.tax_withholdings'].search([]),
#         })

#     @http.route('/tax_withholdings/tax_withholdings/objects/<model("tax_withholdings.tax_withholdings"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('tax_withholdings.object', {
#             'object': obj
#         })
