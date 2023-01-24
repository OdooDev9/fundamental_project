from email.policy import default
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class BudgetRequestApproval(models.Model):
    _name = 'budget.request.approval'

    name = fields.Char('Description')
    active = fields.Boolean(default=True)
    business_id = fields.Many2one('business.unit',string='BU/BR/DIV')
    business_type = fields.Selection(related="business_id.business_type")
    currency_id = fields.Many2one('res.currency',string='Currency')
    # line_ids = fields.One2many('budget.approval.line','approval_request_id', string='Approval')
    approval_type = fields.Selection([('yearly','Yearly Budget'),
                                        ('monthly','Monthly Budget'),
                                        ('weekly','Weekly Budget')],string='Budget Type')
    superior = fields.Boolean('Superior')
    f_n_a_m = fields.Boolean('F&A Manager')
    f_n_a = fields.Boolean('F&A')
    manager = fields.Boolean('Manager')
    gm = fields.Boolean('GM/AGM')
    coo = fields.Boolean('COO')
    pic = fields.Boolean('PIC')
    cfd = fields.Boolean('CFD GM/AGM')
    cfo = fields.Boolean('CFO')
    ceo = fields.Boolean('CEO')
    boh = fields.Boolean('BOH')
    ccd = fields.Boolean('CCD')
    cmc = fields.Boolean('CMC')
    md = fields.Boolean('MD Office')

    def check_unfinished_records(self,business_id,currency_id):
        if self.approval_type == 'monthly':
            monthly_ids = self.env['monthly.budget.request'].search([('state','not in',['draft','rejected','confirm']),('business_id','=',business_id),('currency_id','=',currency_id)])
            if monthly_ids:
                raise ValidationError('Please confirm the monthly budget records before changing the configuration.')
        else:
            weekly_ids = self.env['weekly.budget.request'].search([('state','not in',['draft','rejected','confirm','paid']),('business_id','=',business_id),('currency_id','=',currency_id)])
            if weekly_ids:
                raise ValidationError('Please confirm the weekly budget records before changing the configuration.')

    def write(self,values):
        business_id = values.get('business_id') or self.business_id.id
        currency_id = values.get('currency_id') or self.currency_id.id
        res = super(BudgetRequestApproval, self).write(values)
        if res:
            self.check_unfinished_records(business_id,currency_id)
        return res

class BudgetApproval(models.Model):
    _name = 'budget.approval'

    name = fields.Char('Description')
    active = fields.Boolean(default=True)
    business_id = fields.Many2one('business.unit',string='BU/BR/DIV')
    business_type = fields.Selection(related="business_id.business_type")
    currency_id = fields.Many2one('res.currency',string='Currency')
    line_ids = fields.One2many('budget.approval.line','approval_id', string='Approval')
    budget_type = fields.Selection([('include','Include Budget'),('exclude','Exclude Budget')],string='Budget Type')

    def check_unfinished_records(self,business_id,currency_id,budget_type):
        advance_ids = self.env['budget.advance'].search([('state','not in',['draft','rejected','confirm','paid','close']),('business_id','=',business_id),('currency_id','=',currency_id),('budget_type','=',budget_type)])
        if advance_ids:
            raise ValidationError('Please finish the advance records before changing the configuration.')
        expense_ids = self.env['budget.expense'].search([('state','not in',['draft','rejected','confirm','paid','close']),('business_id','=',business_id),('currency_id','=',currency_id),('budget_type','=',budget_type)])
        if expense_ids:
            raise ValidationError('Please finish the records before changing the configuration.')

    def write(self,values):
        business_id = values.get('business_id') or self.business_id.id
        currency_id = values.get('currency_id') or self.currency_id.id
        budget_type = values.get('budget_type') or self.budget_type
        res = super(BudgetApproval, self).write(values)
        if res:
            self.check_unfinished_records(business_id,currency_id,budget_type)
        return res

class BudgetApprovalLine(models.Model):
    _name = 'budget.approval.line'

    approval_id = fields.Many2one('budget.approval', string='Budget Approval')
    approval_request_id = fields.Many2one('budget.request.approval', string='Budget Request Approval')
    amount = fields.Float('Amount')
    currency_id = fields.Many2one(related='approval_id.currency_id',string='Currency')

    superior = fields.Boolean('Superior')
    f_n_a_m = fields.Boolean('F&A Manager')
    f_n_a = fields.Boolean('F&A')
    manager = fields.Boolean('Manager')
    gm = fields.Boolean('GM/AGM')
    coo = fields.Boolean('COO')
    pic = fields.Boolean('PIC')
    cfd = fields.Boolean('CFD GM/AGM')
    cfo = fields.Boolean('CFO')
    ceo = fields.Boolean('CEO')
    boh = fields.Boolean('BOH')
    ccd = fields.Boolean('CCD')
    cmc = fields.Boolean('CMC')
    md = fields.Boolean('MD Office')

    operator = fields.Selection([
                                ('<=','<='),
                                ('>','>'),
                            ],string="Comparison Operator",default=">")
