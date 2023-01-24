# -*- coding: utf-8 -*-
# from odoo import http


# class LandedCosts(http.Controller):
#     @http.route('/landed_costs/landed_costs', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/landed_costs/landed_costs/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('landed_costs.listing', {
#             'root': '/landed_costs/landed_costs',
#             'objects': http.request.env['landed_costs.landed_costs'].search([]),
#         })

#     @http.route('/landed_costs/landed_costs/objects/<model("landed_costs.landed_costs"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('landed_costs.object', {
#             'object': obj
#         })
