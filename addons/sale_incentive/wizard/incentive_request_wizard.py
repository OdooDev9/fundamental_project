from re import T
from odoo import api, fields, models, _
from datetime import date,datetime
from odoo.exceptions import AccessError, UserError, ValidationError

class IncentiveRequestWizard(models.TransientModel):
    _name = 'incentive.request.wizard'
    _description = ' Incentive Request Wizard'
    
    request_date = fields.Date(default=datetime.today())
    request_wizard_line  = fields.One2many('incentive.request.line.wizard','request_incentive_wizard_id')
    branch_id = fields.Many2one('business.unit', string="Branch Name", required=False,
                                domain="[('business_type','=','br')]")
    business_id = fields.Many2one('business.unit', string="Business Unit", required=False,
                                domain="[('business_type','=','bu')]")
    manager = fields.Boolean()

    @api.model
    def default_get(self, fields):
        res = super(IncentiveRequestWizard, self).default_get(fields)
        incentive_ids = self.env['normal.incentive.main'].browse(self.env.context.get('active_ids', []))
        
        line = []
        bu = set()
        for lines in incentive_ids:
            bu.add(lines.business_id)
            if lines.state == 'incentive_approved':
                
                line.append((0, 0, {
                    'normal_incentive_id': lines.id,
                }))
                res.update({
                    'manager': incentive_ids[0].manager,
                    'branch_id':lines.branch_id[0].id if lines.branch_id else '',
                    'business_id':lines.business_id[0].id,
                    'request_wizard_line': line})
            else:
                raise UserError(_('Your Incentive is not requested, Plz check Your Incentive Line'))

        if len(bu) >1:
            raise UserError(_('Your Incentive is not requested, Business Unit is many differences'))
        if  lines.ready_request_payment == False:
            print(lines,'xxxxxxxxxxxxxxxxxxxxxxxxxx')
            print(lines.ready_request_payment)
            raise ValidationError(_("Invoice hasn't payment yet. After Invoice is payment, Incentive Amount can be request"))


        return res
    
    def process(self):
         
        request_obj = self.env['incentive.request']
        incentive_ids = self.env['normal.incentive.main'].browse(self.env.context.get('active_ids', []))
    

        for request in self:
            for line in request.request_wizard_line:
                if line.normal_incentive_id.state == 'incentive_approved':
                        
                    request_new = request_obj.create({
                        'request_date':request.request_date,
                        'manager':request.manager,
                        'state':'request_incentive_approved',
                        'branch_id':request.branch_id.id,
                        'business_id':request.business_id.id,
                        'incentive_definition_id':incentive_ids[0].incentive_definition_id.id,
                        'incentive_request_line': [(0, 0, {
                            'normal_incentive_id': wiz_line.normal_incentive_id.id,
                            'total':wiz_line.normal_incentive_id.total,
                            'invoice_id':wiz_line.normal_incentive_id.invoice_id.id,
                            'amount_due':wiz_line.normal_incentive_id.due_amount,
                            'paid_amount':wiz_line.normal_incentive_id.paid_amount,
                            'invoice_amount':wiz_line.normal_incentive_id.invoice_amount,
                        }) for wiz_line in request.request_wizard_line],})
                incentive_ids.state = 'request_incentive_approved'
                incentive_ids.incentive_request_id = request_new.id
                return {
                        'name': _('Incentive Request Action'),
                        'view_mode': 'form',
                        'res_model': 'incentive.request',
                        'type': 'ir.actions.act_window',
                        'target': 'current',
                        'res_id': request_new.id,
                        }
                
                # if line.normal_incentive_id.state != 'incentive_approved':
                #     raise UserError(_('Your Incentive is not requested, Plz check Your Incentive Line'))
                # else: 
       


class IncentiveRequestLineWizard(models.TransientModel):
    _name = 'incentive.request.line.wizard'
    _description = ' Incentive Request Line Wizard'

   
    request_incentive_wizard_id = fields.Many2one('incentive.request.wizard')
    normal_incentive_id = fields.Many2one('normal.incentive.main')
  
