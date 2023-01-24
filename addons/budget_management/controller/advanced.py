import json
from odoo import http
from odoo.http import request
from odoo_rest_framework import (
    public_route,
    read_serializer,
    login_required,
    response_json,
    report_domain_serialize,
    jwt_http,
    validator,
)
import werkzeug
HEADERS = [
        ('Content-Type', 'application/json'),
        ('Cache-Control', 'no-store'),
        ('Access-Control-Allow-Origin', '*'),
        ('Access-Control-Allow-Methods', 'GET, POST')
    ]

class Advanced(http.Controller):
    @http.route('/api/weekly-budget-request/list', auth='public')
    def get_budget_request(self, **kwargs):

        fields = [
            'name',
        ]
        domain = []
        for key in kwargs:
            domain.append((key, '=', int(kwargs[key]) if kwargs[key].isdigit() else kwargs[key]))
        try:
            brands = request.env['weekly.budget.request'].sudo().search_read(domain, fields=fields)
            data = json.dumps(brands)
            return request.make_response(data, HEADERS)
        except Exception as error:
            return werkzeug.wrappers.Response(json.dumps({'message': str(error)}), headers=HEADERS, status=404)

    @http.route('/api/account-analytic/list', auth='public')
    def get_account_analytic_list(self, **kwargs):

        fields = [
            'name',
        ]
        domain = []
        for key in kwargs:
            domain.append((key, '=', int(kwargs[key]) if kwargs[key].isdigit() else kwargs[key]))
        try:
            brands = request.env['account.analytic.account'].sudo().search_read(domain, fields=fields)
            data = json.dumps(brands)
            return request.make_response(data, HEADERS)
        except Exception as error:
            return werkzeug.wrappers.Response(json.dumps({'message': str(error)}), headers=HEADERS, status=404)

    @http.route('/api/currency/list', auth='public')
    def get_currency_list(self, **kwargs):

        fields = [
            'name',
        ]
        domain = []
        for key in kwargs:
            domain.append((key, '=', int(kwargs[key]) if kwargs[key].isdigit() else kwargs[key]))
        try:
            brands = request.env['res.currency'].sudo().search_read(domain, fields=fields)
            data = json.dumps(brands)
            return request.make_response(data, HEADERS)
        except Exception as error:
            return werkzeug.wrappers.Response(json.dumps({'message': str(error)}), headers=HEADERS, status=404)
    
    @http.route('/api/business/list', auth='public')
    def get_business_unit(self, **kwargs):
        fields = [
            'name',
            'code',
            'business_type',
            'company',
            'number',
            'building_floor_id',
            'building',
            'street',
            'zone',
            'road',
            'quarter',
            'township_id',
            'city_id',
            'country_id',
            'country_code',
            'active',
            'phone',
            'mobile'
        ]
        domain = []
        for key in kwargs:
            domain.append((key, '=', int(kwargs[key]) if kwargs[key].isdigit() else kwargs[key]))
        print(domain)
        try:
            business_unit = read_serializer(request.env['business.unit'].sudo().search_read(domain, fields=fields))
            data = json.dumps(business_unit)
            return request.make_response(data, HEADERS)
        except Exception as error:
            return werkzeug.wrappers.Response(json.dumps({'message': str(error)}), headers=HEADERS, status=404)
    
    @http.route(route="/api/budget-advance/list/", type='http', auth='public',
                csrf=False, cors='*', methods=['GET'])
    def budget_advance_list(self, *args: tuple, **kwargs: dict) -> json:
        # auth
        # http_method, body, headers, token = jwt_http.parse_request()
        # result = validator.verify_token(token)
        # if not result['status']:
        #     return jwt_http.errcode(code=result['code'], message=result['message'])
        domain =[]
        try:
            fields = ['id','name','partner_id','employee_id','currency_id','business_id','total',
                    'note','date','company_id','state','sequence','move_id','issue_date','analytic_account_id',
                    'expense_count','diff','budget_type','weekly_id','urgent_id','reject_reason','reject_user_id'
                    ,'attachment_ids','line_ids']
            domain = report_domain_serialize(kwargs)
        
            advance_ids = read_serializer(request.env['budget.advance'].sudo().search_read(domain,fields=fields))
            
            for advance in advance_ids:
                
                advance_idss = request.env['budget.advance'].sudo().search([('id','in',[advance.get('id')])])
                # print('*'*10,advance['line_ids'])
                if advance_idss:
                    for adv in advance_idss:
                        for result in adv.line_ids:
                            advance_line = lambda x: [{
                                                        "id": x.id,
                                                        "advance_id":{
                                                            "id":x.advance_id.id,
                                                            "name":x.advance_id.name
                                                        } if x.advance_id else None,
                                                        "name": x.name if x.name else None,
                                                        "analytic_account_id":{
                                                            "id": x.analytic_account_id.id,
                                                            "name":x.analytic_account_id.name
                                                        } if x.analytic_account_id else None,
                                                        "amount":x.amount if x.amount else None,
                                                        "currency_id": {
                                                            "id": x.currency_id.id,
                                                            "name": x.currency_id.name
                                                        } if x.currency_id else None,
                                                        "remark":result.remark if result.remark else None,
                                                        "requested_amount":x.requested_amount if x.requested_amount else None,
                                                        "amount":x.amount if x.amount else None,
                                                        "attachment_ids": {
                                                            "id": x.attachment_ids.id,
                                                            "name": x.attachment_ids.name
                                                        } if x.attachment_ids else None,
                                                    }]
                            if adv == result.advance_id:
                                advance.update({'line_ids': advance_line(result)})
            return response_json(success=True, message='Success', data=advance_ids)
        except Exception as e:
            return response_json(success=False, message=str(e), data=None)


    @http.route(route="/api/budget-advance/create/", type='http', auth='public',
                csrf=False, cors='*', methods=['POST'])

    def budget_advance_create(self, *args: tuple, **kwargs)-> json:
        # http_method, body, headers = jwt_http.parse_request()
        raw_body_data = json.loads(http.request.httprequest.data)
        extractor = lambda x: [(0, 0, i) for i in x]
        # print("************",extractor)
        raw_body_data["line_ids"] = extractor(raw_body_data["line_ids"])

        try:
            budget_advance = request.env['budget.advance']
            advance_id = budget_advance.sudo().create(raw_body_data)
            for line in advance_id.line_ids:
                line.onchange_amount()
            return response_json(success=True, message=None, data=[{'id':advance_id.id}])
        except Exception as e:
            return response_json(success=False, message=str(e), data=raw_body_data)

    @http.route(route="/api/budget-advance/update/", type='http', auth='public',
                csrf=False, cors='*', methods=['PUT'])
    def budget_advance_update(self, *args: tuple, **kwargs: dict) -> json:
        # http_method, body, headers, token = jwt_http.parse_request()
        # result = validator.verify_token(token)
        # if not result['status']:
        #     return jwt_http.errcode(code=result['code'], message=result['message'])
        raw_body_data = json.loads(http.request.httprequest.data)

        model_advance = request.env['budget.advance']
        advance_id = raw_body_data.get("id") or False
        try:
            advance = model_advance.browse(advance_id)
            
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
            # print('raw_body_data line',raw_body_data["line_ids"])

        try:
            
            advance.sudo().write(raw_body_data)
            
            return jwt_http.response(success=True,
                                     message=f"budget advance id {advance_id} udpate successfully !.",
                                     data={"id": advance_id})
        except Exception as e:
            return jwt_http.response(success=False, message=str(e), data=raw_body_data)