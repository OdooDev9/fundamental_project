from odoo import models, fields, api,_
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError

class HrEmployeeChangedDevice(models.Model):
    _name = 'hr.employee.changed.device'
    _description='Hr Employee Changed Device'

    employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee',required=True)
    employee_number = fields.Char(string='Employee Number', related='employee_id.emp_id')
    old_device_id = fields.Char(string='Old Device ID')
    new_device_id = fields.Char(string='New Device ID')
    old_img = fields.Binary(string='Old Image')
    new_img = fields.Binary(string='New Image')
    count = fields.Integer(string="Changed Count",default=0)

    def name_get(self):
        return [(record.id,f"{record.employee_id.name} [{record.employee_number}]") for record in self]
    
    @api.constrains('employee_id')
    def _check_description(self):
            for record in self:
                data = record.search_count([('employee_id','=',record.employee_id.id),('id','!=',record.id)])
                if data:
                    raise ValidationError(_("Can't duplicate in Employee ID."))
