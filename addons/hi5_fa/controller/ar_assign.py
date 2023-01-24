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

class Advanced(http.Controller):
    
    @http.route(route="/api/ar_assign/list/", type='http', auth='public',
                csrf=False, cors='*', methods=['GET'])
    def ar_assign_list(self, *args: tuple, **kwargs: dict) -> json:
        data = []
        domain =[]
        try:
            fields = ['id','name','invoice_id','employee_id','installment_id','business_id','partner_id',
                    'due_amount','collected_amount','total_ar_amount','currency_id','due_date','fine_amount',
                    'remaining_ar_balance','selling_br_id','due_type','ar_action_type',
                    'invoice_type','ar_follow_up_line_ids','ar_confirm_line_ids','ar_remind_line_ids'
                    ]
            domain = report_domain_serialize(kwargs)
        
            assign_ids = read_serializer(request.env['ar.assign.line'].sudo().search_read(domain,fields=fields))
            for assign in assign_ids:
                
                assign_idss = request.env['budget.advance'].sudo().search([('id','in',[assign.get('id')])])
                # print('*'*10,advance)
                if assign_idss:
                    for assign in assign_idss:
                        for result in assign.line_ids:
                            assign_line = lambda x: {
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
                                                        "amount":x.amount if x.currency_id else None,
                                                        "currency_id": {
                                                            "id": x.currency_id.id,
                                                            "name": x.currency_id.name
                                                        } if x.currency_id else None,
                                                        "remark":result.remark if result.remark else None,
                                                        "requested_amount":x.requested_amount if x.requested_amount else None,
                                                    }
                    
                            data.append(assign_line(result))

            assign.update({'line_ids': data})
            return response_json(success=True, message='Success', data=assign_ids)

        except Exception as e:
            return response_json(success=False, message=str(e), data=None)