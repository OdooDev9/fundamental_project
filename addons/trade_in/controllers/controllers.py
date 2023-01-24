# -*- coding: utf-8 -*-
# from odoo import http


# class TradeIn(http.Controller):
#     @http.route('/trade_in/trade_in', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/trade_in/trade_in/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('trade_in.listing', {
#             'root': '/trade_in/trade_in',
#             'objects': http.request.env['trade_in.trade_in'].search([]),
#         })

#     @http.route('/trade_in/trade_in/objects/<model("trade_in.trade_in"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('trade_in.object', {
#             'object': obj
#         })
