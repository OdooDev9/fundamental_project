# -*- coding: utf-8 -*-
# from odoo import http


# class Superdev(http.Controller):
#     @http.route('/superdev/superdev', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/superdev/superdev/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('superdev.listing', {
#             'root': '/superdev/superdev',
#             'objects': http.request.env['superdev.superdev'].search([]),
#         })

#     @http.route('/superdev/superdev/objects/<model("superdev.superdev"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('superdev.object', {
#             'object': obj
#         })
