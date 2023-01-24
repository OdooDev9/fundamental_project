# -*- coding: utf-8 -*-
# from odoo import http


# class BorrowRequest(http.Controller):
#     @http.route('/borrow_request/borrow_request', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/borrow_request/borrow_request/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('borrow_request.listing', {
#             'root': '/borrow_request/borrow_request',
#             'objects': http.request.env['borrow_request.borrow_request'].search([]),
#         })

#     @http.route('/borrow_request/borrow_request/objects/<model("borrow_request.borrow_request"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('borrow_request.object', {
#             'object': obj
#         })
