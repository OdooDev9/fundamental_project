# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError, ValidationError
import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta


class CRMTeam(models.Model):
    _inherit = 'crm.team'

    branch_id = fields.Many2one('business.unit', string="Branch Name", domain="[('business_type','=','br')]")

    business_id = fields.Many2one('business.unit', string="Business Unit", domain="[('business_type','=','bu')]")

    journal_id = fields.Many2one('account.journal', string="Incentive Journal", required=False)

    account_id = fields.Many2one("account.account", string="Incentive Account", required=False)

    product_id = fields.Many2one('product.product', string="Product for Incentive Invoicing", required=False)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    is_incentive_payment = fields.Boolean(string="Is Incentive Payment", search="_search_field")

    def _search_field(self, operator, value):
        field_id = self.search([]).filtered(lambda x: x.is_incentive_payment == value)
        return [('id', operator, [x.id for x in field_id] if field_id else False)]


class AccountMove(models.Model):
    _inherit = 'account.move'

    personal_sale_target_id = fields.Many2one('personal.sale.target', string="Personal Sale Target")

    normal_incentive_id = fields.Many2one('normal.incentive', string="Incentive ID")

    incentive_bill_date = fields.Date(string="Incentive Bill Date")

    is_incentive = fields.Boolean(string="Is Incentive", compute="_compute_is_incentive")

    incentive_quaterly_bonus_id = fields.Many2one('incentive.quaterly.bonus', string="Incentive Quaterly Bonus")


class SaleTarget(models.Model):
    _name = 'sale.target'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Sale Target'

    name = fields.Char(string="Name", required=True)

    branch_ids = fields.Many2many('business.unit', string="Branch Name", required=True,
                                  domain="[('business_type','=','br')]")

    business_unit_id = fields.Many2one('business.unit', string='Business Unit',
                                       domain="[('business_type','=','bu')]")

    b2b_b2c = fields.Selection([
        ('b2b', 'B2B'),
        ('b2c', 'B2C'),
    ], string="B2B/B2C", required=True, default='b2b')

    define_branch_id = fields.Many2one('business.unit', string="Define Branch Name", required=False,
                                       domain="[('business_type','=','br')]")

    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)

    # state = fields.Selection([
    #     ('draft', 'Draft'),
    #     ('request_related_dh_approve', 'Requested Related DH Approve'),
    #     ('related_dh_approved', 'Related DH Approved'),
    #     ('request_gm_approve', 'Requested GM Approve'),
    #     ('gm_approved', 'GM Approved'),
    #     ('request_coo_approve', 'Requested COO Approve'),
    #     ('coo_approved', 'COO Approved'),
    #     ('request_ceo_approve', 'Requested ceo Approve'),
    #     ('ceo_approved', 'CEO Approved'),
    #     ('reject', 'Rejected'),
    # ], string="Status", readonly=True, default="draft", tracking=True)
    state = fields.Selection([
        ('draft', 'New'),
        ('gm_agm','Approved GM/AGM'),
        ('coo','Approved COO')], string='Status', readonly=True, default='draft')



    # incentive_rule_id = fields.Many2one('incentive.calculation.rule',string="Incentive Calculation Rule",domain="[('branch_id','=',branch_id),('is_active','!=',False)]",required=True)
    user_id = fields.Many2one('res.users', string="User", default=lambda self: self.env.user)

    sale_team_target_ids = fields.One2many('sale.team.target', 'sale_target_id', string="Sale Team Targets")

    approval_person = fields.Many2one('res.partner', string="Approval Person")
    dh_id = fields.Many2one('res.users', 'DH')
    gm_id = fields.Many2one('res.users', 'GM')
    coo_id = fields.Many2one('res.users', 'COO')
    ceo_id = fields.Many2one('res.users', 'CEO')
    business_id = fields.Many2one('business.unit', 'Business Unit', required=False,
                                  default=lambda self: self.env.user.current_bu_br_id.id,
                                  domain="[('business_type','=','bu')]")
    active = fields.Boolean(default=True)
    payment_rule = fields.Selection([
        ('invoice', 'Invoice Based'),
        ('payment', 'Payment Based'),
        ('both', '50% Invoice Based and 50% Payment Based'),
    ], string="Payment Rules", default="invoice", required=True)

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
        
    def target_approved(self):
        for rec in self:
            if rec.state == 'request_related_dh_approve':
                rec.state = 'related_dh_approved'
            elif rec.state == 'request_gm_approve':
                rec.state = 'gm_approved'
            elif rec.state == 'request_coo_approve':
                rec.state = 'coo_approved'
            else:
                rec.state = 'ceo_approved'


class SaleTeamTarget(models.Model):
    _name = 'sale.team.target'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Sale Team Target'

    def _default_currency(self):
        return self.env.user.company_id.currency_id.id

    name = fields.Char(string="Name", required=True, default=lambda self: _('New'), readonly=True)

    sale_target_id = fields.Many2one('sale.target', string="Sale Target", required=True, ondelete="cascade")

    branch_ids = fields.Many2many(related="sale_target_id.branch_ids", string="Branches")

    sale_team_id = fields.Many2one('crm.team', string="Sales Team", domain="[('branch_id','in',branch_ids)]",
                                   required=True)

    branch_id = fields.Many2one(related="sale_team_id.branch_id", string="Branch Name")

    journal_id = fields.Many2one(related="incentive_rule_id.journal_id", string="Incentive Journal", required=False)

    account_id = fields.Many2one(related="incentive_rule_id.account_id", string="Incentive Account", required=False)
    pooling_account_id = fields.Many2one(related="incentive_rule_id.pooling_account_id", string="Account Pooling")

    product_id = fields.Many2one(related="sale_team_id.product_id", string="Product for Invoicing", required=False)

    b2b_b2c = fields.Selection(related="sale_target_id.b2b_b2c", string="B2B/B2C")

    define_branch_id = fields.Many2one(related="sale_target_id.define_branch_id", string="Define BU Name")

    start_date = fields.Date(related="sale_target_id.start_date", string="Start Date", required=True)
    end_date = fields.Date(related="sale_target_id.end_date", string="End Date", required=True)
    target = fields.Float(string="Monthly Sales Team Target", required=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('finance_pic','Approved F&A PIC'),
        ('gm_agm','Approved GM/AGM'),
        ('confirm', 'Confirm'),
        ('done', 'Done'),
        ('cancel', 'Cancel'),
    ], string="Status", readonly=True, default="draft", tracking=True)

    incentive_rule_id = fields.Many2one('incentive.calculation.rule', string="Incentive Calculation Rule",
                                        required=True)

    currency_id = fields.Many2one(related='incentive_rule_id.currency_id', string="Currency")

    personal_sale_target_ids = fields.One2many('personal.sale.target', 'sale_team_target_id',
                                               string="Personal Sale Targets")

    approval_person = fields.Many2one('res.partner', string="Approval Person")

    sale_order_count = fields.Integer(string="Sale Order Count", compute="_get_sale_order", readonly=True)
    sale_order_ids = fields.Many2many('sale.order', string="Sale Orders", readonly=True)

    invoice_count = fields.Integer(string="Invoice Count", compute="_get_invoice_count", readonly=True)
    invoice_ids = fields.Many2many('account.move', string="Invoices", compute="_get_invoice_ids", readonly=True)

    user_id = fields.Many2one('res.users', string="User", default=lambda self: self.env.user)

    branch_incentive_created = fields.Boolean(string="Branch Incentive Created")
    business_id = fields.Many2one('business.unit', 'Business Unit', related='sale_target_id.business_id')
    payment_rule = fields.Selection(related='sale_target_id.payment_rule', string="Payment Rules", default="invoice",
                                    required=True)

    bu_user_approve = fields.Boolean(string="BU User Approve",compute='compute_bu_user_approve')


    def compute_bu_user_approve(self):
        if self.business_id.id == self.env.user.current_bu_br_id.id and self.env.user.user_type_id == 'bu':
            self.bu_user_approve = True
        else:
            self.bu_user_approve = False


    @api.depends('sale_order_ids')
    def _get_invoice_ids(self):
        for line in self:
            invoices = []
            for order in line.sale_order_ids:
                if order.invoice_ids:
                    for temp in order.invoice_ids.ids:
                        invoices.append(temp)
            line.invoice_ids = invoices

    def action_finance(self):
        self.state = 'finance_pic'

    def action_gm_agm(self):
        self.state = 'gm_agm'
    def action_confirm(self):
        self.update({
            'state': 'confirm',
        })

    def action_cancel(self):
        self.update({
            'state': 'cancel',
        })

    @api.depends('sale_order_ids')
    def _get_sale_order(self):
        for line in self:
            line.sale_order_count = len(line.sale_order_ids)

    @api.depends('invoice_ids')
    def _get_invoice_count(self):
        for line in self:
            line.invoice_count = len(line.invoice_ids)

    @api.onchange('sale_team_id')
    def _onchange_sale_team_id(self):
        for line in self:

            line.personal_sale_target_ids = [(5, 0, 0)]

            if not line.sale_team_id:
                continue
            if not line.start_date:
                raise ValidationError(_('Start Date cannot be empty. Please fill start date.'))

            if not line.end_date:
                raise ValidationError(_('End Date cannot be empty. Please fill end date.'))

    @api.model
    def create(self, vals):
       
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('sale.team.target', sequence_date=None) or _('New')

        result = super(SaleTeamTarget, self).create(vals)

        members = []

        for member in result.sale_team_id.member_ids:
            members.append((0, 0, {
                'sale_person_id': member.id,
                'start_date': result.start_date,
                'end_date': result.end_date,
                'sale_team_id': result.sale_team_id.id,
                'branch_id': result.branch_id.id,
            }))
        if result.sale_team_id.user_id:
            members.append((0, 0, {
                'sale_person_id': result.sale_team_id.user_id.id,
                'start_date': result.start_date,
                'end_date': result.end_date,
                'sale_team_id': result.sale_team_id.id,
                'branch_id': result.branch_id.id,
            }))

        result.personal_sale_target_ids = members

        if result.start_date > result.end_date:
            raise ValidationError(_('Start date cannot be greater than end date.'))

        old_team_target = self.env['sale.team.target'].search(
            [('id', '!=', result.id), ('sale_team_id', '=', result.sale_team_id.id),
             ('start_date', '>=', result.start_date), ('end_date', '<=', result.end_date)])

        if old_team_target:
            raise ValidationError(
                _("Sale team target is already created for this sale team with selected start date and end date. Please create different sale team or choose different start date and end date."))

        return result

    def action_view_sale_order(self):

        action = self.env.ref('sale_incentive.sale_target_sale_order').read()[0]
        sale_order_ids = self.mapped('sale_order_ids')

        if len(sale_order_ids) > 1:
            action['domain'] = [('id', 'in', sale_order_ids.ids)]
        elif len(sale_order_ids) == 1:
            action['domain'] = [('id', 'in', sale_order_ids.ids)]

        else:
            action = {'type': 'ir.actions.act_window_close'}

        return action

    def action_view_invoice(self):

        invoices = self.mapped('invoice_ids')
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]

        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]

        elif len(invoices) == 1:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = invoices.id

        else:
            action = {'type': 'ir.actions.act_window_close'}

        context = {
            'default_type': 'out_invoice'
        }

        action['context'] = context
        return action


class PersonalSaleTarget(models.Model):
    _name = 'personal.sale.target'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Personal Sale Target'

    def action_move_items(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_account_moves_all_a")
        action['domain'] = [('personal_target_id', '=', self.id),
                            ('business_id', '=', self.env.user.current_bu_br_id.id)]
        return action

    name = fields.Char(string="Name", required=True, default=lambda self: _('New'), readonly=True)

    sale_team_target_id = fields.Many2one('sale.team.target', string="Sale Team Target", required=True,
                                          ondelete="cascade")

    sale_order_ids = fields.Many2many('sale.order', string="Sale Orders", readonly=True,
                                      compute="_compute_sale_order_ids")
    sale_order_count = fields.Integer(string="Sale Order Count", compute="_get_sale_order", readonly=True)

    invoice_count = fields.Integer(string="Invoice Count", compute="_get_invoice_count", readonly=True)
    invoice_ids = fields.Many2many("account.move", string="Invoices", compute="_get_invoice_ids", readonly=True)

    incentive_invoice_count = fields.Integer(string="Incentive Bill Count", compute="_get_incentive_invoice_count",
                                             readonly=True)
    incentive_invoice_ids = fields.Many2many('account.move', string="Invoices", readonly=True)

    user_id = fields.Many2one('res.users', string="User", required=True, default=lambda self: self.env.user)

    incentive_rule_id = fields.Many2one(related="sale_team_target_id.incentive_rule_id",
                                        string="Incentive Calculation Rule")

    sale_team_id = fields.Many2one('crm.team', string="Sales Team", required=True)

    user_team_ids = fields.Many2many('res.users', string="User Teams", compute="_compute_user_team")

    sale_person_id = fields.Many2one('res.users', string="Sale Person", required=True,
                                     domain="[('id','in',user_team_ids)]")

    start_date = fields.Date(related="sale_team_target_id.start_date", string="Start Date")
    end_date = fields.Date(related="sale_team_target_id.end_date", string="End Date")

    branch_id = fields.Many2one('business.unit', string="Branch Name", store=True,
                                domain="[('business_type','=','br')]")

    journal_id = fields.Many2one(related="incentive_rule_id.journal_id", string="Incentive Journal")

    account_id = fields.Many2one(related="incentive_rule_id.account_id", string="Incentive Account")
    pooling_account_id = fields.Many2one(related="incentive_rule_id.pooling_account_id", string="Account Pooling")

    product_id = fields.Many2one(related="sale_team_target_id.product_id", string="Product for Invoicing")

    target = fields.Float(string="Target")
    sale_total = fields.Float(string="Sales Total", compute="_compute_sale_total")
    incentive_amount = fields.Float(string="Incentive Amount", compute="_compute_incentive_amount")

    bu_br_incentive_amount = fields.Float(string="Pooling BU/BR Incentive Amount", compute="_compute_incentive_amount")

    target_reached = fields.Float(string="Target Reached", compute="_compute_target_reached")
    # state = fields.Selection([
    #     ('draft', 'Draft'),
    #     ('boh','Approved BOH'),
    #     ('request_incentive_approved', 'Request Incentive Approved'),
    #     ('incentive_approved', 'Incentive Approved'),
    #     ('reject', 'Rejected'),
    #     ('incentive_withdraw', 'Incentive Withdraw'),
    #     ('pooling_withdraw', 'Pooling Withdraw'),
    #     ('close', 'Close'),
    #     ('incentive_partially_withdraw', 'Incentive Partially Withdraw'),
    # ], string="Status", readonly=True, default="draft", tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('boh','Approved BOH'),
        ('reject', 'Rejected'),
        ('incentive_withdraw', 'Incentive Withdraw'),
        ('pooling_withdraw', 'Pooling Withdraw'),
        ('close', 'Close'),
        ('incentive_partially_withdraw', 'Incentive Partially Withdraw'),
    ], string="Status", readonly=True, default="draft", tracking=True)

    approval_person = fields.Many2one('res.partner', string="Approval Person")

    currency_id = fields.Many2one(related="sale_team_target_id.currency_id", string="Currency")

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    business_id = fields.Many2one('business.unit', 'Business Unit', related='sale_team_target_id.business_id')
    payment_rule = fields.Selection(related='sale_team_target_id.payment_rule', string="Payment Rules",
                                    default="invoice", required=True)
    paid_amount = fields.Float()
    due_amount = fields.Float(compute='get_due')

    bu_br_user_approve = fields.Boolean(compute='compute_br_user_approve')
    
    def compute_br_user_approve(self):
        for rec in self:
            if rec.sale_team_id.branch_id.id == self.env.user.current_bu_br_id.id and self.env.user.user_type_id == 'bu':
                rec.bu_br_user_approve = True

            if rec.sale_team_id.branch_id.id == self.env.user.current_bu_br_id.id and self.env.user.user_type_id == 'br':
                rec.bu_br_user_approve = True
            else:
                rec.bu_br_user_approve = False

    def action_boh(self):
        self.state = 'boh'
    def get_due(self):
        for rec in self:
            rec.due_amount = rec.incentive_amount - rec.paid_amount

    def target_close(self):
        return self.write({'state': 'close'})

    def create_br_entry(self):
        br = []
        incentive_amount = self.currency_id._convert(self.incentive_amount,
                                                     self.env.user.company_id.currency_id,
                                                     self.env.user.company_id,
                                                     datetime.today(),
                                                     )
        move_line = {'name': self.name,
                     'partner_id': self.business_id.partner_id.id,
                     'account_id': self.branch_id.incentive_account_id.id,
                     'business_id': self.branch_id.id,
                     'date': datetime.today(),
                     'amount_currency': -self.incentive_amount,
                     'credit': incentive_amount,
                     'currency_id': self.currency_id.id,
                     'personal_target_id': self.id, }
        br.append(move_line)
        bu_br_incentive_amount = self.currency_id._convert(self.bu_br_incentive_amount,
                                                           self.env.user.company_id.currency_id,
                                                           self.env.user.company_id,
                                                           datetime.today(),
                                                           )
        move_line = {'name': self.name,
                     'partner_id': self.business_id.partner_id.id,
                     'account_id': self.branch_id.pooling_account_id.id,
                     'business_id': self.branch_id.id,
                     'date': datetime.today(),
                     'amount_currency': -self.bu_br_incentive_amount,
                     'credit': bu_br_incentive_amount,
                     'currency_id': self.currency_id.id,
                     'personal_target_id': self.id, }
        br.append(move_line)
        # Aff
        # amount = self.currency_id._convert(self.incentive_amount + self.bu_br_incentive_amount,
        #                                     self.env.user.company_id.currency_id,
        #                                     self.env.user.company_id,
        #                                     datetime.today(),
        #                                 )
        amount = incentive_amount + bu_br_incentive_amount
        move_line = {'name': self.name,
                     'partner_id': self.business_id.partner_id.id,
                     'account_id': self.branch_id.aff_account_receivable_id.id,
                     'business_id': self.branch_id.id,
                     'date': datetime.today(),
                     'amount_currency': self.incentive_amount + self.bu_br_incentive_amount,
                     'debit': amount,
                     'currency_id': self.currency_id.id,
                     'personal_target_id': self.id, }
        br.append(move_line)
        line_ids = [(0, 0, l) for l in br]
        move_vals = {
            'journal_id': self.journal_id.id,
            'ref': self.name,
            'date': datetime.today(),
            'line_ids': line_ids,
        }
        self.env['account.move'].create(move_vals).action_post()
        return True

    def create_bu_entry(self):
        bu = []
        incentive_amount = self.currency_id._convert(self.incentive_amount,
                                                     self.env.user.company_id.currency_id,
                                                     self.env.user.company_id,
                                                     datetime.today(),
                                                     )
        move_line = {'name': self.name,
                     'partner_id': self.branch_id.partner_id.id,
                     'account_id': self.account_id.id,
                     'business_id': self.business_id.id,
                     'date': datetime.today(),
                     'amount_currency': self.incentive_amount,
                     'debit': incentive_amount,
                     'currency_id': self.currency_id.id,
                     'personal_target_id': self.id, }
        bu.append(move_line)
        bu_br_incentive_amount = self.currency_id._convert(self.bu_br_incentive_amount,
                                                           self.env.user.company_id.currency_id,
                                                           self.env.user.company_id,
                                                           datetime.today(),
                                                           )
        move_line = {'name': self.name,
                     'partner_id': self.branch_id.partner_id.id,
                     'account_id': self.pooling_account_id.id,
                     'business_id': self.business_id.id,
                     'date': datetime.today(),
                     'amount_currency': self.bu_br_incentive_amount,
                     'debit': bu_br_incentive_amount,
                     'currency_id': self.currency_id.id,
                     'personal_target_id': self.id, }
        bu.append(move_line)
        # Aff
        # amount = self.currency_id._convert(self.incentive_amount + self.bu_br_incentive_amount,
        #                                     self.env.user.company_id.currency_id,
        #                                     self.env.user.company_id,
        #                                     datetime.today(),
        #                                 )
        amount = incentive_amount + bu_br_incentive_amount
        move_line = {'name': self.name,
                     'partner_id': self.branch_id.partner_id.id,
                     'account_id': self.business_id.aff_account_payable_id.id,
                     'business_id': self.business_id.id,
                     'date': datetime.today(),
                     'amount_currency': -(self.incentive_amount + self.bu_br_incentive_amount),
                     'credit': amount,
                     'currency_id': self.currency_id.id,
                     'personal_target_id': self.id, }
        bu.append(move_line)
        line_ids = [(0, 0, l) for l in bu]
        move_vals = {
            'journal_id': self.journal_id.id,
            'ref': self.name,
            'date': datetime.today(),
            'line_ids': line_ids,
        }
        self.env['account.move'].create(move_vals).action_post()
        return True

    def incentive_approved(self):
        br = self.create_br_entry()
        bu = self.create_bu_entry()
        return self.write({'state': 'incentive_approved'})

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('personal.sale.target', sequence_date=None) or _('New')

        result = super(PersonalSaleTarget, self).create(vals)
        return result

    @api.onchange('sale_team_target_id')
    def _onchange_sale_team_target(self):
        for line in self:
            try:
                if line.sale_team_target_id.branch_id:
                    line.branch_id = line.sale_team_target_id.branch_id.id
                if line.sale_team_target_id.sale_team_id:
                    line.sale_team_id = line.sale_team_target_id.sale_team_id.id
            except Exception:
                raise UserError(_('Please choose sale team target first!'))

    @api.depends('sale_team_target_id')
    def _compute_sale_order_ids(self):
        for line in self:
            orders = []
            for order in line.sale_team_target_id.sale_order_ids:
                if line.sale_person_id.id == order.user_id.id:
                    orders.append(order.id)

            line.sale_order_ids = orders

    @api.depends('sale_order_ids')
    def _get_invoice_ids(self):
        for line in self:
            invoices = []
            for order in line.sale_order_ids:
                logging.info(order.invoice_ids)
                if order.invoice_ids:
                    for temp in order.invoice_ids.ids:
                        invoices.append(temp)
            line.invoice_ids = invoices

    @api.depends('sale_order_ids')
    def _get_sale_order(self):
        for line in self:
            line.sale_order_count = len(line.sale_order_ids)

    @api.depends('invoice_ids')
    def _get_invoice_count(self):
        for line in self:
            line.invoice_count = len(line.invoice_ids)

    @api.depends('incentive_invoice_ids')
    def _get_incentive_invoice_count(self):
        for line in self:
            line.incentive_invoice_count = len(line.incentive_invoice_ids)

    def action_view_sale_order(self):

        action = self.env.ref('sale_incentive.sale_target_sale_order').read()[0]
        sale_order_ids = self.mapped('sale_order_ids')

        if len(sale_order_ids) > 1:
            action['domain'] = [('id', 'in', sale_order_ids.ids)]
        elif len(sale_order_ids) == 1:
            action['domain'] = [('id', 'in', sale_order_ids.ids)]

        else:
            action = {'type': 'ir.actions.act_window_close'}

        return action

    def action_view_invoice(self):

        invoices = self.mapped('invoice_ids')
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]

        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]

        elif len(invoices) == 1:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = invoices.id

        else:
            action = {'type': 'ir.actions.act_window_close'}

        context = {
            'default_type': 'out_invoice'
        }

        action['context'] = context
        return action

    def action_view_incentive_invoice(self):
        invoices = self.mapped('incentive_invoice_ids')
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]

        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]

        elif len(invoices) == 1:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = invoices.id

        else:
            action = {'type': 'ir.actions.act_window_close'}

        context = {
            'default_type': 'out_invoice'
        }

        action['context'] = context
        return action

    @api.depends('sale_order_ids')
    def _compute_sale_total(self):
        for line in self:
            total = 0.0
            # for order in line.sale_order_ids:
            for order in line.invoice_ids:
                logging.info(order.invoice_user_id.name)
                if order.invoice_user_id.id == line.sale_person_id.id:
                    if line.start_date and line.end_date:
                        if order.invoice_date or datetime.today().date() >= line.start_date and order.invoice_date or datetime.today().date() <= line.end_date:
                            total += order.amount_total_signed
            line.sale_total = total

    @api.depends('target', 'sale_total')
    def _compute_target_reached(self):
        for line in self:
            target_reached = 0.0
            if line.sale_total > 0.0 and line.target > 0.0:
                target_reached = 100 * (line.sale_total / line.target)

            line.target_reached = target_reached

    @api.depends('target_reached', 'sale_total')
    def _compute_incentive_amount(self):
        for line in self:

            if line.sale_total == 0:
                line.incentive_amount = 0.0
                line.bu_br_incentive_amount = 0.0
                continue

            amount = 0.0
            sale_person_incentive_percent = line.incentive_rule_id.sale_person_incentive_percentage
            bu_br_incentive_percent = line.incentive_rule_id.pooling_incentive_percentage
            define_incentive_amount = 0.0
            target_reached = line.target_reached
            if line.incentive_rule_id.incentive_calculation == 'agent':
                for record in line.incentive_rule_id.incentive_performance_range_ids:
                    if not line.incentive_rule_id.different_with_sale_target:
                        if record.conditional_operator == '>=':
                            if target_reached >= record.higher_range:
                                define_incentive_amount = record.incentive_amount
                        elif record.conditional_operator == '>':
                            if target_reached > record.higher_range:
                                define_incentive_amount = record.incentive_amount

                        elif record.conditional_operator == 'between':
                            if target_reached >= record.lower_range and target_reached < record.higher_range:
                                define_incentive_amount = record.incentive_amount

                        elif record.conditional_operator == '<=':
                            if target_reached <= record.lower_range:
                                define_incentive_amount = record.incentive_amount
                        elif record.conditional_operator == '<':
                            if target_reached < record.lower_range:
                                define_incentive_amount = record.incentive_amount
            else:
                for record in line.incentive_rule_id.incentive_performance_range_ids:
                    if not line.incentive_rule_id.different_with_sale_target:
                        if record.conditional_operator == '>=':
                            if target_reached >= record.higher_range:
                                define_incentive_amount = line.sale_total * (
                                        record.incentive_percentage / 100) + line.target * (
                                                                  record.outstanding / 100)
                        elif record.conditional_operator == '>':
                            if target_reached > record.higher_range:
                                define_incentive_amount = line.sale_total * (
                                        record.incentive_percentage / 100) + line.target * (
                                                                  record.outstanding / 100)

                        elif record.conditional_operator == 'between':
                            if target_reached >= record.lower_range and target_reached < record.higher_range:
                                define_incentive_amount = line.sale_total * (
                                        record.incentive_percentage / 100) + line.target * (
                                                                  record.outstanding / 100)

                        elif record.conditional_operator == '<=':
                            if target_reached <= record.lower_range:
                                define_incentive_amount = line.sale_total * (
                                        record.incentive_percentage / 100) + line.target * (
                                                                  record.outstanding / 100)
                        elif record.conditional_operator == '<':
                            if target_reached < record.lower_range:
                                define_incentive_amount = line.sale_total * (
                                        record.incentive_percentage / 100) + line.target * (
                                                                  record.outstanding / 100)
                        else:
                            define_incentive_amount = 0.0

            amount = define_incentive_amount * (sale_person_incentive_percent / 100)

            pooling_amount = define_incentive_amount * (bu_br_incentive_percent / 100)
            line.incentive_amount = amount
            line.bu_br_incentive_amount = pooling_amount

    @api.depends('sale_team_id')
    def _compute_user_team(self):
        for line in self:
            teams = []

            for member in line.sale_team_id.member_ids:
                teams.append(member.id)

            if line.sale_team_id.user_id:
                teams.append(line.sale_team_id.user_id.id)
            line.user_team_ids = teams


class SaleSettlement(models.Model):
    _name = 'branch.incentive.settlement'
