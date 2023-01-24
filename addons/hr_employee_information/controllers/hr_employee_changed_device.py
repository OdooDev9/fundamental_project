from ast import arg
from curses import raw
from dataclasses import field
import json
from math import fabs
from odoo import http
from Odoo_API_Library.JwtHttp import jwt_http
from Odoo_API_Library.Validator import validator
from odoo.http import request
from .Serializer import format_json


class HrEmployeeChangedDevice(http.Controller):
    @http.route(route='/api/employee/changed-device/list/', type='http', auth='public', csrf=False, cors='*', methods=['GET'])
    def changed_device_list(self, *args: tuple, **kwargs: dict) -> json:
        _, _, _, token = jwt_http.parse_request()
        result = validator.verify_token(token)
        if not result['status']:
            return jwt_http.errcode(code=result['code'], message=result['message'])
        else:
            model_hr_employee_changed_device = request.env['hr.employee.changed.device']
            fields = ['employee_id', 'employee_number',
                      'old_device_id', 'new_device_id', 'count']
            data = model_hr_employee_changed_device.search_read(
                [], fields=fields)
            return jwt_http.response(data=format_json(data=data))

    @http.route(route='/api/employee/changed-device/update/', type='http', auth='public', csrf=False, cors='*', methods=['PUT'])
    def update_changed_device(self, *args: tuple, **kwargs: dict) -> json:
        _, _, _, token = jwt_http.parse_request()
        result = validator.verify_token(token)
        if not result['status']:
            return jwt_http.errcode(code=result['code'], message=result['message'])
        else:
            raw_body_data = http.request.httprequest.data
            my_json = json.loads(
                raw_body_data.decode('utf8').replace("'", '"'))
            if my_json.get('id'):
                try:
                    employee_changed_device = request.env['hr.employee.changed.device'].browse(my_json.get('id'))
                    print(employee_changed_device)
                    if employee_changed_device:
                        print("*"*50)
                        if my_json.get('new_device_id') and  my_json.get('new_img'):
                            changed_device = employee_changed_device.write(
                                {
                                    'old_device_id': employee_changed_device.new_device_id,
                                    'new_device_id': my_json.get('new_device_id'),
                                    'old_img': employee_changed_device.new_img or False,
                                    'new_img': my_json.get('new_img'),
                                    'count': my_json.get('count')
                                })
                            if changed_device:
                                return jwt_http.response(success=True, message=f"{my_json.get('id')} is update successfully.")
                            else:
                                return jwt_http.response(success=False, message=f"{my_json.get('id')} can't update.")
                        else:
                            return jwt_http.response(success=False, message='invalid you old or new device and old or new image.')
                    else:
                        return jwt_http.response(success=False, message=f"{my_json.get('id')} can't update or this record doesn't have in databases.")
                except:
                    return jwt_http.response(success=False, message="doesn't have this record.")
            else:
                return jwt_http.response(success=False, message="doesn't have this record.")

    @http.route(route='/api/employee/changed-device/create/', type='http', auth='public', csrf=False, cors="*", methods=['POST'])
    def create_changed_device(self) -> json:
        _, _, _, token = jwt_http.parse_request()
        result = validator.verify_token(token)
        if not result['status']:
            return jwt_http.errcode(code=result['code'], message=result['message'])
        else:
            raw_body_data = http.request.httprequest.data
            my_json = json.loads(
                raw_body_data.decode('utf8').replace("'", '"'))
            model_changed_device = request.env['hr.employee.changed.device']
            # print(f"employee_id ==> {my_json.get('employee_id')} {type(my_json.get('employee_id'))}")
            check_data = model_changed_device.search(
                [('employee_id', '=', my_json.get('employee_id'))])
            if not check_data:
                try:
                    created_data = model_changed_device.create(my_json)
                    success, message = True, f"record id {created_data.id} is created successfully."
                except Exception as e:
                    success, message = False, str(e)
            else:
                success, message = False, "Employee ID is already exists."
            return jwt_http.response(success=success, message=message)
