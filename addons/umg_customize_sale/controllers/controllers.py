# -*- coding: utf-8 -*-
# from odoo import http


# class UmgCustomizeSale(http.Controller):
#     @http.route('/umg_customize_sale/umg_customize_sale', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/umg_customize_sale/umg_customize_sale/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('umg_customize_sale.listing', {
#             'root': '/umg_customize_sale/umg_customize_sale',
#             'objects': http.request.env['umg_customize_sale.umg_customize_sale'].search([]),
#         })

#     @http.route('/umg_customize_sale/umg_customize_sale/objects/<model("umg_customize_sale.umg_customize_sale"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('umg_customize_sale.object', {
#             'object': obj
#         })
