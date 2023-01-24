# -*- coding: utf-8 -*-
# from odoo import http


# class AddBrand(http.Controller):
#     @http.route('/add_brand/add_brand/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/add_brand/add_brand/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('add_brand.listing', {
#             'root': '/add_brand/add_brand',
#             'objects': http.request.env['add_brand.add_brand'].search([]),
#         })

#     @http.route('/add_brand/add_brand/objects/<model("add_brand.add_brand"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('add_brand.object', {
#             'object': obj
#         })
