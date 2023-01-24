from sys import float_repr_style
from pkg_resources import require
from requests import request
from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import UserError
class UrgentBudgetRequest(models.Model):
    _name = 'urgent.budget.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Urgent Budget Request'

    def action_move_items(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_account_moves_all_a")
        action['domain'] = [('urgent_budget_id', '=', self.id),('business_id','=',self.env.user.current_bu_br_id.id)]
        return action

    def action_advances_items(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("budget_management.action_advance")
        action['domain'] = [('urgent_id', '=', self.id)]
        return action
    
    def _set_bu_br_domain(self):
        domain = [('id','=',self.env.user.current_bu_br_id.id)]
      
        # domain = ['|',('id', 'in', [bu.id for bu in self.env.user.hr_bu_ids]),('id', 'in', [br.id for br in self.env.user.hr_br_ids])]
        return domain
   
    def action_view_expense(self):
        self.ensure_one()
        action = self.env.ref('budget_management.action_expense').read()[0]
        action['domain'] = [('urgent_id', '=', self.id)]
        return action

    def _compute_expense_count(self):
        for rec in self:
            rec.expense_count = len(self.env['budget.expense'].search([('urgent_id', '=', rec.id)]))

    expense_count = fields.Integer(compute='_compute_expense_count')
    
    # not confirmed amount
    def _compute_expense_amount(self):
        for rec in self:
            total = 0.0
            for exp in self.env['budget.expense'].search([('urgent_id', '=', rec.id), ('state', 'not in', ['confirm', 'close'])]):
                total += exp.total
            rec.expense_amount = total    
    expense_amount = fields.Integer(compute='_compute_expense_amount')
    
    # confirmed amount
    def _compute_expense_amount_confirmed(self):
        for rec in self:
            total = 0.0
            for exp in self.env['budget.expense'].search([('urgent_id', '=', rec.id), ('state', 'in', ['confirm', 'close'])]):
                total += exp.total
            rec.expense_amount_confirmed = total
    expense_amount_confirmed = fields.Integer(compute='_compute_expense_amount_confirmed')

    # available amount
    def _compute_available_amount(self):
        total = 0.0
        for rec in self:
            total = rec.total - (rec.expense_amount_confirmed + rec.expense_amount)
        rec.available_amount = total
    available_amount = fields.Integer(compute='_compute_available_amount')

    name = fields.Char('Name', copy=False, readonly=True, default=lambda x: _('New'))
    business_id = fields.Many2one('business.unit','BU/BR/DIV', default=lambda self: self.env.user.current_bu_br_id,domain=_set_bu_br_domain,required="1")
    date = fields.Date('Requested Date', default=datetime.today())
    user_id = fields.Many2one('res.users','Request User',default=lambda self: self.env.user)
    # ref = fields.Char('Yearly Budget Ref')
    date_start = fields.Date('Date Start')
    date_end = fields.Date('Date End')
    currency_id = fields.Many2one('res.currency','Currency')
    line_ids = fields.One2many('urgent.budget.request.line','request_id',string='Budget Items')
    sequence = fields.Integer()
    note = fields.Text('Note')
    total = fields.Monetary('Total',compute='get_total')
    state = fields.Selection([('draft','Draft'),('submit','F&A M Checked'),
                              ('boh','BOH Approved'),
                              ('gm_agm','GM/AGM Approved'), ('coo','COO'),
                              ('budget_pic','Budget PIC Checked'),('confirm','CFD Approved'),('paid','Paid')],default='draft',string='State')
    received_date = fields.Date('Received Date')
    bu_br_user_approve = fields.Boolean(compute='compute_bu_br_user_approve')
    br_user_approve = fields.Boolean(compute='compute_br_user_approve')
    cfd_user_approve = fields.Boolean(compute='compute_cfd_user_approve')

    def get_sequence(self, business_id=False):
        urgent_id = self.env['urgent.budget.request'].search([('business_id', '=', business_id)], order="sequence desc", limit=1)
        code = self.env['business.unit'].browse(business_id).code
        sequence = urgent_id.sequence
        code = 'UBR' + '-' + code.upper() + '-' + datetime.today().strftime("%Y-%m")+'-'+'%04d' % (int(sequence)+1,)
        return code, int(sequence)+1

    @api.depends('line_ids.amount')
    def get_total(self):
        if self.line_ids:
            for line in self.line_ids: self.total+= line.amount
        else:
            self.total = 0.0

    def compute_bu_br_user_approve(self):
        for rec in self:
            if rec.business_id.id == self.env.user.current_bu_br_id.id and self.env.user.user_type_id == 'br':
                rec.bu_br_user_approve = True
            if rec.business_id.id == self.env.user.current_bu_br_id.id and self.env.user.user_type_id == 'bu':
                rec.bu_br_user_approve = True      
            else:
                rec.bu_br_user_approve = False
                
    def compute_br_user_approve(self):
        for rec in self:
            if rec.business_id.id == self.env.user.current_bu_br_id.id and self.env.user.user_type_id == 'br':
                rec.br_user_approve = True
            else:
                rec.br_user_approve = False

    def compute_cfd_user_approve(self):
        for rec in self:
            if self.env.user.user_type_id == 'cfd':
                rec.cfd_user_approve = True
            else:
                rec.cfd_user_approve = False

    def action_submit(self):
        self.state = 'submit'
    
    def action_boh(self):
        self.state = 'boh'

    def action_confirm(self):
        self.state = 'confirm'
    
    def gm_approved(self):
        self.state = 'gm_agm'
    
    def coo_approved(self):
        self.state = 'coo'
    
    def budget_pic_checked(self):
        self.state = 'budget_pic'
    
    # def action_confirm(self):
    #     self.state = 'confirm'

    # def _get_available_amount(self):
    #     used_amount = 0.0
    #     for w in self.env['weekly.budget.request'].search([('monthly_id','=',self.id)]):
    #         used_amount += w.total
    #     final = self.total - used_amount
    #     return final
    
    #Urgent and advance relation
    # 
    advance_ids = fields.One2many('budget.advance', 'urgent_id', string='Advance Items')

    @api.ondelete(at_uninstall=True)
    def _check_state(self):
        for rec in self:
            if rec.state in ('draft'):
                raise UserError(_('You can only delete a draft Request'))    

    @api.model
    def create(self,values):
        if not values.get('name', False) or values['name'] == _('New'):
            values['name'], values['sequence'] = self.get_sequence(values.get('business_id', False)) or _('New')
        res = super(UrgentBudgetRequest, self).create(values)
        return res

class UrgentBudgetLine(models.Model):
    _name = 'urgent.budget.request.line'
    _description = 'Urgent Budget Request Items'

    request_id = fields.Many2one('urgent.budget.request')
    account_id = fields.Many2one('account.account','Account')
    name = fields.Char('Description')
    analytic_account_id = fields.Many2one('account.analytic.account','Analytic Account')
    amount = fields.Float('Budget Amount')
    currency_id = fields.Many2one(related='request_id.currency_id')
    remark = fields.Text('Remark')