# -*- coding: utf-8 -*-
# from odoo import http


# class MasterDataExtension(http.Controller):
#     @http.route('/master_data_extension/master_data_extension/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/master_data_extension/master_data_extension/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('master_data_extension.listing', {
#             'root': '/master_data_extension/master_data_extension',
#             'objects': http.request.env['master_data_extension.master_data_extension'].search([]),
#         })

#     @http.route('/master_data_extension/master_data_extension/objects/<model("master_data_extension.master_data_extension"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('master_data_extension.object', {
#             'object': obj
#         })
