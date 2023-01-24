from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError, ValidationError
import logging


class IncentiveCalculationRule(models.Model):
    _name = 'incentive.calculation.rule'
    _description = 'Incentive Calculation Rule'

    def _default_currency(self):
        return self.env.user.company_id.currency_id.id

    name = fields.Char(string="Name",required=True)

    branch_id = fields.Many2one('business.unit',string="BU/BR")

    user_id = fields.Many2one('res.users',string="User",default=lambda self:self.env.user)

    define_branch_id = fields.Many2one('business.unit',string="Define BU/BR")

    is_active = fields.Boolean(string="Active",default=False,store=True)

    b2b_b2c = fields.Selection([
            ('b2b','B2B'),
            ('b2c','B2C'),
        ],string="B2B/B2C")

    currency_id = fields.Many2one('res.currency',required=True,default=_default_currency)

    different_with_sale_target = fields.Boolean(string="Different With Sales Target",default=False)

    sale_target_amount = fields.Float(string="Sales Target Amount")

    incentive_calculation = fields.Selection([
            ('agent','Fixed Amount Division to Multiple Agent'),
            ('percentage','Fixed Percentage Division to Multiple Agent')
        ],string="Incentive Calculation",default='agent')

    payment_rule = fields.Selection([
            ('invoice','Invoice Based'),
            ('payment','Payment Based'),
            ('both','50% Invoice Based and 50% Payment Based'),
        ],string="Payment Rules",default="invoice",required=True)
    business_id = fields.Many2one('business.unit', string='Business Unit', default=lambda self: self.env.user.current_bu_br_id)


    
    #sale_person_id = fields.Many2one('res.users',string="Salesperson",default=lambda self:self.env.user)
    sale_person_settlement_period = fields.Selection([
            ('monthly','Montly'),
            ('quaterly','Quaterly'),
            ('annually','Annually'),
            ('user_defined','User Defined'),
        ],string="Settlement Period",default="monthly")

    sale_person_used = fields.Boolean(string="Used",default=False)
    sale_person_incentive_percentage = fields.Float(string="Incentive Percentage",required=True)

    sale_person_quaterly_start_date = fields.Date(string="Quaterly Start Date")

    sale_person_quaterly_end_date = fields.Date(string="Quaterly End Date")

    sale_person_quaterly_time = fields.Selection([
            ('3','3'),
            ('4','4')
        ],string="Quaterly Time",default="3")

    sale_person_monthly_start_day = fields.Integer(string="From")
    sale_person_monthly_end_day = fields.Integer(string="To")

    sale_person_annually_date = fields.Date(string="Annual Date")
    sale_person_user_defined_date = fields.Date(string="User Defined Date")

    pooling_settlement_period = fields.Selection([
            ('monthly','Montly'),
            ('quaterly','Quaterly'),
            ('annually','Annually'),
            ('user_defined','User Defined'),
        ],string="Settlement Period",default="monthly")

    pooling_used = fields.Boolean(string="Used",default=False)
    pooling_incentive_percentage = fields.Float(string="Incentive Percentage",required=True)

    pooling_annually_date = fields.Date(string="Annual Date")
    pooling_user_defined_date = fields.Date(string="User Defined Date")


    pooling_quaterly_start_date = fields.Date(string="Quaterly Start Date")
    pooling_quaterly_end_date = fields.Date(string="Quaterly End Date")
    pooling_quaterly_time = fields.Selection([
            ('3','3'),
            ('4','4')
        ],string="Quaterly Time",default="3")

    pooling_monthly_start_day = fields.Integer(string="From")
    pooling_monthly_end_day = fields.Integer(string="To")
    incentive_performance_range_ids = fields.One2many('incentive.performance.range','incentive_calculation_rule_id',string="Incentive Performance Range")
    account_id = fields.Many2one('account.account','Account Incentive', domain="[('bu_br_id','=', business_id)]")
    pooling_account_id = fields.Many2one('account.account','Account Pooling', domain="[('bu_br_id','=', business_id)]")
    journal_id = fields.Many2one('account.journal',string='Journal')
    state = fields.Selection([
        ('draft', 'New'),
        ('gm_agm','Approved GM/AGM'),
        ('coo','Approved COO')], string='Status', readonly=True, default='draft')

    bu_user_approve = fields.Boolean(string="BU User Approve",compute='compute_bu_user_approve')


    def compute_bu_user_approve(self):
        if self.business_id.id == self.env.user.current_bu_br_id.id and self.env.user.user_type_id == 'bu':
            self.bu_user_approve = True
        else:
            self.bu_user_approve = False

    

    def action_gm_agm(self):
        self.state = 'gm_agm'
    
    def action_coo(self):
        self.state = 'coo'

    @api.constrains('sale_person_monthly_start_day','sale_person_monthly_end_day')
    def _check_sale_person_monthly_day(self):
        for line in self:
            if line.sale_person_monthly_start_day > line.sale_person_monthly_end_day:
                raise ValidationError(_('Start day cannot be greater than end day.'))

    @api.constrains('pooling_monthly_start_day','pooling_monthly_end_day')
    def _check_sale_person_monthly_day(self):
        for line in self:
            if line.pooling_monthly_start_day > line.pooling_monthly_end_day:
                raise ValidationError(_('Start day cannot be greater than end day.'))	

    @api.model 
    def create(self, vals):

        if 'sale_person_incentive_percentage' in vals:
            if vals['sale_person_incentive_percentage'] == 0.0:
                raise ValidationError(_('Incentive Percentage for Salesperson must be greater than zero!'))

        if 'pooling_incentive_percentage' in vals:
            if vals['pooling_incentive_percentage'] == 0.0:
                raise ValidationError(_('Incentive Percentage for pooling bu/br must be greater than zero!'))			

        result = super(IncentiveCalculationRule, self).create(vals)

        return result


class IncentivePerformanceRange(models.Model):
    _name = 'incentive.performance.range'
    _description = 'Incentive Performance Range'

    incentive_calculation_rule_id = fields.Many2one('incentive.calculation.rule',string="Incentive Calculation Rule")

    sale_target_operator = fields.Selection([
            ('<','<'),
            ('<=','<='),
            ('>','>'),
            ('>=','>='),
        ],string="Comparison Operator",default=">")

    different_with_sale_target = fields.Boolean(related='incentive_calculation_rule_id.different_with_sale_target')

    sale_target_amount = fields.Float(string="Sales Target Amount",related="incentive_calculation_rule_id.sale_target_amount")

    lower_range = fields.Float(string="Lower Range (%)",default=0.0)

    conditional_operator = fields.Selection([
            ('>=','>='),
            ('>','>'),
            ('<=','<='),
            ('<','<'),
            ('between','Between')
        ],string="Conditional Operator",help="Between Operator takes less than from higher_range and greater than equal to lower range")

    higher_range = fields.Float(string="Higher Range (%)",default=0.0)

    incentive_amount = fields.Float(string="Incentive Amount",default=0.0,required=True)
    incentive_percentage = fields.Float('Incentive (%)')
    outstanding = fields.Float('Outstanding (%)')

