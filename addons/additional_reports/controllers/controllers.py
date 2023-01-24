# -*- coding: utf-8 -*-
# from odoo import http


# class AdditionalReports(http.Controller):
#     @http.route('/additional_reports/additional_reports', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/additional_reports/additional_reports/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('additional_reports.listing', {
#             'root': '/additional_reports/additional_reports',
#             'objects': http.request.env['additional_reports.additional_reports'].search([]),
#         })

#     @http.route('/additional_reports/additional_reports/objects/<model("additional_reports.additional_reports"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('additional_reports.object', {
#             'object': obj
#         })
