from sys import float_repr_style
from pkg_resources import require
from requests import request
from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta

class MonthlyBudgetRequest(models.Model):
    _name = 'monthly.budget.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Monthly Budget Request'

    def action_weekly_items(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("budget_management.action_weekly_budget")
        action['domain'] = [('monthly_id', '=', self.id)]
        return action
    
    def _set_bu_br_domain(self):
        domain = [('id','=',self.env.user.current_bu_br_id.id)]
      
        # domain = ['|',('id', 'in', [bu.id for bu in self.env.user.hr_bu_ids]),('id', 'in', [br.id for br in self.env.user.hr_br_ids])]
        return domain
   
    name = fields.Char('Name', copy=False, readonly=True, default=lambda x: _('New'))
    business_id = fields.Many2one('business.unit','BU/BR/DIV', default=lambda self: self.env.user.current_bu_br_id,domain=_set_bu_br_domain,required="1", tracking=True)
    date = fields.Date('Requested Date', default=datetime.today(), tracking=True)
    user_id = fields.Many2one('res.users','Request User',default=lambda self: self.env.user, tracking=True)
    ref = fields.Char('Yearly Budget Ref')
    date_start = fields.Date('Date Start', tracking=True)
    date_end = fields.Date('Date End', tracking=True)
    currency_id = fields.Many2one('res.currency','Currency', tracking=True)
    company_id = fields.Many2one(
        'res.company', 'Company', index=True,
        default=lambda self: self.env.company)
    line_ids = fields.One2many('monthly.budget.request.line','monthly_id',string='Budget Items')
    sequence = fields.Integer()
    note = fields.Text('Note')
    total = fields.Monetary('Total',compute='get_total', tracking=True)
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
    weekly_count = fields.Integer(compute='get_weekly_count')
    
    bu_br_div_user_approve = fields.Boolean(compute="compute_bu_br_div_user_approve")
    cfd_user_approve = fields.Boolean(compute="compute_cfd_user_approve")
    div_user_approve = fields.Boolean(compute="compute_div_user_approve")

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

    reject_reason = fields.Text(string='Reason', tracking=True)
    reject_user_id = fields.Many2one("res.users","Rejected By")
    superior_id = fields.Many2one('res.users','Superior(To)')

    # related weekly budget
    def _get_field_domain(self):
        return [('state', '=', 'confirm')]
    weekly_ids = fields.One2many('weekly.budget.request', 'monthly_id', string='Weekly Items')

    def get_weekly_count(self):
        for rec in self:
            weekly_ids = self.env['weekly.budget.request'].search([('monthly_id','=',rec.id)])
            rec.weekly_count = len(weekly_ids)

    def get_sequence(self, business_id=False):
        monthly_id = self.env['monthly.budget.request'].search([('business_id', '=', business_id)], order="sequence desc", limit=1)
        code = self.env['business.unit'].browse(business_id).code
        sequence = monthly_id.sequence
        code = 'MBG' + '-' + code.upper() + '-' + datetime.today().strftime("%Y-%m")+'-'+'%04d' % (int(sequence)+1,)
        return code, int(sequence)+1

    @api.depends('line_ids.amount')
    def get_total(self):
        for rec in self:
            if rec.line_ids:
                for line in rec.line_ids: rec.total+= line.amount
            else:
                rec.total = 0.0

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
                approval_id = self.env['budget.request.approval'].search([('business_id','=',rec.business_id.id),('approval_type','=','monthly'),('active','=',True),('currency_id','=',rec.currency_id.id)])
                #approval_id = self.env['budget.request.approval'].search([('business_id','=',self.env['business.unit'].search([('business_type','=','cfd')], limit=1).id),('approval_type','=','monthly'),('active','=',True),('currency_id','=',rec.currency_id.id)])
                if not approval_id:
                    raise UserError(_('Define Monthly budget approval for '+rec.business_id.name+ ' with the currency '+rec.currency_id.name))
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
    
    @api.onchange('date_start','date_end')
    def onchange_date_period(self):
        if self.date_start and self.date_end:
            if self.date_start >= self.date_end:
                raise UserError("Please correctly choose your Budget Date")

    def check_date_constraints(self,date_start,date_end,business_id):
        check_date = datetime.strptime(str(date_start), '%Y-%m-%d').date()
        while(check_date < datetime.strptime(str(date_end), '%Y-%m-%d').date()):
            monthly_budget_ids = self.env['monthly.budget.request'].search([
                                                        ('business_id','=',business_id),('id','!=',self.id),('state','!=','rejected'),
                                                        '&',('date_start','<=',check_date),('date_end','>=',check_date),
                                                    ])
            if monthly_budget_ids:
                raise UserError("You have already created monthly budget for the requested period.")
            check_date = check_date + relativedelta(days=1)
      
    @api.model
    def create(self,values):
        date_start = values.get('date_start')
        date_end = values.get('date_end')
        business_id = values.get('business_id')
        self.check_date_constraints(date_start,date_end,business_id)
        if not values.get('line_ids') or not values['line_ids']:
            raise UserError("Please add Budget Items Line.")
        if not values.get('name', False) or values['name'] == _('New'):
            values['name'], values['sequence'] = self.get_sequence(values.get('business_id', False)) or _('New')
        res = super(MonthlyBudgetRequest, self).create(values)
        return res

    def write(self,values):
        business_id = values.get('business_id') if values.get('business_id') else self.business_id.id
        date_start = values.get('date_start') if values.get('date_start') else self.date_start
        date_end = values.get('date_end') if values.get('date_end') else self.date_end
        self.check_date_constraints(date_start,date_end,business_id)
        if values.get('line_ids'):
            if not values.get('line_ids')[0][-1] and not values['line_ids'][0][-1] and len(self.line_ids) == len(values.get('line_ids')) and len(self.line_ids)== 1:
                raise UserError("Please add Budget Items Line.")
        res = super(MonthlyBudgetRequest, self).write(values)
        return res

    def action_reject(self):
        return {
            "name": "Reject",
            "type": "ir.actions.act_window",
            "res_model": "budget.reject",
            "view_mode": 'form',
            "context": {
                'default_origin_rec_id': int(self.id),
                'default_model_name' : 'monthly.budget.request'
            },
            "target": "new",
        }

    @api.ondelete(at_uninstall=True)
    def _check_state(self):
        for rec in self:
            if rec.state in ('draft'):
                raise UserError(_('You can only delete a draft Request'))

class MonthlyBudgetLine(models.Model):
    _name = 'monthly.budget.request.line'
    _description = 'Monthly Budget Request Items'

    monthly_id = fields.Many2one('monthly.budget.request')
    account_id = fields.Many2one('account.account','Account')
    name = fields.Char('Description')
    analytic_account_id = fields.Many2one('account.analytic.account','Analytic Account')
    amount = fields.Float('Budget Amount')
    currency_id = fields.Many2one(related='monthly_id.currency_id')
    company_id = fields.Many2one(
        'res.company', 'Company', index=True,
        default=lambda self: self.env.company)
    remark = fields.Text('Remark')
    business_id = fields.Many2one('business.unit')
    expense_nature_type = fields.Selection([('cogs','COGS'),
                                        ('opex','OPEX'),
                                        ('capex','CAPEX'),
                                        ('other','OTHER')], string='Expense Nature')

    @api.model
    def create(self,values):
        if not values.get('amount') or not values['amount']:
            raise UserError("Please add an amount for Budget Items Line.")
        res = super(MonthlyBudgetLine, self).create(values)
        return res

    def write(self,values):
        amount = values.get('amount') or self.amount
        if amount <= 0.0 :
            raise UserError("Please add an amount greater than zero for Budget Items Line.")
        res = super(MonthlyBudgetLine, self).write(values)
        return res

    @api.onchange('business_id')
    def onchange_business_id(self):
        if self.business_id:
            if self.business_id.business_type == "br" or self.business_id.business_type == "bu":
                return {'domain': {'account_id': [('bu_br_id', '=', self.business_id.id)]}}
            else:
                return {'domain': {'account_id': [('bu_br_id', '=', self.env['business.unit'].search([('business_type','=','cfd')], limit=1).id)]}}
