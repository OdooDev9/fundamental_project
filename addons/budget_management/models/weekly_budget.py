from math import remainder
from xml import dom
from pkg_resources import require
from requests import request
from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta

class WeeklyBudgetRequest(models.Model):
    _name = 'weekly.budget.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Weekly Budget Request'

    def action_move_items(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("budget_management.action_account_moves_all_budget")
        # action['domain'] = [('weekly_budget_id', '=', self.id)]
        action['domain'] = [('weekly_budget_id', '=', self.id),('account_id.bu_br_id','=',self.env.user.current_bu_br_id.id)]
        return action

    def action_journal_entry_items(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("budget_management.action_journal_entry_all_budget")
        if self.env.user.user_type_id == 'br':
            action['domain'] = [('weekly_budget_id', '=', self.id),('hr_br_id','=',self.env.user.current_bu_br_id.id)]
        else:
            action['domain'] = [('weekly_budget_id', '=', self.id),('hr_bu_id','=',self.env.user.current_bu_br_id.id)]
        return action

    def action_view_expense(self):
        self.ensure_one()
        action = self.env.ref('budget_management.action_expense').read()[0]
        action['domain'] = [('weekly_id', '=', self.id)]
        return action

    def _compute_expense_count(self):
        for rec in self:
            rec.expense_count = len(self.env['budget.expense'].search([('weekly_id', '=', rec.id)]))

    expense_count = fields.Integer(compute='_compute_expense_count')
    
    # not confirmed amount
    def _compute_expense_amount(self):
        for rec in self:
            total = 0.0
            # Claim[budget.expense]  
            for exp in self.env['budget.expense'].search([('weekly_id', '=', rec.id), ('state', 'not in', ['paid', 'close'])]):
                total += exp.total
            # Advance -> Clearance[budget.expense]             
            for exp in self.env['budget.expense'].search([('advance_id', 'in', self.advance_ids.ids), ('state', 'not in', ['paid', 'close'])]):
                total += exp.total             
            rec.expense_amount = total    
    expense_amount = fields.Integer(compute='_compute_expense_amount')
    
    # confirmed amount
    def _compute_expense_amount_confirmed(self):
        for rec in self:
            total = 0.0
            # Claim[budget.expense]
            for exp in self.env['budget.expense'].search([('weekly_id', '=', rec.id), ('state', 'in', ['paid', 'close'])]):
                total += exp.total
            # Advance -> Clearance[budget.expense]
            for exp in self.env['budget.expense'].search([('advance_id', 'in', self.advance_ids.ids), ('state', 'in', ['paid', 'close'])]):
                total += exp.total
            rec.expense_amount_confirmed = total
    expense_amount_confirmed = fields.Integer(compute='_compute_expense_amount_confirmed')

    def _compute_available_amount(self):
        total = 0.0
        for rec in self:
            total = rec.total - (rec.expense_amount_confirmed + rec.expense_amount)
        rec.available_amount = total
    available_amount = fields.Integer(compute='_compute_available_amount')

    def _set_bu_br_domain(self):
        domain = [('id','=',self.env.user.current_bu_br_id.id)]
        # domain = ['|',('id', 'in', [bu.id for bu in self.env.user.hr_bu_ids]),('id', 'in', [br.id for br in self.env.user.hr_br_ids])]
        return domain
   
    name = fields.Char('Name', copy=False, readonly=True, default=lambda x: _('New'))
    business_id = fields.Many2one('business.unit','BU/BR/DIV',default=lambda self: self.env.user.current_bu_br_id,domain=_set_bu_br_domain, required="1", tracking=True)
    date = fields.Date('Requested Date', default=datetime.today(), tracking=True)
    user_id = fields.Many2one('res.users','Request User',default=lambda self: self.env.user, tracking=True)
    date_start = fields.Date('Date Start', tracking=True)
    date_end = fields.Date('Date End', tracking=True)
    currency_id = fields.Many2one('res.currency','Currency')
    company_id = fields.Many2one(
        'res.company', 'Company', index=True,
        default=lambda self: self.env.company)
    line_ids = fields.One2many('weekly.budget.request.line','weekly_id',string='Budget Items')
    sequence = fields.Integer()
    note = fields.Text('Note')
    total = fields.Monetary('Total',compute='get_total', tracking=True)
    received_date = fields.Date('Received Date', tracking=True)
    monthly_id = fields.Many2one('monthly.budget.request','Monthly Budget Ref', ondelete='restrict', tracking=True)
    ref = fields.Char(related='monthly_id.name', string='Monthly Budget Ref', tracking=True)
    # state = fields.Selection([('draft','Draft'),('submit','F&A Manager Checked'),('confirm','Paid'),('rejected','Rejected')],default='draft',string='State', tracking=True)

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
    #Weekly and advance relation
    advance_ids = fields.One2many('budget.advance', 'weekly_id', string='Advance Items', tracking=True)
    reject_reason = fields.Text(string='Reason', tracking=True)
    reject_user_id = fields.Many2one("res.users","Rejected By")

    bu_br_div_user_approve = fields.Boolean(compute="compute_bu_br_div_user_approve")
    cfd_user_approve = fields.Boolean(compute="compute_cfd_user_approve")
    div_user_approve = fields.Boolean(compute="compute_div_user_approve")
    can_edit_access = fields.Boolean(compute="compute_edit_access")
    can_edit_coa = fields.Boolean(compute="compute_edit_coa")
    can_superior_approve = fields.Boolean(compute="compute_superior_approve")

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

    superior_id = fields.Many2one('res.users','Superior(To)')

    def get_sequence(self, business_id=False):
        weekly_id = self.env['weekly.budget.request'].search([('business_id', '=', business_id)], order="sequence desc", limit=1)
        code = self.env['business.unit'].browse(business_id).code
        sequence = weekly_id.sequence
        code = 'WBG' + '-' + code.upper() + '-' + datetime.today().strftime("%Y-%m")+'-'+'%04d' % (int(sequence)+1,)
        return code, int(sequence)+1

    @api.depends('line_ids.amount')
    def get_total(self):
        for rec in self:
            total = 0.00
            if rec.line_ids:
                for line in rec.line_ids: 
                    total += line.amount
            rec.total = total

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

    @api.depends('btn_pic','cfd_user_approve')
    def compute_edit_access(self):
        for rec in self:
            if rec.state == 'confirm' and rec.cfd_user_approve and self.user_has_groups('master_data_extension.group_cashier'):
                rec.can_edit_access = True
            else:
                rec.can_edit_access = False

    @api.depends('btn_f_n_a','btn_f_n_a_m','cfd_user_approve')
    def compute_edit_coa(self):
        for rec in self:
            if rec.btn_f_n_a and self.user_has_groups('product_configure.group_finance_account_pic'):
                rec.can_edit_coa = True
            elif rec.btn_f_n_a_m and self.user_has_groups('product_configure.group_finance_account_head'):
                rec.can_edit_coa = True
            else:
                rec.can_edit_coa = False

    @api.depends('btn_superior','superior_id')
    def compute_superior_approve(self):
        for rec in self:
            if self.btn_superior and self.superior_id.id == self.env.user.id:
                rec.can_superior_approve = True
            else:
                rec.can_superior_approve = False

    @api.depends('business_id','currency_id')
    def get_approval(self):
        for rec in self:
            if rec.business_id and rec.currency_id:
                approval_id = self.env['budget.request.approval'].search([('business_id','=',rec.business_id.id),('approval_type','=','weekly'),('active','=',True),('currency_id','=',rec.currency_id.id)])
                if not approval_id:
                    raise UserError(_('Define Weekly budget approval for '+rec.business_id.name+ ' with the currency '+rec.currency_id.name))
                else:
                    rec.superior = approval_id.superior
                    rec.f_n_a_m = approval_id.f_n_a_m
                    rec.f_n_a = approval_id.f_n_a
                    rec.manager = approval_id.manager
                    rec.gm = approval_id.gm
                    rec.coo = approval_id.coo
                    rec.pic = approval_id.pic
                    rec.cfd = approval_id.cfd
                    rec.cmc = approval_id.cmc
                    rec.cfo = approval_id.cfo
                    rec.ceo = approval_id.ceo
                    rec.md = approval_id.md
                    rec.boh = approval_id.boh
                    rec.ccd = approval_id.ccd
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

    # def check_date_constraints(self,date_start,date_end,business_id):
    #     check_date = datetime.strptime(str(date_start), '%Y-%m-%d').date()
    #     while(check_date < datetime.strptime(str(date_end), '%Y-%m-%d').date()):
    #         weekly_budget_ids = self.env['weekly.budget.request'].search([
    #                                                     ('business_id','=',business_id),('id','!=',self.id),('state','!=','rejected'),
    #                                                     '&',('date_start','<=',check_date),('date_end','>=',check_date),
    #                                                 ])
    #         if weekly_budget_ids:
    #             raise UserError("You have already created weekly budget for the requested period.")
    #         check_date = check_date + relativedelta(days=1)
            
    @api.model
    def create(self,values):
        date_start = values.get('date_start')
        date_end = values.get('date_end')
        business_id = values.get('business_id')
        # self.check_date_constraints(date_start,date_end,business_id)
        monthly_id = self.env['monthly.budget.request'].search([('id','=',values.get('monthly_id'))])
        date_start = fields.Date.to_date (values.get('date_start'))
        date_end = fields.Date.to_date (values.get('date_end'))
        if not (date_start >= monthly_id.date_start and date_start <= monthly_id.date_end) or not (date_end >= monthly_id.date_start and date_end <= monthly_id.date_end):
            raise UserError("Please select the date period between "+ fields.Date.to_string(monthly_id.date_start) + " and "+ fields.Date.to_string(monthly_id.date_end)+ ".")
        if not values.get('line_ids') or not values['line_ids']:
            raise UserError("Please add Budget Items Line.")
        if not values.get('name', False) or values['name'] == _('New'):
            values['name'], values['sequence'] = self.get_sequence(values.get('business_id', False)) or _('New')
        res = super(WeeklyBudgetRequest, self).create(values)
        return res

    def write(self,values):
        business_id = values.get('business_id') if values.get('business_id') else self.business_id.id
        date_start = values.get('date_start') if values.get('date_start') else self.date_start
        date_end = values.get('date_end') if values.get('date_end') else self.date_end
        # self.check_date_constraints(date_start,date_end,business_id)
        date_start = fields.Date.to_date (values.get('date_start')) if values.get('date_start') else self.date_start
        date_end = fields.Date.to_date (values.get('date_end')) if values.get('date_end') else self.date_end
        monthly_id = self.env['monthly.budget.request'].search([('id','=',values.get('monthly_id') if values.get('monthly_id') else self.monthly_id.id)])
        if not (date_start >= monthly_id.date_start and date_start <= monthly_id.date_end) or not (date_end >= monthly_id.date_start and date_end <= monthly_id.date_end):
            raise UserError("Please select the date period between "+ fields.Date.to_string(monthly_id.date_start) + " and "+ fields.Date.to_string(monthly_id.date_end)+ ".")
        if values.get('line_ids'):
            if not values.get('line_ids')[0][-1] and not values['line_ids'][0][-1] and len(self.line_ids) == len(values.get('line_ids')) and len(self.line_ids)== 1:
                raise UserError("Please add Budget Items Line.")
        res = super(WeeklyBudgetRequest, self).write(values)
        return res

    def _get_available_amount_from_monthly(self,monthly_id):
        used_amount = 0.0
        domain = [('monthly_id','=',monthly_id.id)]
        if self._origin.id: domain.append(('id','!=', self._origin.id))
        for w in self.env['weekly.budget.request'].search(domain):
            used_amount += w.total
        return used_amount,self.monthly_id.total - used_amount

    @api.onchange('total')
    def onchange_total(self):
        self.check_available_budget_amount()

    def check_available_budget_amount(self):
        used_amount,remaining_without_current = self._get_available_amount_from_monthly(self.monthly_id)
        if (self.total + used_amount) > (self.monthly_id.total):
            currency = self.currency_id.name
            raise UserError(_(
                f"You reached the limit of Monthly Budget for your request.\nUsed Amount: {used_amount} {currency}\n Remaining Amount Without Current request: {remaining_without_current} {currency}\n Your Request amount: {self.total} {currency}"
            ))

    @api.ondelete(at_uninstall=True)
    def _check_state(self):
        for rec in self:
            if rec.state in ('draft'):
                raise UserError(_('You can only delete a draft Request'))

    @api.onchange('monthly_id')
    def onchange_monthly_id(self):
        if self.monthly_id:
            self.currency_id = self.monthly_id.currency_id.id
            self.line_ids = False
            self.date_start = self.monthly_id.date_start
            self.date_end = self.monthly_id.date_end

    @api.onchange('date_start','date_end')
    def onchange_date_period(self):
        if self.date_start and self.date_end:
            if self.date_start >= self.date_end:
                raise UserError("Please correctly choose your Budget Date")

    def action_reject(self):
        return {
            "name": "Reject",
            "type": "ir.actions.act_window",
            "res_model": "budget.reject",
            "view_mode": 'form',
            "context": {
                'default_origin_rec_id': int(self.id),
                'default_model_name' : 'weekly.budget.request'
            },
            "target": "new",
        }

    def action_paid(self):
        self.check_available_budget_amount()
        return {
                "name": _("Weekly Budget"),
                "type": "ir.actions.act_window",
                "res_model": "weekly.approval.wizard",
                "view_mode": 'form',
                "target": "new",
                "context": {}
            }

class WeeklyBudgetLine(models.Model):
    _name = 'weekly.budget.request.line'
    _description = 'Weekly Budget Request Items'

    monthly_id = fields.Many2one('monthly.budget.request')
    weekly_id = fields.Many2one('weekly.budget.request')
    account_id = fields.Many2one('account.account','Account', domain="[('id','in',coa_ids)]")
    name = fields.Char('Description')
    analytic_account_id = fields.Many2one('account.analytic.account','Analytic Account')
    amount = fields.Monetary('Budget Amount')
    currency_id = fields.Many2one(related='weekly_id.currency_id')
    company_id = fields.Many2one(
        'res.company', 'Company', index=True,
        default=lambda self: self.env.company)
    remark = fields.Text('Remark')
    control_amount = fields.Float('Used Amount')
    monthly_allow_amount = fields.Float('Monthly Allow Amount')
    coa_ids = fields.Many2many('account.account','monthly_coa_rel',string='COA domain')

    @api.onchange('monthly_id')
    def onchage_monthly_for_domain(self):
        if self.monthly_id:
            self.account_id = False
            account_ids = []
            for line in self.monthly_id.line_ids:
                account_ids.append(line.account_id.id)
            # self.coa_ids = account_ids
            self.coa_ids = [(6,0,account_ids)]
            # return {'domain': {'account_id': [('id','in',account_ids)],'analytic_account_id':[('id','in',analytic_account_ids)]}}

    @api.onchange('amount')
    def onchange_budget_amount(self):
        if self.monthly_id and self.amount > 0.0:
            if not self.monthly_id:
                raise UserError("Please select a monthly budget ref first.")
            if not self.account_id:
                raise UserError("Please select an account before adding amount")
            for line in self.monthly_id.line_ids:
                if self.account_id == line.account_id:
                    if self.amount > (line.amount - self.control_amount):
                            raise UserError("You can't exceed the amount "+ str(line.amount) + " for the account "+ str(self.account_id.name) + " and left amount is "+ str(line.amount - self.control_amount))

    @api.onchange('account_id')
    def check_amount_control_for_coa(self):
        control_amount = 0.0
        if self.account_id:
            if self.monthly_id:
                previous_weekly_ids = self.env['weekly.budget.request'].search([('monthly_id','=',self.monthly_id.id),('state','=','paid')])
                for rec in previous_weekly_ids:
                    for line in rec.line_ids:
                        if self.account_id == line.account_id:
                            control_amount += line.amount
                for line in self.monthly_id.line_ids:
                    if self.account_id == line.account_id:
                        self.analytic_account_id = line.analytic_account_id.id
                        self.monthly_allow_amount = line.amount
            self.control_amount = control_amount

    @api.model
    def create(self,values):
        if not values.get('amount') or not values['amount']:
            raise UserError("Please add an amount for Budget Items Line.")
        # amount = values.get('amount') or values['amount']
        # control_amount = values.get('control_amount') or values['control_amount']
        # monthly_allow_amount = values.get('monthly_allow_amount') or values['monthly_allow_amount']
        # if amount > (monthly_allow_amount - control_amount):
        #     raise UserError("You can't exceed the amount "+ str(amount) + " for the account "+ str(self.account_id.name) + " and left amount is "+ str(line.amount - self.control_amount))
        res = super(WeeklyBudgetLine, self).create(values)
        return res

    def write(self,values):
        amount = values.get('amount') or self.amount
        if amount <= 0.0 :
            raise UserError("Please add an amount greater than zero for Budget Items Line.")
        res = super(WeeklyBudgetLine, self).write(values)
        return res

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    weekly_budget_id = fields.Many2one('weekly.budget.request')
    urgent_budget_id = fields.Many2one('urgent.budget.request')

class AccountMove(models.Model):
    _inherit = 'account.move'

    weekly_budget_id = fields.Many2one('weekly.budget.request')

# class BusinessUnit(models.Model):
#     _inherit = 'business.unit'

#     budget_control_percent = fields.Integer('Extra Budget limited(%)')
