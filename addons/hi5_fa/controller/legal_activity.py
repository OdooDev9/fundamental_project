from asyncio.log import logger
import base64
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

class LegalActivityController(http.Controller):

    @login_required(['/web/content',
        '/web/content/<string:xmlid>',
        '/web/content/<string:xmlid>/<string:filename>',
        '/web/content/<int:id>',
        '/web/content/<int:id>/<string:filename>',
        '/web/content/<string:model>/<int:id>/<string:field>',
        '/web/content/<string:model>/<int:id>/<string:field>/<string:filename>'], type='http', auth="public")
    def content_common(self, xmlid=None, model='ir.attachment', id=None, field='datas',
                       filename=None, filename_field='name', unique=None, mimetype=None,
                       download=None, data=None, token=None, access_token=None, **kw):

        return request.env['ir.http']._get_content_common(xmlid=xmlid, model=model, res_id=id, field=field, unique=unique, filename=filename,
            filename_field=filename_field, download=download, mimetype=mimetype, access_token=access_token, token=token)
    

    @login_required(['/api/image/<string:model>/<int:id>/<string:field>'], type='http', auth="public")
    def content_image(self, xmlid=None, model='ir.attachment', id=None, field='datas',
                      filename_field='name', unique=None, filename=None, mimetype=None,
                      download=None, width=0, height=0, crop=False, access_token=None,
                      **kwargs):
        # other kwargs are ignored on purpose
        return request.env['ir.http']._content_image(xmlid=xmlid, model=model, res_id=id, field=field,
                                                     filename_field=filename_field, unique=unique, filename=filename,
                                                     mimetype=mimetype,
                                                     download=download, width=width, height=height, crop=crop,
                                                     quality=int(kwargs.get('quality', 0)), access_token=access_token)

    @http.route(route="/api/legal-activity/list/", type='http', auth='public',
                csrf=False, cors='*', methods=['GET'])
    def legal_activity_list(self, *args: tuple, **kwargs: dict) -> json:
     
        domain =[]
       
        try:
            fields = ['id','customer_name','invoice_type','invoice_no','selling_br','ar_action_type','legal_status','legal_activity_line_ids']
            domain = report_domain_serialize(kwargs)
        
            legal_ids = read_serializer(request.env['ar.legal.activity'].search_read(domain,fields=fields))
            print("*"*100,legal_ids)
            print(type(legal_ids))
            
            

            for legal in legal_ids:
                
                legal_idss = request.env['ar.legal.activity'].search([('id','in',[legal.get('id')])])
                print(legal_idss)
                print(legal_idss.legal_activity_line_ids)
                print(legal_idss.legal_activity_line_ids.attachment_ids)
                
                for att_id in legal_idss.legal_activity_line_ids.attachment_ids:
                    print(att_id)
                    print(att_id.name)
                    print(type(att_id.name))
                print("*****************")

                if legal_idss:
                    for res in legal_idss:
                        for result in res.legal_activity_line_ids:
                            legal_line = lambda x: [{
                                                        "id": x.id,
                                                        "legal_activity_id":{
                                                            "id":x.legal_activity_id.id,
                                                        } if x.legal_activity_id else None,
                                                        "date":str(x.date) if x.date else None,
                                                        "action":x.action if x.action else None,
                                                        "contact_type":x.contact_type if x.contact_type else None,
                                                        "on_target_pic":x.on_target_pic if x.on_target_pic else None,
                                                        "legal_team_pic":x.legal_team_pic if x.legal_team_pic else None,
                                                        "on_target_feedback":x.on_target_feedback if x.on_target_feedback else None,
                                                        "notice_times":x.notice_times if x.notice_times else None,
                                                        "pic_comment":x.pic_comment if x.pic_comment else None,
                                                        "attachment_ids":{
                                                            "id": str(x.attachment_ids),
                                                        }if x.attachment_ids else None,
                                                        "action_date":str(x.action_date) if x.action_date else None
                                                    }]
                            if res == result.legal_activity_id:                                
                                legal.update({'legal_activity_line_ids': legal_line(result)})
                
                # data_result = legal
                # print('*'*12,legal)

            return response_json(success=True, message='Success', data=legal_ids)
        except Exception as e:
            return response_json(success=False, message=str(e), data=None)

    @http.route(route="/api/legal-activity/create/", type='http', auth='public',
                csrf=False, cors='*', methods=['POST'])
    def legal_activity_create(self, *args: tuple, **kwargs)-> json:
        # http_method, body, headers = jwt_http.parse_request()

        raw_body_data = json.loads(http.request.httprequest.data)
        extractor = lambda x: [(0, 0, i) for i in x]
        print("************",extractor)
        raw_body_data["legal_activity_line_ids"] = extractor(raw_body_data["legal_activity_line_ids"])
        # ...
	# code that creates and fills a dictonary with validated data
	# ... 
        try:

            if request.httprequest.method == 'POST':

                legal_id = request.env['ar.legal.activity'].sudo().create(raw_body_data)
                print("*****=====>",legal_id)
                if 'task_attachment' in request.params:
                    attached_files = request.httprequest.files.getlist('task_attachment')
                    for attachment in attached_files:
                        attached_file = attachment.read()
                        request.env['ir.attachment'].sudo().create({
                                    'name': attachment.filename,
                                    'res_model': 'ar.legal.activity',
                                    'res_id': legal_id.id,
                                    'type': 'binary',
                                    'datas_fname': attachment.filename,
                                    'datas': attached_file.encode('base64'),
                                    })  

            # return request.render("hi5_fa.legal_activity", {})
       
            
            return response_json(success=True, message=None, data=[{'id':legal_id.id}])
        except Exception as e:
            return response_json(success=False, message=str(e), data=raw_body_data)














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