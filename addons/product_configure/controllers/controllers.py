# -*- coding: utf-8 -*-
# from odoo import http


# class ProductConfigure(http.Controller):
#     @http.route('/product_configure/product_configure', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/product_configure/product_configure/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('product_configure.listing', {
#             'root': '/product_configure/product_configure',
#             'objects': http.request.env['product_configure.product_configure'].search([]),
#         })

#     @http.route('/product_configure/product_configure/objects/<model("product_configure.product_configure"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('product_configure.object', {
#             'object': obj
#         })
