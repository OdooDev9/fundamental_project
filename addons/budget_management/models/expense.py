from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import AccessError, UserError, ValidationError, MissingError

class Expenses(models.Model):
    _name = 'budget.expense'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Budget Expense'

    def _set_bu_br_domain(self):
        domain = [('id','=',self.env.user.current_bu_br_id.id)]
        return domain

    def _get_move_line_domain(self):
        return [('account_id', 'in', self.env['account.account'].search([('bu_br_id','=',self.env.user.current_bu_br_id.id)]).ids),('exp_move_id','in',self.ids)]

    name = fields.Char(copy=False, readonly=True, default=lambda x: _('New'))
    partner_id = fields.Many2one('res.partner', 'Requested Person', default=lambda self: self.env.user.partner_id)
    employee_id = fields.Many2one('hr.employee','Employee')
    currency_id = fields.Many2one('res.currency', 'Currency')
    business_id = fields.Many2one('business.unit', 'Business Unit',default=lambda self: self.env.user.current_bu_br_id,domain=_set_bu_br_domain,required="1")
    total = fields.Float('Amount')
    note = fields.Text('Note')
    date = fields.Date('Date', default=datetime.today())
    company_id = fields.Many2one('res.company', string='Company')
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
    line_ids = fields.One2many('budget.expense.line', 'expense_id', string='Budget Expense Lines')
    ex_sequence = fields.Integer()
    ac_sequence = fields.Integer()
    total = fields.Float('Amount Total', compute='compute_total')
    move_line_ids = fields.One2many('account.move.line', 'exp_move_id', 'Move Lines', domain=_get_move_line_domain)
    move_id = fields.Many2one('account.move')
    advance_id = fields.Many2one('budget.advance')
    advance_amount = fields.Float(related='advance_id.total',string="Advance Total")
    diff_amount = fields.Float('Refund/Additional Total', compute="compute_different_amount")
    claim_amount = fields.Float()
    budget_type = fields.Selection([('include','Include Budget'),('exclude','Exclude Budget')],default='include', string='Budget Type')
    expense_type = fields.Selection([('clear','Clearance'),('claim','Claim')], string='Expense Type')
    
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
    can_edit_coa = fields.Boolean(compute="compute_edit_coa")
    can_superior_approve = fields.Boolean(compute="compute_superior_approve")
    
    # Relation Between Advance/Weekly/Urgent
    weekly_id = fields.Many2one('weekly.budget.request', ondelete='restrict', string="Weekly Budget Ref")
    urgent_id = fields.Many2one('urgent.budget.request', domain=[('state','=','paid')], ondelete='restrict')

    reject_reason = fields.Text(string='Reject Reason', tracking=True)
    reject_user_id = fields.Many2one("res.users","Rejected By")
    attachment_ids = fields.Many2many('ir.attachment','budget_expense_ir_attachment_rel','expense_id','attachment',string="Attachment", required=True)
    superior_id = fields.Many2one('res.users','Superior(To)')

    @api.onchange('business_id','employee_id')
    def onchange_business_id_for_advance_domain(self):
        if self.business_id or self.employee_id:
            return {'domain':{'advance_id':[('employee_id','=',self.employee_id.id),('state','=','paid'),('business_id','=',self.business_id.id)]}}

    @api.onchange('business_id')
    def onchange_business_id_for_weekly_domain(self):
        if self.business_id:
            weekly_ids = self.env['weekly.budget.request'].search([('business_id','=',self.business_id.id),('state','=','paid')])
            return {'domain':{'weekly_id':[('id','in',weekly_ids.ids)]}}

    @api.onchange('advance_id','weekly_id','urgent_id')
    def _get_currency_id(self):
        for rec in self:
            if rec.advance_id:
                rec.currency_id = rec.advance_id.currency_id
            if rec.weekly_id:
                rec.currency_id = rec.weekly_id.currency_id
            if rec.urgent_id:
                rec.currency_id = rec.urgent_id.currency_id

    @api.onchange('budget_type','date','business_id')
    def onchange_budget_type_and_date_and_bu(self):
        self.weekly_id = False
        self.urgent_id = False
        self.line_ids = False

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

    @api.depends('business_id','currency_id','total','budget_type')
    def get_approval(self):
        for rec in self:
            if rec.business_id and rec.currency_id:
                approval_id = self.env['budget.approval'].search([('business_id','=',rec.business_id.id),('budget_type','=',rec.budget_type),('active','=',True),('currency_id','=',rec.currency_id.id)])
                if not approval_id:
                    raise UserError(_('Define '+ rec.budget_type + ' budget approval for '+rec.business_id.name))
                total = rec.currency_id._convert(rec.total, approval_id.currency_id,self.env.company, self.date)
                line_id = approval_id.line_ids.filtered(lambda x: x.operator=='<=' and x.amount >= total).sorted(key=lambda x: x.amount)
                if not line_id:
                    line_id = approval_id.line_ids.filtered(lambda x: x.operator=='>' and x.amount <= total).sorted(key=lambda x: x.amount)
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
    def compute_total(self):
        for rec in self:
            if rec.line_ids:
                for line in rec.line_ids:
                    rec.total += line.amount
            else:rec.total = 0.0

    @api.model
    def create(self,values):
        bu_id = self.env['business.unit'].search([('id','=', values['business_id'])])
        if not values.get('line_ids') or not values['line_ids']:
            raise UserError("Please add expense Line.")
        if not values.get('name', False) or values['name'] == _('New'):
            if values.get('expense_type') == 'clear':
                values['name'] = "EX-"+ str(bu_id.code) + self.env['ir.sequence'].next_by_code('budget.clearance') or 'New'
            elif values.get('expense_type') == 'claim':
                values['name'] = "AC-"+ str(bu_id.code) + self.env['ir.sequence'].next_by_code('budget.claim') or 'New'
        values['claim_amount'] = 0.0
        res = super(Expenses, self).create(values)
        return res
    
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
                'default_model_name' : 'budget.expense'
            },
            "target": "new",
        }
        
    def _get_available_amount_from_weekly(self):
        return self.weekly_id.expense_amount,self.weekly_id.available_amount

    def _get_available_amount_from_urgent(self):
        return self.urgent_id.expense_amount,self.urgent_id.available_amount

    @api.onchange('advance_id')
    def onchange_for_budget_type(self):
        if self.advance_id:
            self.budget_type = self.advance_id.budget_type

    @api.onchange('total')
    def onchange_total(self):
        if self.total < 0.0:
            raise UserError("Amount cannot be negative.")
        elif self.total > 0.0:
            if self.budget_type == 'include':
                used_amount = 0
                urgent_amount = 0
                if self.expense_type == 'claim':
                    monthly_id = self.env['monthly.budget.request'].search([('date_start','<=',self.date),('date_end','>=',self.date),('business_id','=',self.business_id.id),('state','=','confirm')])
                else:
                    monthly_id = self.env['monthly.budget.request'].search([('date_start','<=',self.advance_id.date),('date_end','>=',self.advance_id.date),('business_id','=',self.business_id.id),('state','=','confirm')])
                if not monthly_id:
                    raise MissingError("Need to have a confirmed monthly budget for an request or Please select a weekly budget ref.")
                else:
                    for urgent in self.env['budget.advance'].search([('date','>=',monthly_id.date_start),('date','<=',monthly_id.date_end),('business_id','=',self.business_id.id),('state','in',['paid','close']),('budget_type','=','exclude')]):
                        urgent_amount += urgent.total
                    for expense in self.env['budget.expense'].search([('date','>=',monthly_id.date_start),('date','<=',monthly_id.date_end),('business_id','=',self.business_id.id),('state','in',['paid','close'])]):
                        used_amount += expense.total
                    extra_allowed_amount = ((monthly_id.total+urgent_amount) * (self.business_id.budget_control_percent/100))
                    remaining_without_current = (monthly_id.total + extra_allowed_amount+urgent_amount) - used_amount
                    if self.total > remaining_without_current:
                        currency = self.currency_id.name
                        raise UserError(_(
                            f"You reached the limit of Advance Budget for your request.\n Used Amount for this month: {used_amount}{currency}\n Remaining Amount Without Current request: {remaining_without_current}{currency}\n Your Request amount: {self.total}{currency}"
                        ))
                self.diff_amount = abs(self.total - self.advance_id.total)

    @api.depends('total','advance_id')
    def compute_different_amount(self):
        for rec in self:
            rec.diff_amount = abs(rec.total - rec.advance_id.total)

    @api.ondelete(at_uninstall=True)
    def _check_state(self):
        for rec in self:
            if rec.state in ('draft'):
                raise UserError(_('You can only delete a draft Request'))

    def action_paid(self):
        self.onchange_total()
        return {
                "name": _("Expense(Claim/Clearance)"),
                "type": "ir.actions.act_window",
                "res_model": "expense.wizard",
                "view_mode": 'form',
                "target": "new",
                "context": {}
            }

class ExpenseLine(models.Model):
    _name = 'budget.expense.line'
    _description = 'Budget Expense Line'

    expense_id = fields.Many2one('budget.expense', string='Expense')
    name = fields.Char('Description')
    account_id = fields.Many2one('account.account','Account',domain="[('id','in',coa_ids)]")
    analytic_account_id = fields.Many2one('account.analytic.account','Analytic Account')
    amount = fields.Monetary('Amount')
    currency_id = fields.Many2one(related='expense_id.currency_id')
    remark = fields.Text('Remark')
    no = fields.Integer('No.',compute='_compute_get_number')
    requested_amount = fields.Monetary('Request Amount')
    budget_type = fields.Selection([('include','Include Budget'),('exclude','Exclude Budget')], string='Budget Type')
    expense_type = fields.Selection([('clear','Clearance'),('claim','Claim')], string='Expense Type')
    advance_id = fields.Many2one('budget.advance')
    weekly_id = fields.Many2one('weekly.budget.request', ondelete='restrict', string="Weekly Budget Ref")
    date = fields.Date('Date')
    business_id = fields.Many2one('business.unit', 'Business Unit')
    attachment_ids = fields.Many2many("ir.attachment","expense_line_rel",string="Attachment")
    coa_ids = fields.Many2many('account.account','expense_coa_rel',string='COA domain')

    @api.onchange('requested_amount')
    def onchange_amount(self):
        self.amount = self.requested_amount

    def _compute_get_number(self):
        for order in self.mapped('expense_id'):
            number = 1
            for line in order.line_ids:
                line.no = number
                number += 1

    @api.depends('qty','price')
    def get_subtotal(self):
        for rec in self:
            rec.total = rec.price * rec.qty

    @api.onchange('budget_type','date')
    def onchange_budget_type(self):
        if self.budget_type:
            account_ids = []
            self.account_id = False
            if self.expense_type == 'clear':
                if self.advance_id.weekly_id:
                    for rec in self.advance_id.weekly_id.line_ids:
                        account_ids.append(rec.account_id.id)
                else:
                    if self.advance_id.budget_type == 'include':
                        monthly_id = self.env['monthly.budget.request'].search([('date_start','<=',self.advance_id.date),('date_end','>=',self.advance_id.date),('business_id','=',self.business_id.id),('state','=','confirm')])
                        for line in monthly_id.line_ids:
                            account_ids.append(line.account_id.id)
                    else:
                        all_coa = False
                        if self.business_id.business_type == 'bu' or self.business_id.business_type == 'br':
                            all_coa = self.env['account.account'].search([('bu_br_id','=',self.business_id.id)])
                        else:
                            all_coa = self.env['account.account'].search([('bu_br_id','=',self.env['business.unit'].search([('business_type','=','cfd')], limit=1).id)])
                        for line in all_coa:
                            account_ids.append(line.id)
            else:
                if self.weekly_id:
                    for rec in self.weekly_id.line_ids:
                        account_ids.append(rec.account_id.id)
                else:
                    if self.budget_type == 'include':
                        monthly_id = self.env['monthly.budget.request'].search([('date_start','<=',self.date),('date_end','>=',self.date),('business_id','=',self.business_id.id),('state','=','confirm')])
                        for line in monthly_id.line_ids:
                            account_ids.append(line.account_id.id)
                    else:
                        all_coa = False
                        if self.business_id.business_type == 'bu' or self.business_id.business_type == 'br':
                            all_coa = self.env['account.account'].search([('bu_br_id','=',self.business_id.id)])
                        else:
                            all_coa = self.env['account.account'].search([('bu_br_id','=',self.env['business.unit'].search([('business_type','=','cfd')], limit=1).id)])
                        for line in all_coa:
                            account_ids.append(line.id)
            self.coa_ids = [(6,0,account_ids)]

    @api.onchange('account_id')
    def check_amount_control_for_coa(self):
        if self.account_id:
            if self.expense_type == 'clear':
                if self.advance_id.weekly_id:
                    for line in self.advance_id.weekly_id.line_ids:
                        if self.account_id == line.account_id:
                            self.analytic_account_id = line.analytic_account_id.id
                else:
                    if self.advance_id.budget_type == 'include':
                        monthly_id = self.env['monthly.budget.request'].search([('date_start','<=',self.advance_id.date),('date_end','>=',self.advance_id.date),('business_id','=',self.business_id.id),('state','=','confirm')])
                        for line in monthly_id.line_ids:
                            # print("self.account_id",self.account_id)
                            # print("line.account_id",line.account_id)
                            if self.account_id == line.account_id:
                                # print(".......................my analytic_account_id.....",line.analytic_account_id.name)
                                self.analytic_account_id = line.analytic_account_id.id
                    else:
                        self.analytic_account_id = self.advance_id.analytic_account_id.id
            else:
                if self.weekly_id:
                    for line in self.weekly_id.line_ids:
                        if self.account_id == line.account_id:
                            self.analytic_account_id = line.analytic_account_id.id
                else:
                    if self.budget_type == 'include':
                        monthly_id = self.env['monthly.budget.request'].search([('date_start','<=',self.date),('date_end','>=',self.date),('business_id','=',self.business_id.id),('state','=','confirm')])
                        for line in monthly_id.line_ids:
                            if self.account_id == line.account_id:
                                self.analytic_account_id = line.analytic_account_id.id
                    else:
                        self.analytic_account_id = self.advance_id.analytic_account_id.id

    @api.model
    def create(self,values):
        if not values.get('requested_amount') or not values['requested_amount']:
            raise UserError("Please add an amount for line.")
        res = super(ExpenseLine, self).create(values)
        return res

    def write(self,values):
        amount = values.get('requested_amount') or self.requested_amount
        if amount <= 0.0 :
            raise UserError("Please add an amount greater than zero for line.")
        res = super(ExpenseLine, self).write(values)
        return res

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    _description = 'Account Move Line'

    exp_move_id = fields.Many2one('budget.expense', 'Expense')

class AccountMove(models.Model):
    _inherit = 'account.move'
    _description = 'Account Move'

    exp_move_id = fields.Many2one('budget.expense', 'Expense')
