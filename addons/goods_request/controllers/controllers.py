# -*- coding: utf-8 -*-
# from odoo import http


# class GoodsRequest(http.Controller):
#     @http.route('/goods_request/goods_request', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/goods_request/goods_request/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('goods_request.listing', {
#             'root': '/goods_request/goods_request',
#             'objects': http.request.env['goods_request.goods_request'].search([]),
#         })

#     @http.route('/goods_request/goods_request/objects/<model("goods_request.goods_request"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('goods_request.object', {
#             'object': obj
#         })
