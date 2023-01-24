# -*- coding: utf-8 -*-
# from odoo import http


# class TestNewReport(http.Controller):
#     @http.route('/test_new_report/test_new_report', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/test_new_report/test_new_report/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('test_new_report.listing', {
#             'root': '/test_new_report/test_new_report',
#             'objects': http.request.env['test_new_report.test_new_report'].search([]),
#         })

#     @http.route('/test_new_report/test_new_report/objects/<model("test_new_report.test_new_report"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('test_new_report.object', {
#             'object': obj
#         })
