from odoo import http, _
from odoo.http import request
from odoo_rest_framework import jwt_http,validator,read_serializer,fields_extractor,login_required
import json

class NrcCodeApi(http.Controller):

    @login_required('/api/visit/nrc-code/list/', type='http', auth='public', csrf=False, cors='*',methods=['GET'])
    def get_aftersale_service_list(self,limit=None,offset=1,order=None,**kwargs):
        search_query = []
        for a in kwargs:
            try:
                value = int(kwargs.get(a))
                search_query.append((a,'=',value))
            except:
                values = kwargs.get(a)
                search_query.append((a,'=',values))
        if limit:
            limit = int(limit)
        model_obj = request.env['nrc.no']
        all_fields = fields_extractor(model_object=model_obj)
        deal_after_service_ids = model_obj.sudo().search_read(search_query,fields=all_fields,limit=limit, offset=int(offset)-1 if isinstance(offset,str) else offset-1,order=order)
        value_object =  read_serializer(value_object=deal_after_service_ids)
        return jwt_http.response(success=True,data=value_object)

class NrcDescriptionApi(http.Controller):

    @login_required('/api/visit/nrc-description/list/', type='http', auth='public', csrf=False, cors='*',methods=['GET'])
    def get_aftersale_service_list(self,limit=None,offset=1,order=None,**kwargs):
        search_query = []
        for a in kwargs:
            try:
                value = int(kwargs.get(a))
                search_query.append((a,'=',value))
            except:
                values = kwargs.get(a)
                search_query.append((a,'=',values))
        if limit:
            limit = int(limit)
        model_obj = request.env['nrc.description']
        all_fields = fields_extractor(model_object=model_obj)
        deal_after_service_ids = model_obj.sudo().search_read(search_query,fields=all_fields,limit=limit, offset=int(offset)-1 if isinstance(offset,str) else offset-1,order=order)
        value_object =  read_serializer(value_object=deal_after_service_ids)
        return jwt_http.response(success=True,data=value_object)

class NrcTypeApi(http.Controller):

    @login_required('/api/visit/nrc-type/list/', type='http', auth='public', csrf=False, cors='*',methods=['GET'])
    def get_aftersale_service_list(self,limit=None,offset=1,order=None,**kwargs):
        search_query = []
        for a in kwargs:
            try:
                value = int(kwargs.get(a))
                search_query.append((a,'=',value))
            except:
                values = kwargs.get(a)
                search_query.append((a,'=',values))
        if limit:
            limit = int(limit)
        model_obj = request.env['nrc.type']
        all_fields = fields_extractor(model_object=model_obj)
        deal_after_service_ids = model_obj.sudo().search_read(search_query,fields=all_fields,limit=limit, offset=int(offset)-1 if isinstance(offset,str) else offset-1,order=order)
        value_object =  read_serializer(value_object=deal_after_service_ids)
        return jwt_http.response(success=True,data=value_object)



