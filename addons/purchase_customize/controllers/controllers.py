# -*- coding: utf-8 -*-
# from odoo import http


# class PurchaseCustomize(http.Controller):
#     @http.route('/purchase_customize/purchase_customize', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/purchase_customize/purchase_customize/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('purchase_customize.listing', {
#             'root': '/purchase_customize/purchase_customize',
#             'objects': http.request.env['purchase_customize.purchase_customize'].search([]),
#         })

#     @http.route('/purchase_customize/purchase_customize/objects/<model("purchase_customize.purchase_customize"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('purchase_customize.object', {
#             'object': obj
#         })
