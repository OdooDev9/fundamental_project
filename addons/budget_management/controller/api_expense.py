import json
from odoo import http
from odoo import fields
from odoo.http import request
from odoo_rest_framework import jwt_http, validator
import os
from odoo_rest_framework import (
    public_route,
    response_json,
    read_serializer,
    login_required,
    fields_extractor,
report_domain_serialize
)

class ExpenseController(http.Controller):

    @http.route(route="/api/budget-expense/list/", type='http', auth='public',
                csrf=False, cors='*', methods=['GET'])
    def budget_expense_list(self, *args: tuple, **kwargs: dict) -> json:
        # auth
        # http_method, body, headers, token = jwt_http.parse_request()
        # result = validator.verify_token(token)
        # if not result['status']:
        #     return jwt_http.errcode(code=result['code'], message=result['message'])
        try:
            domain = report_domain_serialize(kwargs)
            user = request.env.user.current_bu_br_id

            expense_list = request.env['budget.expense'].sudo().search(domain)
            data = []
            for list_expense in expense_list:
                rev = {
                    "id": list_expense.id,
                    "name": list_expense.name,
                    "employee_id": {
                        "id": list_expense.employee_id.id,
                        "name": list_expense.employee_id.name
                    } if list_expense.employee_id else None,
                    "currency_id": {
                        "id": list_expense.currency_id.id,
                        "name": list_expense.currency_id.name
                    } if list_expense.currency_id else None,
                    "business_id": {
                        "id": list_expense.business_id.id,
                        "name": list_expense.business_id.name
                    }if list_expense.business_id else None,
                    "date": str(list_expense.date) if list_expense.date else None,
                    "state": list_expense.state,
                    "line_ids": [],
                    "expense_type": list_expense.expense_type if list_expense.expense_type else None,
                    "attachment_ids": {
                        "id": list_expense.attachment_ids.id,
                        "name": list_expense.attachment_ids.name
                    } if list_expense.attachment_ids else None,
                    
                }
                if list_expense.expense_type == 'claim':
                    if list_expense.budget_type == 'include':
                        rev.update(
                            budget_type = list_expense.budget_type if list_expense.budget_type else None,
                            weekly_id= {
                                "id": list_expense.weekly_id.id,
                                "name": list_expense.weekly_id.name
                            } if list_expense.weekly_id else None
                        )
                    else:
                        rev.update(budget_type = list_expense.budget_type)
                else:
                    rev.update(
                        advance_id = {
                            "id": list_expense.advance_id.id,
                            "name": list_expense.advance_id.name
                        } if list_expense.advance_id else None
                    )
                for expense_line_ids in list_expense.line_ids:
                    expense_line = lambda x: {
                                                "id": x.id,
                                                "name": x.name if x.name else None,
                                                "account_id": {
                                                    "id": x.account_id.id,
                                                    "name": x.account_id.name,
                                                } if x.account_id else None,
                                                "analytic_account_id": {
                                                    "id": x.analytic_account_id.id,
                                                    "name": x.analytic_account_id.name,
                                                },
                                                "remark": x.remark if x.remark else None,
                                                "requested_amount": x.requested_amount if x.requested_amount else None,
                                                "amount": x.amount if x.amount else None,
                                                "attachment_ids": {
                                                    "id": x.attachment_ids.id,
                                                    "name": x.attachment_ids.name
                                                } if x.attachment_ids else None,
                                            }
                    rev['line_ids'].append(expense_line(expense_line_ids))

                if list_expense.business_id == user:
                    data.append(rev)
                else:
                    data.append(rev)
            return response_json(success=True, message='Success', data=data)
        except Exception as e:
            return response_json(success=False, message=str(e), data=None)  

    @http.route(route="/api/budget-expense/create", type='http', auth='public', csrf=False,
                    cors='*', methods=['POST'])
    def budget_expense_create(self, *args: tuple, **kwargs)-> json:
        raw_body_data = json.loads(http.request.httprequest.data)
        extractor = lambda x: [(0, 0, i) for i in x]
        raw_body_data['line_ids'] = extractor(raw_body_data['line_ids'])

        try:
            expense_ids = request.env['budget.expense']
            expense_id = expense_ids.sudo().create(raw_body_data)
            # if expense_id.business_id == request.env.user.current_bu_br_id:
            return response_json(success=True, message=None, data={"id": expense_id.id})
            #     else:
            #         print(request.env.user.name)
            #         if request.env.user.name == 'Administrator':
            #             return response_json(success=True, message=str('Admin create'), data={"id": expense_id.id})
            #         else:
            #             return response_json(success=False, message=str('Can not create'), data=None)
        except Exception as e:
            return response_json(success=False, message=str(e), data=None)

    @http.route(route="/api/budget-expense/update/", type='http', auth='public',
                csrf=False, cors='*', methods=['PUT'])
    def budget_expense_update(self, *args: tuple, **kwargs: dict) -> json:
        # http_method, body, headers, token = jwt_http.parse_request()
        # result = validator.verify_token(token)
        # if not result['status']:
        #     return jwt_http.errcode(code=result['code'], message=result['message'])
        raw_body_data = json.loads(http.request.httprequest.data)

        model_expense = request.env['budget.expense']
        expense_id = raw_body_data.get("id") or False
        try:
            expense = model_expense.browse(expense_id)
        except Exception as e:
            return jwt_http.response(code=403, message=str(e), success=False)

        def remove_id(data):
            data.pop("id")
            return data

        # Lines create and update
        def fun_line_update(line):
            res = []
            for i in line:
                if i.get('id'):
                    res.append((1, i.get('id'), remove_id(i)))
                else:
                    res.append((0, 0, i))
            return res

        raw_body_data.pop("id")
       
        if raw_body_data.get('line_ids'):
            raw_body_data["line_ids"] = fun_line_update(raw_body_data['line_ids'])
        try:
            expense.sudo().write(raw_body_data)
            
            return jwt_http.response(success=True,
                                     message=f"budget expense id {expense_id} udpate successfully !.",
                                     data={"id": expense_id})
        except Exception as e:
            return jwt_http.response(success=False, message=str(e), data=raw_body_data)