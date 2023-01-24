import json
from odoo import http
from odoo.http import request

from odoo_rest_framework import jwt_http
from odoo_rest_framework  import validator
from .response import response


class Employee(http.Controller):

    @http.route('/api/employee/list/', type='http', auth='public', csrf=False, cors='*')
    def get_employee_info(self, **kw):
        datas = []
        http_method, body, headers, token = jwt_http.parse_request()
        result = validator.verify_token(token)
        
        if not result['status']:
            return jwt_http.errcode(code=result['code'], message=result['message'])

        employee_ids = request.env['hr.employee'].sudo().search([('active', '=', True)])
        for rec in employee_ids:
            datas.append({  'id': rec.id,
                            'name': rec.name,
                            'holding_id': [{'id': rec.holding_id.id, 'name': rec.holding_id.name}],
                        })
        return jwt_http.response(data=datas,message='Employee List')

    @http.route('/api/user/list/', type='http', auth='public', csrf=False, cors='*')
    def get_user_info(self, *args:tuple,**kwargs: dict)->json:
        datas = []
        http_method, body, headers, token = jwt_http.parse_request()
        result = validator.verify_token(token)
        
        if not result['status']:
            return jwt_http.errcode(code=result['code'], message=result['message'])

        search_query = []
        if kwargs.get("id"):
            search_query.append(('id','=',kwargs.get("id")))

        user_ids = request.env['res.users'].sudo().search(search_query)
        for rec in user_ids:
            employee_ids = []
            if rec.employee_ids:
                for employee in rec.employee_ids:
                    employee_ids.append({
                                        'db_id': employee.id,
                                        'work_email': employee.work_email,
                                        'name': employee.name,
                                        'holding_id': [{'id': employee.holding_id.id, 'name': employee.holding_id.name}],
                                        'employee_id': employee.emp_id,
                                        'old_employee_id': employee.old_id,
                                        # 'job_id': [{'id': employee.job_id.id, 'name': employee.job_id.name}],
                                        })
            datas.append({  'id': rec.id,
                            'email': rec.login,
                            'name': rec.name,
                            'company_id': [{'id': rec.company_id.id, 'name': rec.company_id.name}],
                            'employee_ids':employee_ids
                        })
        return jwt_http.response(data=datas,message='User(login) List')

    # @http.route(route='/api/employee/list/', type='http', auth='public', csrf=False, cors='*', methods=['GET'])
    # def employee_list(self, *args: dict, **kwargs: dict) -> json:
    #     http_method, body, headers, token = jwt_http.parse_request()
    #     result = validator.verify_token(token)
    #     if not result['status']:
    #         return jwt_http.errcode(code=result['code'], message=result['message'])
    #     fields = ['id', 'name', 'work_email', 'work_phone', 'emp_id', 'wage_type', 'employee_status',
    #               'hr_company_id', 'station_id', 'holding_id', 'sub_id', 'department_id', 'job_id', 'position_level_id',
    #               'employment_type']
    #     employee_list = request.env['hr.employee'].search_read([('active', '=', True)], fields=fields)
    #     return jwt_http.response(data=employee_list)

    # @http.route(route='/api/employee/search/<string:employee_id>/', type='http', auth='public', csrf=False, cors='*')
    # def employee_list_search(self, employee_id, *args: dict, **kwargs: dict) -> json:
    #     # print(employee_id, type(employee_id), "===>")
    #     http_method, body, headers, token = jwt_http.parse_request()
    #     result = validator.verify_token(token)
    #     if not result['status']:
    #         return jwt_http.errcode(code=result['code'], message=result['message'])
    #     fields = ['id', 'name', 'work_email', 'work_phone', 'emp_id', 'wage_type', 'employee_status',
    #               'hr_company_id', 'station_id', 'holding_id', 'sub_id', 'department_id', 'job_id', 'position_level_id',
    #               'employment_type']
    #     employee_list = request.env['hr.employee'].search_read([('active', '=', True), ('emp_id', '=', employee_id)],
    #                                                            fields=fields)
    #     if not employee_list:
    #         return response(success=False, message="this record doesn't have.", data=None)
    #         # jwt_http.response(success=False, message="this record doesn't have.", data=None)
    #     return response(success=True, data=employee_list)  # jwt_http.response(data=employee_list)

    # # Department
    # @http.route('/api/department', type='http', auth='public', csrf=False, cors='*')
    # def get_department(self, **kw):
    #     http_method, body, headers, token = jwt_http.parse_request()
    #     result = validator.verify_token(token)
    #     if not result['status']:
    #         return jwt_http.errcode(code=result['code'], message=result['message'])
    #     else:
    #         fields = [
    #             'name', 'department_code', 'manager_id', 'business_id', 'parent_id'
    #         ]
    #         data = request.env['hr.department'].sudo().search_read([], fields=fields)
    #         return jwt_http.response(success=True, message="Holding Business", data=data)
