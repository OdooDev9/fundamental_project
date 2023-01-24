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

class resanced(http.Controller):

    @http.route(route="/api/reposses-activity/list/", type='http', auth='public',
                csrf=False, cors='*', methods=['GET'])
    def reposses_activity_list(self, *args: tuple, **kwargs: dict) -> json:
        # auth
        # http_method, body, headers, token = jwt_http.parse_request()
        # result = validator.verify_token(token)
        # if not result['status']:
        #     return jwt_http.errcode(code=result['code'], message=result['message'])
    
        domain =[]
       
        try:
            fields = ['id','cus_name','invoice_type','invoice_no','selling_br','ar_action_type','reposess_status','ar_repossess_line_ids']
            domain = report_domain_serialize(kwargs)
        
            reposses_ids = read_serializer(request.env['ar.repossess'].search_read(domain,fields=fields))
            print("*"*100,reposses_ids)
            print(type(reposses_ids))
            
            for reposses in reposses_ids:
                
                reposses_idss = request.env['ar.repossess'].search([('id','in',[reposses.get('id')])])
               
                if reposses_idss:
                    for res in reposses_idss:
                        for result in res.ar_repossess_line_ids:
                            reposses_line = lambda x: [{
                                                        "id": x.id,
                                                        "repossess_line_id":{
                                                            "id":x.repossess_line_id.id,
                                                        } if x.repossess_line_id else None,
                                                        "date":str(x.date) if x.date else None,
                                                        "action":x.action if x.action else None,
                                                        "contact_type":x.contact_type if x.contact_type else None,
                                                        "on_target_pic":x.on_target_pic if x.on_target_pic else None,
                                                        "on_target_feedback":x.on_target_feedback if x.on_target_feedback else None,
                                                        "pic_comment":x.pic_comment if x.pic_comment else None,
                                                        "reposess_plan_date":str(x.reposess_plan_date) if x.reposess_plan_date else None,
                                                        "mc_reposess_date":str(x.mc_reposess_date) if x.mc_reposess_date else None,
                                                        "mc_location":x.mc_location if x.mc_location else None,
                                                        "mc_given_back_date":str(x.mc_given_back_date) if x.mc_given_back_date else None
                                                    }]
                            if res == result.repossess_line_id:                                
                                reposses.update({'reposses_activity_line_ids': reposses_line(result)})

            return response_json(success=True, message='Success', data=reposses_ids)
        except Exception as e:
            return response_json(success=False, message=str(e), data=None)

    # @login_required(route="/api/legal-activity/update/", type='http', auth='public',
    #             csrf=False, cors='*', methods=['PUT','PATCH'])
    # def legal_activity_update(self,id, **kwargs):  
    #     try:
    #         legal_ids = request.env['ar.legal.activity'].browse(id)
    #         if legal_ids.create_date:
    #                 legal_list = list(kwargs.items())
    #                 for kwarg in legal_list:
    #                     if type(kwarg[1])!=dict:
    #                         key = [kwarg[0]]
    #                         value = [kwarg[1]]
    #                         legal_ids.write(dict(zip(key,value)))
    #                     else:
    #                         legal_ids.legal_activity_line_ids.write(kwarg[1])
    # # ['id','customer_name','invoice_type','invoice_no','selling_br','ar_action_type','legal_status','legal_activity_line_ids']
    #         return response_json(success=True,message=None,data=[
    #             {
    #                 'customer_name': legal_ids.customer_name,
    #                 'invoice_type': legal_ids.invoice_type,
    #                 'invoice_no':legal_ids.invoice_no,
    #                 'selling_br':legal_ids.selling_br,
    #                 'ar_action_type':legal_ids.ar_action_type,
    #                 'legal_status':legal_ids.legal_status,
    #                 "legal_activity_line_ids": {
    #                                             "id": legal_ids.legal_activity_line_ids.id,
    #                                             "date":str(legal_ids.legal_activity_line_ids.date) ,
    #                                             "action":legal_ids.legal_activity_line_ids.action ,
    #                                             "contact_type":legal_ids.legal_activity_line_ids.contact_type,
    #                                             "on_target_pic":legal_ids.legal_activity_line_ids.on_target_pic,
    #                                             "legal_team_pic":legal_ids.legal_activity_line_ids.legal_team_pic,
    #                                             "on_target_feedback":legal_ids.legal_activity_line_ids.on_target_feedback ,
    #                                             "notice_times":legal_ids.legal_activity_line_ids.notice_times,
    #                                             "pic_comment":legal_ids.legal_activity_line_ids.pic_comment ,
    #                                             # "attachment":str(legal_ids.legal_activity_line_ids.attachment) ,
    #                                             "action_date":str(legal_ids.legal_activity_line_ids.action_date) 
    #                     },
                    
    #                 }
    #         ])
    #         # print(legal_ids)

    #     except Exception as e:
    #         return response_json(success=False, message=str(e), data=None)