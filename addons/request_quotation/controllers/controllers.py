# -*- coding: utf-8 -*-
# from odoo import http


# class RequestQuotation(http.Controller):
#     @http.route('/request_quotation/request_quotation', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/request_quotation/request_quotation/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('request_quotation.listing', {
#             'root': '/request_quotation/request_quotation',
#             'objects': http.request.env['request_quotation.request_quotation'].search([]),
#         })

#     @http.route('/request_quotation/request_quotation/objects/<model("request_quotation.request_quotation"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('request_quotation.object', {
#             'object': obj
#         })
