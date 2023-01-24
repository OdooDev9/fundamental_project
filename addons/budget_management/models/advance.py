from asyncio import futures
from curses.ascii import US
from email.policy import default
import re
from wsgiref.simple_server import demo_app

from pyparsing import line
from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import AccessError, UserError, ValidationError, MissingError

class Advance(models.Model):
    _name = 'budget.advance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Budget Advance'

    def action_view_expense(self):
        action = self.env.ref('budget_management.action_expense').read()[0]
        action['domain'] = [('advance_id', '=', self.id)]
        return action
        
    def _compute_expense_count(self):
        for rec in self:
            rec.expense_count = len(self.env['budget.expense'].search([('advance_id', '=', rec.id)]))

    def _set_bu_br_domain(self):
        domain = [('id','=',self.env.user.current_bu_br_id.id)]
        return domain

    def _get_move_line_domain(self):
        if self.env.user.user_type_id == 'div' or self.env.user.user_type_id == 'cfd':
            return [('account_id', 'in', self.env['account.account'].search([('bu_br_id','=',self.env['business.unit'].search([('business_type','=','cfd')], limit=1).id)]).ids),('advance_move_id','in',self.ids)]
        else:
            return [('account_id', 'in', self.env['account.account'].search([('bu_br_id','=',self.env.user.current_bu_br_id.id)]).ids),('advance_move_id','in',self.ids)]

    name = fields.Char('Reference', copy=False, readonly=True, default=lambda x: _('New'))
    partner_id = fields.Many2one('res.partner', 'Requested Person', default=lambda self: self.env.user.partner_id, tracking=True)
    employee_id = fields.Many2one('hr.employee','Requester/Employee', tracking=True)
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.company.currency_id, tracking=True)
    business_id = fields.Many2one('business.unit', 'Business Unit',default=lambda self: self.env.user.current_bu_br_id,domain=_set_bu_br_domain,required="1", tracking=True)
    note = fields.Text('Note')
    date = fields.Date('Date',default=datetime.today(), tracking=True)
    issue_date = fields.Date('Issue Date', tracking=True)
    company_id = fields.Many2one('res.company', string='Company',default=lambda self: self.env.company, tracking=True)

    state = fields.Selection([('draft','Draft'),
                                ('submit','Budget PIC submitted'),
                                ('superior','Superior Checked'),
                                ('f_and_a_manager_check','F&A Manager Checked'),
                                ('f_and_a_check','F&A Checked'),
                                ('manager','Manager Checked'),
                                ('gm_agm','GM/AGM Approved'), 
                                ('coo','COO'),
                                ('budget_pic','Budget PIC Checked'),
                                ('cfd','CFD GM/AGM Approved'),
                                ('cfo','CFO Approved'),
                                ('cmc','CMC GM Approved'),
                                ('ceo','CEO Approved'),
                                ('boh','BOH Approved'),
                                ('ccd','CCD Approved'),
                                ('confirm', 'Confirmed'),
                                ('paid','Paid'),
                                ('close', 'Closed'),
                                ('rejected','Rejected')], string='State', default='draft', tracking=True)
    sequence = fields.Integer()
    move_line_ids = fields.One2many('account.move.line', 'advance_move_id', 'Move Lines', domain=_get_move_line_domain)
    move_id = fields.Many2one('account.move')
    account_id = fields.Many2one('account.account', tracking=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', tracking=True)
    expense_count = fields.Integer(compute='_compute_expense_count', tracking=True)
    diff = fields.Float(compute='compute_amount_diff')
    line_ids = fields.One2many('budget.advance.line','advance_id', 'Advance')
    total = fields.Float('Total',compute='get_total')
    budget_type = fields.Selection([('include','Include Budget'),('exclude','Exclude Budget')],default='include', string='Budget Type', tracking=True)
    
    superior = fields.Boolean(compute='get_approval',default=False)
    f_n_a_m = fields.Boolean(compute='get_approval',default=False)
    f_n_a = fields.Boolean(compute='get_approval',default=False)
    manager = fields.Boolean(compute='get_approval',default=False)
    gm = fields.Boolean(compute='get_approval',default=False)
    coo = fields.Boolean(compute='get_approval',default=False)
    pic = fields.Boolean(compute='get_approval',default=False)
    cfd = fields.Boolean(compute='get_approval',default=False)
    cmc = fields.Boolean(compute='get_approval',default=False)
    cfo = fields.Boolean(compute='get_approval',default=False)
    ceo = fields.Boolean(compute='get_approval',default=False)
    md = fields.Boolean(compute='get_approval',default=False)
    boh = fields.Boolean(compute='get_approval',default=False)
    ccd = fields.Boolean(compute='get_approval',default=False)
    paid = fields.Boolean('Paid')

    btn_superior = fields.Boolean(default=False)
    btn_f_n_a_m = fields.Boolean(default=False)
    btn_f_n_a = fields.Boolean(default=False)
    btn_manager = fields.Boolean(default=False)
    btn_gm = fields.Boolean(default=False)
    btn_coo = fields.Boolean(default=False)
    btn_pic = fields.Boolean(default=False)
    btn_cfd = fields.Boolean(default=False)
    btn_cmc = fields.Boolean(default=False)
    btn_cfo = fields.Boolean(default=False)
    btn_ceo = fields.Boolean(default=False)
    btn_md = fields.Boolean(default=False)
    btn_boh = fields.Boolean(default=False)
    btn_ccd = fields.Boolean(default=False)

    bu_br_div_user_approve = fields.Boolean(compute="compute_bu_br_div_user_approve")
    cfd_user_approve = fields.Boolean(compute="compute_cfd_user_approve")
    div_user_approve = fields.Boolean(compute="compute_div_user_approve")
    can_superior_approve = fields.Boolean(compute="compute_superior_approve")
    
    # Relation Between Advance/Weekly/Urgent
    weekly_id = fields.Many2one('weekly.budget.request', ondelete='restrict', tracking=True, string="Weekly Budget Ref")
    urgent_id = fields.Many2one('urgent.budget.request', domain=[('state','=','paid')], ondelete='restrict')

    reject_reason = fields.Text(string='Reject Reason', tracking=True)
    reject_user_id = fields.Many2one("res.users","Rejected By")
    attachment_ids = fields.Many2many('ir.attachment','budget_advance_ir_attachment_rel','advance_id','attachment',string="Attachment")
    superior_id = fields.Many2one('res.users','Superior(To)')

    def compute_bu_br_div_user_approve(self):
        for rec in self:
            if rec.business_id.business_type == 'bu' or rec.business_id.business_type == 'br' or rec.business_id.business_type == 'div':
                if rec.business_id.id == self.env.user.current_bu_br_id.id:
                    rec.bu_br_div_user_approve = True
                else:
                    rec.bu_br_div_user_approve = False
            else:
                if self.env.user.user_type_id == 'cfd':
                    rec.bu_br_div_user_approve = True
                else:
                    rec.bu_br_div_user_approve = False

    def compute_cfd_user_approve(self):
        for rec in self:
            if self.env.user.user_type_id == 'cfd':
                rec.cfd_user_approve = True
            else:
                rec.cfd_user_approve = False

    def compute_div_user_approve(self):
        for rec in self:
            if self.env.user.user_type_id == 'div':
                rec.div_user_approve = True
            else:
                rec.div_user_approve = False

    @api.onchange('business_id')
    def onchange_business_id(self):
        if self.business_id:
            weekly_ids = self.env['weekly.budget.request'].search([('business_id','=',self.business_id.id),('state','=','paid')])
            return {'domain':{'weekly_id':[('id','in',weekly_ids.ids)]}}

    @api.onchange('business_id','date','weekly_id','budget_type')
    def onchange_for_analytic_account(self):
        if self.business_id and self.date:
            analytic_account_ids = []
            if self.budget_type == 'include':
                if not self.weekly_id:
                    monthly_id = self.env['monthly.budget.request'].search([('date_start','<=',self.date),('date_end','>=',self.date),('business_id','=',self.business_id.id),('state','=','confirm')])
                    if not monthly_id:
                        raise MissingError("Need to have a confirmed monthly budget for an advance request for "+ str(self.business_id.name)+".")
                    else:
                        for line in monthly_id.line_ids:
                            analytic_account_ids.append(line.analytic_account_id.id)
                        return {'domain': {'analytic_account_id': [('id','in',analytic_account_ids)]}}
                else:
                    for line in self.weekly_id.line_ids:
                        analytic_account_ids.append(line.analytic_account_id.id)
                    return {'domain': {'analytic_account_id': [('id','in',analytic_account_ids)]}}
            else:
                return {'domain': {'analytic_account_id': [('id','in',self.env['account.analytic.account'].search([]).ids)]}}

    @api.depends('btn_superior','superior_id')
    def compute_superior_approve(self):
        for rec in self:
            if self.btn_superior and self.superior_id.id == self.env.user.id:
                rec.can_superior_approve = True
            else:
                rec.can_superior_approve = False

    @api.depends('business_id','currency_id','total','budget_type')
    def get_approval(self):
        for rec in self:
            if rec.business_id and rec.currency_id:
                approval_id = self.env['budget.approval'].search([('business_id','=',rec.business_id.id),('budget_type','=',rec.budget_type),('active','=',True),('currency_id','=',rec.currency_id.id)])
                if not approval_id:
                    raise UserError(_('Define '+ rec.budget_type + ' budget approval for '+rec.business_id.name))
                total = rec.currency_id._convert(rec.total, approval_id.currency_id,self.env.company, self.date)

                line_id = approval_id.line_ids.filtered(lambda x: x.operator == '<=' and x.amount >= total).sorted(key=lambda x: x.amount)
                if not line_id:
                    line_id = approval_id.line_ids.filtered(lambda x: x.operator == '>' and x.amount <= total).sorted(key=lambda x: x.amount)
                if line_id:
                    rec.superior = line_id[0].superior
                    rec.f_n_a_m = line_id[0].f_n_a_m
                    rec.f_n_a = line_id[0].f_n_a
                    rec.manager = line_id[0].manager
                    rec.gm = line_id[0].gm
                    rec.coo = line_id[0].coo
                    rec.pic = line_id[0].pic
                    rec.cfd = line_id[0].cfd
                    rec.cmc = line_id[0].cmc
                    rec.cfo = line_id[0].cfo
                    rec.ceo = line_id[0].ceo
                    rec.md = line_id[0].md
                    rec.boh = line_id[0].boh
                    rec.ccd = line_id[0].ccd
                else:
                    rec.superior = False
                    rec.f_n_a_m = False
                    rec.f_n_a = False
                    rec.manager = False
                    rec.gm = False
                    rec.coo = False
                    rec.pic = False
                    rec.cfd = False
                    rec.cmc = False
                    rec.cfo = False
                    rec.ceo = False
                    rec.md = False
                    rec.boh = False
                    rec.ccd = False
            else:
                rec.superior = False
                rec.f_n_a_m = False
                rec.f_n_a = False
                rec.manager = False
                rec.gm = False
                rec.coo = False
                rec.pic = False
                rec.cfd = False
                rec.cmc = False
                rec.cfo = False
                rec.ceo = False
                rec.md = False
                rec.boh = False
                rec.ccd = False

    @api.depends('line_ids.amount')
    def get_total(self):
        for rec in self:
            if rec.line_ids:
                for line in rec.line_ids:
                    rec.total+= line.amount
            else:
                rec.total = 0.0

    def compute_amount_diff(self):
        for rec in self:
            expense_ids = self.env['budget.expense'].search([('advance_id', '=', rec.id)])
            if expense_ids:
                claim = 0.0
                for expense in expense_ids:
                    claim += expense.claim_amount
                rec.diff = rec.total - claim
            else:
                rec.diff = rec.total
    
    def action_budget_pic_submit(self):
        self.state = 'submit'
        self.get_next_approve_button()

    def action_superior_approve(self):
        self.state = 'superior'
        self.get_next_approve_button()

    def action_f_and_a_manager_approve(self):
        self.state = 'f_and_a_manager_check'
        self.get_next_approve_button()

    def action_f_and_a_approve(self):
        self.state = 'f_and_a_check'
        self.get_next_approve_button()

    def action_manager_approve(self):
        self.state = 'manager'
        self.get_next_approve_button()

    def action_bu_gm_agm_approve(self):
        self.state = 'gm_agm'
        self.get_next_approve_button()

    def coo_approved(self):
        self.state = 'coo'
        self.get_next_approve_button()

    def action_boh_approve(self):
        self.state = 'boh'
        self.get_next_approve_button()

    def action_ccd_approve(self):
        self.state = 'ccd'
        self.get_next_approve_button()

    def budget_pic_checked(self):
        self.state = 'budget_pic'
        self.get_next_approve_button()

    def cfd_gm_agm_approve(self):
        self.state = 'cfd'
        self.get_next_approve_button()

    def cfd_cfo_approve(self):
        self.state = 'cfo'
        self.get_next_approve_button()

    def cmc_gm_approve(self):
        self.state = 'cmc'
        self.get_next_approve_button()

    def action_ceo_approve(self):
        self.btn_ceo = False
        self.get_next_approve_button()

    def action_md_approve(self):
        self.btn_md = False
        self.state = 'confirm'

    # ----------------------------------------------------------

    def get_next_approve_button(self):
        if self.state == 'submit':
            if self.business_id.business_type == 'br':
                if self.superior:
                    if not self.superior_id:
                        raise ValidationError('Please select a superior.')
                    self.btn_superior = True
                elif self.f_n_a:
                    self.btn_f_n_a = True
                elif self.boh:
                    self.btn_boh = True
                elif self.ccd:
                    self.btn_ccd = True
                elif self.pic:
                    self.btn_pic = True
                elif self.cfd:
                    self.btn_cfd = True
                elif self.cfo:
                    self.btn_cfo = True
                elif self.cmc:
                    self.btn_cmc = True
                elif self.ceo:
                    self.btn_ceo = True
                elif self.md: 
                    self.btn_md = True
                else:
                    self.state = 'confirm'
            elif self.business_id.business_type == 'bu':
                if self.superior:
                    if not self.superior_id:
                        raise ValidationError('Please select a superior.')
                    self.btn_superior = True
                elif self.f_n_a_m:
                    self.btn_f_n_a_m = True
                elif self.gm:
                    self.btn_gm = True
                elif self.coo:
                    self.btn_coo = True
                elif self.pic:
                    self.btn_pic = True
                elif self.cfd:
                    self.btn_cfd = True
                elif self.cfo:
                    self.btn_cfo = True
                elif self.cmc:
                    self.btn_cmc = True
                elif self.ceo:
                    self.btn_ceo = True
                elif self.md: 
                    self.btn_md = True
                else:
                    self.state = 'confirm'
            else:
                if self.superior:
                    if not self.superior_id:
                        raise ValidationError('Please select a superior.')
                    self.btn_superior = True
                elif self.manager:
                    self.btn_manager = True
                elif self.gm:
                    self.btn_gm = True
                elif self.coo:
                    self.btn_coo = True
                elif self.pic:
                    self.btn_pic = True
                elif self.cfd:
                    self.btn_cfd = True
                elif self.cfo:
                    self.btn_cfo = True
                elif self.cmc:
                    self.btn_cmc = True
                elif self.ceo:
                    self.btn_ceo = True
                elif self.md: 
                    self.btn_md = True
                else:
                    self.state = 'confirm'
        elif self.state == 'superior':
            self.btn_superior = False
            if self.business_id.business_type == 'br':
                if self.f_n_a:
                    self.btn_f_n_a = True
                elif self.boh:
                    self.btn_boh = True
                elif self.ccd:
                    self.btn_ccd = True
                elif self.pic:
                    self.btn_pic = True
                elif self.cfd:
                    self.btn_cfd = True
                elif self.cfo:
                    self.btn_cfo = True
                elif self.cmc:
                    self.btn_cmc = True
                elif self.ceo:
                    self.btn_ceo = True
                elif self.md: 
                    self.btn_md = True
                else:
                    self.state = 'confirm'
            elif self.business_id.business_type == 'bu':
                if self.f_n_a_m:
                    self.btn_f_n_a_m = True
                elif self.gm:
                    self.btn_gm = True
                elif self.coo:
                    self.btn_coo = True
                elif self.pic:
                    self.btn_pic = True
                elif self.cfd:
                    self.btn_cfd = True
                elif self.cfo:
                    self.btn_cfo = True
                elif self.cmc:
                    self.btn_cmc = True
                elif self.ceo:
                    self.btn_ceo = True
                elif self.md: 
                    self.btn_md = True
                else:
                    self.state = 'confirm'
            else:
                if self.manager:
                    self.btn_manager = True
                elif self.gm:
                    self.btn_gm = True
                elif self.coo:
                    self.btn_coo = True
                elif self.pic:
                    self.btn_pic = True
                elif self.cfd:
                    self.btn_cfd = True
                elif self.cfo:
                    self.btn_cfo = True
                elif self.cmc:
                    self.btn_cmc = True
                elif self.ceo:
                    self.btn_ceo = True
                elif self.md: 
                    self.btn_md = True
                else:
                    self.state = 'confirm'
        elif self.state == 'f_and_a_check' or self.state == 'f_and_a_manager_check' or self.state=='manager':
            self.btn_f_n_a_m = False
            self.btn_f_n_a = False
            self.btn_manager = False
            if self.business_id.business_type == 'br':
                if self.boh:
                    self.btn_boh = True
                elif self.ccd:
                    self.btn_ccd = True
                elif self.pic:
                    self.btn_pic = True
                elif self.cfd:
                    self.btn_cfd = True
                elif self.cfo:
                    self.btn_cfo = True
                elif self.cmc:
                    self.btn_cmc = True
                elif self.ceo:
                    self.btn_ceo = True
                elif self.md: 
                    self.btn_md = True
                else:
                    self.state = 'confirm'
            else:
                if self.gm:
                    self.btn_gm = True
                elif self.coo:
                    self.btn_coo = True
                elif self.pic:
                    self.btn_pic = True
                elif self.cfd:
                    self.btn_cfd = True
                elif self.cfo:
                    self.btn_cfo = True
                elif self.cmc:
                    self.btn_cmc = True
                elif self.ceo:
                    self.btn_ceo = True
                elif self.md: 
                    self.btn_md = True
                else:
                    self.state = 'confirm'
        elif self.state == 'gm_agm':
            self.btn_gm = False
            if self.coo:
                self.btn_coo = True
            elif self.pic:
                self.btn_pic = True
            elif self.cfd:
                self.btn_cfd = True
            elif self.cfo:
                self.btn_cfo = True
            elif self.cmc:
                self.btn_cmc = True
            elif self.ceo:
                self.btn_ceo = True
            elif self.md: 
                self.btn_md = True
            else:
                self.state = 'confirm'
        elif self.state == 'coo':
            self.btn_coo = False
            if self.pic:
                self.btn_pic = True
            elif self.cfd:
                self.btn_cfd = True
            elif self.cfo:
                self.btn_cfo = True
            elif self.cmc:
                self.btn_cmc = True
            elif self.ceo:
                self.btn_ceo = True
            elif self.md: 
                self.btn_md = True
            else:
                self.state = 'confirm'
        elif self.state == 'boh':
            self.btn_boh = False
            if self.ccd:
                self.btn_ccd = True
            elif self.pic:
                self.btn_pic = True
            elif self.cfd:
                self.btn_cfd = True
            elif self.cfo:
                self.btn_cfo = True
            elif self.cmc:
                self.btn_cmc = True
            elif self.ceo:
                self.btn_ceo = True
            elif self.md: 
                self.btn_md = True
            else:
                self.state = 'confirm'
        elif self.state == 'ccd':
            self.btn_ccd = False
            if self.pic:
                self.btn_pic = True
            elif self.cfd:
                self.btn_cfd = True
            elif self.cfo:
                self.btn_cfo = True
            elif self.cmc:
                self.btn_cmc = True
            elif self.ceo:
                self.btn_ceo = True
            elif self.md: 
                self.btn_md = True
            else:
                self.state = 'confirm'
        elif self.state == 'budget_pic':
            self.btn_pic = False
            if self.cfd:
                self.btn_cfd = True
            elif self.cfo:
                self.btn_cfo = True
            elif self.cmc:
                self.btn_cmc = True
            elif self.ceo:
                self.btn_ceo = True
            elif self.md: 
                self.btn_md = True
            else:
                self.state = 'confirm'
        elif self.state == 'cfd':
            self.btn_cfd = False
            if self.cfo:
                self.btn_cfo = True
            elif self.cmc:
                self.btn_cmc = True
            elif self.ceo:
                self.btn_ceo = True
            elif self.md: 
                self.btn_md = True
            else:
                self.state = 'confirm'
        elif self.state == 'cfo':
            self.btn_cfo = False
            if self.cmc:
                self.btn_cmc = True
            elif self.ceo:
                self.btn_ceo = True
            elif self.md: 
                self.btn_md = True
            else:
                self.state = 'confirm'
        elif self.state == 'cmc':
            self.btn_cmc = False
            if self.ceo:
                self.btn_ceo = True
            elif self.md: 
                self.btn_md = True
            else:
                self.state = 'confirm'

    # ----------------------------------------------------------
    def action_close(self):
        self.state = 'close'

    def action_reject(self):
        return {
            "name": "Reject",
            "type": "ir.actions.act_window",
            "res_model": "budget.reject",
            "view_mode": 'form',
            "context": {
                'default_origin_rec_id': int(self.id),
                'default_model_name' : 'budget.advance'
            },
            "target": "new",
        }
    
    def get_sequence(self, business_id=False):

        advance_id = self.env['budget.advance'].search([('business_id', '=', business_id)], order="sequence desc",
                                                           limit=1)
        code = self.env['business.unit'].browse(business_id).code
        sequence = advance_id.sequence
        code = 'ADV' + '-' + code.upper() + '-' + datetime.today().strftime("%Y-%m")+'-'+'%04d' % (int(sequence)+1,)
        return code, int(sequence)+1

    @api.model
    def create(self,values):
        if not values.get('line_ids') or not values['line_ids']:
            raise UserError("Please add advance Line.")
        if not values.get('name', False) or values['name'] == _('New'):
            values['name'], values['sequence'] = self.get_sequence(values.get('business_id', False)) or _('New')
        res = super(Advance, self).create(values)
        return res

    def write(self,values):
        if values.get('line_ids'):
            if not values.get('line_ids')[0][-1] and not values['line_ids'][0][-1] and len(self.line_ids) == len(values.get('line_ids')) and len(self.line_ids)== 1:
                raise UserError("Please add Advance Line.")
        res = super(Advance, self).write(values)
        return res

    @api.onchange('budget_type')
    def onchange_budget_type(self):
        self.weekly_id = False
        self.urgent_id = False
        self.line_ids = False

    # def _get_available_amount_from_weekly_or_monthly(self):
    #     if self.weekly_id:
    #         return self.weekly_id.available_amount
    #     else:
    #         monthly_id = self.env['monthly.budget.request'].search([('date_start','<=',self.date),('date_end','>=',self.date),('business_id','=',self.business_id.id),('state','=','confirm')])
    #         if not monthly_id:
    #             raise MissingError("Need to have a confirmed monthly budget for an advance request or Please select a weekly budget ref.")
    #         else:
    #             extra_allowed_amount = (monthly_id.total * (self.business_id.budget_control_percent/100))
    #             return (monthly_id.total + extra_allowed_amount)

    # @api.onchange('total','weekly_id')
    # def onchange_total(self):
    #     if self.budget_type == 'include' and self.total > 0.0:
    #         available_amount = self._get_available_amount_from_weekly_or_monthly()
    #         if self.total > available_amount:
    #             currency = self.currency_id.name
    #             raise UserError("Your limit amount is "+ str(available_amount) + ".")

    @api.onchange('weekly_id', 'urgent_id')
    def onchange_field(self):
        self.currency_id = self.weekly_id.currency_id.id if self.budget_type == 'include' else self.urgent_id.currency_id.id

    @api.ondelete(at_uninstall=True)
    def _check_state(self):
        for rec in self:
            if rec.state in ('draft'):
                raise UserError(_('You can only delete a draft Request'))

class BudgetAdvanceLine(models.Model):
    _name = 'budget.advance.line'
    _description = 'Advance Line'

    advance_id = fields.Many2one('budget.advance', string='Advance')
    name = fields.Char('Description')
    analytic_account_id = fields.Many2one(related='advance_id.analytic_account_id',string='Analytic Account')
    amount = fields.Float('Received Amount')
    currency_id = fields.Many2one(related='advance_id.currency_id')
    remark = fields.Text('Remark')
    requested_amount = fields.Float('Request Amount')
    business_id = fields.Many2one('business.unit','BU/BR/DIV')
    attachment_ids = fields.Many2many("ir.attachment","advance_line_rel",string="Attachment")

    @api.onchange('requested_amount')
    def onchange_amount(self):
        self.amount = self.requested_amount

    @api.model
    def create(self,values):
        if not values.get('amount') or not values['amount']:
            raise UserError("Please add an amount for Advance line.")
        res = super(BudgetAdvanceLine, self).create(values)
        return res

    def write(self,values):
        amount = values.get('amount') or self.amount
        if amount <= 0.0 :
            raise UserError("Please add an amount greater than zero for Advance line.")
        res = super(BudgetAdvanceLine, self).write(values)
        return res

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    _description = 'Account Move Line'

    advance_move_id = fields.Many2one('budget.advance', 'Advance')

class AccountMove(models.Model):
    _inherit = 'account.move'

    advance_move_id = fields.Many2one('budget.advance', 'Advance')
