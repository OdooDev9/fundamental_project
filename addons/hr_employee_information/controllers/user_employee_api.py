from odoo import http
from odoo.http import request
from odoo_rest_framework import jwt_http,validator,read_serializer,fields_extractor,login_required

class ResUserApiCCD(http.Controller):
   
    @login_required('/api/user/list/', type='http', auth='public', csrf=False, cors='*',methods=['GET'])
    def get_saleman_users(self, limit=None,offset=1,order=None,**kwargs):
        data = []
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
        model_obj = request.env['res.users']
        user_datas = model_obj.search(search_query,limit=limit,order=order,offset=int(offset)-1 if isinstance(offset,str) else offset-1)
        for rec in user_datas:
            data.append({
                'id':rec.id,
                'email':rec.login,
                'name':rec.name,
                'company_id': [{'id': rec.company_id.id, 'name': rec.company_id.name}],
                'employee_info':[{'db_id':rec.employee_id.id,'work_email':rec.work_email,
                                   'employee_id':rec.employee_id.emp_id,'old_employee_id':rec.employee_id.old_id,
                                   'job_id':{'id':rec.employee_id.job_id.id,'name':rec.employee_id.job_id.name},
                                   'personal_phone':rec.employee_id.personal_phone,'faceid':rec.employee_id.faceid,
                                   'holding_id':{"id":rec.employee_id.holding_id.id,'name':rec.employee_id.holding_id.name},
                                   'department_id':{'id':rec.employee_id.department_id.id,'name':rec.employee_id.department_id.name}
                                }]
            })
        return jwt_http.response(message='Users List',success=True,data=data)

class EmployeeApiCCD(http.Controller):

    @login_required('/api/employee/list/', type='http', auth='public', csrf=False, cors='*',methods=['GET'])
    def get_saleman_employee(self, limit=None,offset=1,order=None,**kwargs):
        data = []
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
        model_obj = request.env['hr.employee']
        employee_datas = model_obj.search(search_query,limit=limit,order=order,offset=int(offset)-1 if isinstance(offset,str) else offset-1)
        for rec in employee_datas:

            emp_name = None
            if rec.sir_id and rec.first_name and rec.last_name:
                emp_name = rec.sir_id.name+' '+rec.first_name +' ' + rec.last_name
            data.append({
                'id':rec.id,'name':emp_name,'work_email':rec.work_email,'work_phone':rec.work_phone,'emp_id':rec.emp_id,'wage_type':rec.wage_type,'employee_status':rec.employee_status,
                'hr_company_id':[{'id':rec.company_id.id,'name':rec.company_id.name}],
                'station_id':[{'id':rec.station_id.id,'name':rec.station_id.name}],
                'holding_id':[{'id':rec.holding_id.id,'name':rec.holding_id.name}],
                'sub_id':[{'id':rec.sub_id.id,'name':rec.sub_id.name}],
                'department_id':[{'id':rec.department_id.id,'name':rec.department_id.name}],
                'job_id':[{'id':rec.job_id.id,'name':rec.job_id.name}],
                'position_level_id':[{'id':rec.position_level_id.id,'name':rec.position_level_id.name}],
                'employment_type':rec.employment_type,
            })
        return jwt_http.response(message='Employee List',success=True,data=data)
