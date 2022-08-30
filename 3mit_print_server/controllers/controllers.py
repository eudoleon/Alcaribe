# -*- coding: utf-8 -*-
# from odoo import http


# class 3mitPrinter(http.Controller):
#     @http.route('/3mit_printer/3mit_printer/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/3mit_printer/3mit_printer/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('3mit_printer.listing', {
#             'root': '/3mit_printer/3mit_printer',
#             'objects': http.request.env['3mit_printer.3mit_printer'].search([]),
#         })

#     @http.route('/3mit_printer/3mit_printer/objects/<model("3mit_printer.3mit_printer"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('3mit_printer.object', {
#             'object': obj
#         })
