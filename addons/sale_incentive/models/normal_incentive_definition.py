from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError, ValidationError
from datetime import datetime
import logging


class NormalIncentiveDefinition(models.Model):
    _name = 'normal.incentive.definition'
    _description = 'Normal Incentive Definition'

    def _default_currency(self):
        return self.env.user.company_id.currency_id.id

    name = fields.Char(string="Name", required=True)

    is_active = fields.Boolean(string="Active", default=True)
    is_b2b = fields.Boolean(string="Is for Retail Customer (B2B)", default=False)
    is_gov_tender = fields.Boolean(string="Is for Goverment Tender Sales", default=False)

    calculation_type = fields.Selection([
        ('fixed_amount', 'Fixed Amount'),
        ('fixed_percent', 'Fixed Percentage'),
        ('fixed_percent_multi_agent', 'Fixed Percentage Division to Multi Agent'),
        ('fixed_amount_multi_agent', 'Fixed Amount Division to Multi Agent'),
        ('by_section_fixed_amount', 'By Sections Fixed Amount Division to Multi Agent'),
    ], string="Calculation Type", default="fixed_amount", required=True)

    payment_rule = fields.Selection([
        ('invoice', 'Invoice Based'),
        ('payment', 'Payment Based'),
        ('both', '50% Invoice Based and 50% Payment Based'),
    ], string="Payment Rules", default="invoice", required=True)

    branch_ids = fields.Many2many('business.unit', string="BU/BR Names", domain="[('business_type','=','br')]")

    rates_definition = fields.Selection([
        ('category', 'By Product Category'),
        ('product', 'By Product'),
        ('sale_order_type', 'By Units or Parts'),
    ], string="Rates Definition", required=True)

    currency_id = fields.Many2one('res.currency', required=True, default=_default_currency,
                                  string="Incentive Invoice Paid Currency")

    salesperson_used = fields.Boolean(string="Used", default=False)
    salesperson_settlement_period = fields.Selection([
        ('monthly', 'Montly'),
        ('quaterly', 'Quaterly'),
        ('annually', 'Annually'),
        ('user_defined', 'User Defined'),
    ], string="Settlement Period")

    sale_person_annually_date = fields.Date(string="Annual Date")
    sale_person_user_defined_date = fields.Date(string="User Defined Date")

    sale_person_quaterly_start_date = fields.Date(string="Quaterly Start Date")

    sale_person_quaterly_end_date = fields.Date(string="Quaterly End Date")

    sale_person_quaterly_time = fields.Selection([
        ('3', '3'),
        ('4', '4')
    ], string="Quaterly Time", default="3")

    sale_person_monthly_start_day = fields.Integer(string="From")
    sale_person_monthly_end_day = fields.Integer(string="To")

    bu_br_used = fields.Boolean(string="Used", default=False)
    bu_br_settlement_period = fields.Selection([
        ('monthly', 'Montly'),
        ('quaterly', 'Quaterly'),
        ('annually', 'Annually'),
        ('user_defined', 'User Defined'),
    ], string="Settlement Period")

    bu_br_quaterly_start_date = fields.Date(string="Quaterly Start Date")

    bu_br_quaterly_end_date = fields.Date(string="Quaterly End Date")

    bu_br_quaterly_time = fields.Selection([
        ('3', '3'),
        ('4', '4')
    ], string="Quaterly Time", default="3")

    bu_br_monthly_start_day = fields.Integer(string="From")
    bu_br_monthly_end_day = fields.Integer(string="To")

    bu_br_annually_date = fields.Date(string="Annual Date")
    bu_br_user_defined_date = fields.Date(string="User Defined Date")

    retain_for_salesperson_used = fields.Boolean(string="Used", default=False)
    retain_settlement_period = fields.Selection([
        ('monthly', 'Montly'),
        ('quaterly', 'Quaterly'),
        ('annually', 'Annually'),
        ('user_defined', 'User Defined'),
    ], string="Settlement Period")

    retain_quaterly_start_date = fields.Date(string="Quaterly Start Date")

    retain_quaterly_end_date = fields.Date(string="Quaterly End Date")

    retain_quaterly_time = fields.Selection([
        ('3', '3'),
        ('4', '4')
    ], string="Quaterly Time", default="3")

    retain_monthly_start_day = fields.Integer(string="From")
    retain_monthly_end_day = fields.Integer(string="To")

    retain_annually_date = fields.Date(string="Annual Date")
    retain_user_defined_date = fields.Date(string="User Defined Date")

    area_sale_manager_used = fields.Boolean(string="Used", default=False)
    area_sale_manager_settlement_period = fields.Selection([
        ('monthly', 'Montly'),
        ('quaterly', 'Quaterly'),
        ('annually', 'Annually'),
        ('user_defined', 'User Defined'),
    ], string="Settlement Period")

    area_sale_manager_quaterly_start_date = fields.Date(string="Quaterly Start Date")

    area_sale_manager_quaterly_end_date = fields.Date(string="Quaterly End Date")

    area_sale_manager_quaterly_time = fields.Selection([
        ('3', '3'),
        ('4', '4')
    ], string="Quaterly Time", default="3")

    area_sale_manager_monthly_start_day = fields.Integer(string="From")
    area_sale_manager_monthly_end_day = fields.Integer(string="To")

    area_sale_manager_annually_date = fields.Date(string="Annual Date")
    area_sale_manager_user_defined_date = fields.Date(string="User Defined Date")

    incentive_rule_ids = fields.One2many('normal.incentive.rules', 'incentive_definition_id', string="Incentive Rules")

    user_id = fields.Many2one('res.users', string="User", default=lambda self: self.env.user)

    journal_id = fields.Many2one('account.journal', string="Incentive Journal", required=True)

    account_id = fields.Many2one('account.account', string="Incentive Account", required=True,
                                 domain="[('bu_br_id','=',business_id)]")

    product_id = fields.Many2one('product.product', string="Product for Invoicing", required=True)
    business_id = fields.Many2one('business.unit', string="Business Unit", required=True,
                                  default=lambda self: self.env.user.current_bu_br_id.id)
    government_salesperson_used = fields.Boolean('Used')
    government_pooling_used = fields.Boolean('Used')
    sale = fields.Selection([('product', 'Normal Sale'), ('service', 'Service Sale')], string='Units or Parts',
                            default='product')
    pooling_account_id = fields.Many2one('account.account', 'Account Pooling', domain="[('bu_br_id','=',business_id)]")
    retain_account_id = fields.Many2one('account.account', 'Retain Account', domain="[('bu_br_id','=',business_id)]")
    asm_account_id = fields.Many2one('account.account', 'ASM Account', domain="[('bu_br_id','=',business_id)]")
    state = fields.Selection([
        ('draft', 'New'),
        ('finance_head','Approved F&A Head')], string='Status', readonly=True, default='draft')

    bu_user_approve = fields.Boolean(string="BU User Approve",compute='compute_bu_user_approve')

    def action_draft(self):
        self.state = 'draft'
        
    def compute_bu_user_approve(self):
        if self.business_id.id == self.env.user.current_bu_br_id.id and self.env.user.user_type_id == 'bu':
            self.bu_user_approve = True
        else:
            self.bu_user_approve = False

    def action_finance_head(self):
        self.state = 'finance_head'

    @api.onchange('business_id')
    def _onchange_hr_bu(self):
        self.incentive_rule_ids = False
        return {'domain': {'business_id': [('id', 'in', [bu.id for bu in self.env.user.hr_bu_ids])]}}

    # updated NHS
    @api.constrains('sale', 'business_id')
    def contrain_incentive(self):
        record = self.env['normal.incentive.definition'].search(
            [('is_active', '=', True), ('sale', '=', self.sale), ('business_id', '=', self.business_id.id),
             ('is_gov_tender', '=', False)])
        if len(record) > 1:
            raise UserError(_('Duplication Error.'))
        gov_record = record = self.env['normal.incentive.definition'].search(
            [('is_active', '=', True), ('sale', '=', self.sale), ('business_id', '=', self.business_id.id),
             ('is_gov_tender', '=', True)])
        if len(gov_record) > 1:
            raise UserError(_('Government Tender Duplication Error.'))

    @api.onchange('calculation_type')
    def _onchange_calculation_type(self):
        for rec in self:
            rec.incentive_rule_ids = False

    @api.onchange('is_gov_tender')
    def _onchange_gov_tender(self):
        for rec in self:
            rec.government_salesperson_used = False
            rec.government_pooling_used = False

    @api.onchange('rates_definition')
    def _onchange_rates_definition(self):
        for line in self:
            if line.rates_definition == 'category':
                category_ids = []
                categories = self.env['product.category'].search([('business_id', '=', line.business_id.id)])
                for cc in categories:
                    category_ids.append(cc)

                create_category = [(6, 0, [])]

                for c in category_ids:
                    create_category.append((0, 0, {
                        'product_categ_id': c.id,
                    }))

                line.incentive_rule_ids = create_category

            elif line.rates_definition == 'product':
                product_ids = [(6, 0, [])]

                category_ids = []
                categories = self.env['product.category'].search([('business_id', '=', line.business_id.id)])
                for cc in categories:
                    category_ids.append(cc)

                for category in category_ids:
                    products = self.env['product.product'].search([('categ_id', '=', category.id)])
                    for p in products:
                        product_ids.append((0, 0, {
                            'product_id': p.id
                        }))
                line.incentive_rule_ids = product_ids
            elif line.rates_definition == 'sale_order_type':
                line.incentive_rule_ids = [(6, 0, [])]
                lists = [(0, 0, {
                    'unit_or_part': 'unit'
                }), (0, 0, {
                    'unit_or_part': 'part'
                })]
                line.incentive_rule_ids = lists


    def _check_product_fixed_amount_agent_base(self,line):
        for rule in self.incentive_rule_ids:                           
            if rule.product_id.id == line.product_id.id:
                if self.payment_rule == 'both':
                    temp = (rule.incentive_fixed_rate)/2
                    return temp,rule.salesperson_incentive_rate,rule.bu_br_rate,rule.retain_rate,rule.gov_salesperson_percentage,rule.gov_pooling_percentage
                else:
                    temp = rule.incentive_fixed_rate
                    return temp,rule.salesperson_incentive_rate,rule.bu_br_rate,rule.retain_rate,rule.gov_salesperson_percentage,rule.gov_pooling_percentage

    def _check_product_base(self,line):
        for rule in self.incentive_rule_ids:                           
            if rule.product_id.id == line.product_id.id:
                if self.payment_rule == 'both':
                    temp = ((line.quantity * line.price_unit) * (rule.incentive_percentage/100))/2
                    return temp,rule.salesperson_incentive_rate,rule.bu_br_rate,rule.retain_rate,rule.gov_salesperson_percentage,rule.gov_pooling_percentage
                else:
                    temp = ((line.quantity * line.price_unit) * (rule.incentive_percentage/100))
                    return temp,rule.salesperson_incentive_rate,rule.bu_br_rate,rule.retain_rate,rule.gov_salesperson_percentage,rule.gov_pooling_percentage



                    # Category

    def _check_product_categ_amount_agent_base(self,line):
        for rule in self.incentive_rule_ids:
            cate_id = line.product_id.categ_id
            categ_child = self.env['product.category'].search([('id','child_of',rule.product_categ_id.ids)])
            if rule.product_categ_id.id == cate_id.id | cate_id.id in categ_child.ids:
                if self.payment_rule == 'both':
                    temp = (rule.incentive_fixed_rate)/2
                    
                    return temp,rule.salesperson_incentive_rate,rule.bu_br_rate,rule.retain_rate,rule.gov_salesperson_percentage,rule.gov_pooling_percentage
                else:
                    temp = (rule.incentive_fixed_rate)
                    return temp,rule.salesperson_incentive_rate,rule.bu_br_rate,rule.retain_rate,rule.gov_salesperson_percentage,rule.gov_pooling_percentage

    def _check_product_categ_base(self,line):
        for rule in self.incentive_rule_ids:
            cate_id = line.product_id.categ_id
            line_amount = line.quantity * line.price_unit
            categ_child = self.env['product.category'].search([('id','child_of',rule.product_categ_id.ids)])
            if rule.product_categ_id.id == cate_id.id | cate_id.id in categ_child.ids:
                if self.payment_rule == 'both':
                    temp = (line_amount * (rule.incentive_percentage/100))/2
                    return line_amount,temp,rule.salesperson_incentive_rate,rule.bu_br_rate,rule.retain_rate,rule.gov_salesperson_percentage,rule.gov_pooling_percentage,rule.sales_manager_rate
                else:
                    temp = (line_amount * (rule.incentive_percentage/100))
                    return line_amount,temp,rule.salesperson_incentive_rate,rule.bu_br_rate,rule.retain_rate,rule.gov_salesperson_percentage,rule.gov_pooling_percentage,rule.sales_manager_rate

class NormalIncentiveRules(models.Model):
    _name = 'normal.incentive.rules'
    _description = 'Normal Incentive Rules'

    incentive_definition_id = fields.Many2one('normal.incentive.definition', string="Incentive Definition",
                                              required=True, ondelete="cascade")
    branch_ids = fields.Many2many('business.unit', string="Branch Name", domain="[('business_type','=','br')]")

    product_id = fields.Many2one('product.product', string="Product Name",
                                 domain="[('business_id','=',parent.business_id)]")
    product_categ_id = fields.Many2one('product.category', string="Product Category",
                                       domain="[('business_id','=',parent.business_id)]")

    incentive_fixed_rate = fields.Float(string="Incentive Fixed Rate")
    incentive_percentage = fields.Float(string="Incentive (%)")
    salesperson_incentive_rate = fields.Float(string="Salesperson Rate")
    bu_br_rate = fields.Float(string="Pooling BU/BR Rate")
    retain_rate = fields.Float(string="Retain for Salesperson Rate")
    sales_manager_rate = fields.Float(string="Areas Sales Manager")
    gov_salesperson_percentage = fields.Float('GOV Salesperson (%)')
    gov_pooling_percentage = fields.Float('GOV Pooling (%)')
    lower_range = fields.Float(string="By Section Amount(lower)")
    upper_range = fields.Float(string="By Section Amount(upper)")
    by_section_operator = fields.Selection([
        ('>=', '>='),
        ('>', '>'),
        ('<=', '<='),
        ('<', '<'),
        ('between', 'Between')
    ], string="Operator", default=">")
    unit_or_part = fields.Selection([('unit', 'Unit'), ('part', 'Spare Part')], string='Units or Parts')
    currency_id = fields.Many2one(related='incentive_definition_id.currency_id',
                                  depends=['incentive_definition_id.currency_id'], store=True,
                                  string='Currency')


class NormalIncentiveParent(models.Model):
    _name = 'normal.incentive.main'
    _description = 'Normal Incentive'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'


    # Deduct JE************************************

    def create_deduct_br_entry(self, incentive_id, accured_account_id, br):
        amount = self.currency_id._convert(incentive_id.deduct_amount,
                                           self.env.user.company_id.currency_id,
                                           self.env.user.company_id,
                                           datetime.today(),
                                           )
        move_line = {'name': incentive_id.name,
                     'partner_id': self.business_id.partner_id.id,
                     'account_id': accured_account_id.id,
                     'business_id': incentive_id.branch_id.id,
                     'date': datetime.today(),
                     'amount_currency': incentive_id.deduct_amount,
                     'debit': amount,
                     'currency_id': self.currency_id.id,
                     'incentive_id': self.id, }
        br.append(move_line)
        return br

    def create_deduct_bu_entry(self, incentive_id, bu):
        amount = self.currency_id._convert(incentive_id.deduct_amount,
                                           self.env.user.company_id.currency_id,
                                           self.env.user.company_id,
                                           datetime.today(),
                                           )
        move_line = {'name': incentive_id.name,
                     'partner_id': self.branch_id.partner_id.id,
                     'account_id': incentive_id.account_id.id,
                     'business_id': incentive_id.business_id.id,
                     'date': datetime.today(),
                     'amount_currency': - incentive_id.deduct_amount,
                     'credit': amount,
                     'currency_id': self.currency_id.id,
                     'incentive_id': self.id, }
        bu.append(move_line)
        return bu

    def create_deduct_entry(self, incentive_id, br, bu):
        if incentive_id.sale_person_type in ['sale_person', 'gov_salesperson', 'retain']:
            accured_account_id = incentive_id.branch_id.incentive_account_id
        if incentive_id.sale_person_type in ['bu_br', 'gov_pooling']:
            accured_account_id = incentive_id.branch_id.pooling_account_id
        br = self.create_deduct_br_entry(incentive_id, accured_account_id, br)
        bu = self.create_deduct_bu_entry(incentive_id, bu)
        return bu, br
    def reverse_deduct_incentive(self):
        bu = []
        br = []
        amount = 0.0
        line_total_amount =0.0
        amount_currency =0.0
        if self.branch_id and not self.manager:
            for items in self.line_ids:
                amount = self.currency_id._convert(items.deduct_amount,
                                               self.env.user.company_id.currency_id,
                                               self.env.user.company_id,
                                               datetime.today(),
                                               )
                # amount += items.deduct_amount
                line_total_amount +=amount
                print('///////',line_total_amount)
                
                bu, br = self.create_deduct_entry(items, br, bu)
                # items.state = 'incentive_approved'
           

                amount_currency += items.deduct_amount
            print('///////',line_total_amount)
            print('amount in currency xxxx',amount_currency)
            # amount = self.currency_id._convert(amount,
            #                                    self.env.user.company_id.currency_id,
            #                                    self.env.user.company_id,
            #                                    datetime.today(),
            #                                    )

            # Br
            move_line = {'name': self.name,
                         'partner_id': self.business_id.partner_id.id,
                         'account_id': self.branch_id.aff_account_receivable_id.id,
                         'business_id': self.branch_id.id,
                         'date': datetime.today(),
                         'amount_currency':- amount_currency,
                         'credit': line_total_amount,
                         'currency_id': self.currency_id.id,
                         'incentive_id': self.id, }
            br.append(move_line)
            line_ids = [(0, 0, l) for l in br]
            br_move_vals = {
                'journal_id': self.incentive_definition_id.journal_id.id,
                'ref': self.name,
                'date': datetime.today(),
                'line_ids': line_ids,
                'hr_br_id':self.branch_id.id,
                'hr_bu_id':self.business_id.id,
            }
            print('br move vals',br_move_vals)
            self.env['account.move'].create(br_move_vals).action_post()

            # BU
            move_line = {'name': self.name,
                         'partner_id': self.branch_id.partner_id.id,
                         'account_id': self.business_id.aff_account_payable_id.id,
                         'business_id': self.business_id.id,
                         'date': datetime.today(),
                         'amount_currency': amount_currency,
                         'debit': line_total_amount,
                         'currency_id': self.currency_id.id,
                         'incentive_id': self.id, }
            bu.append(move_line)
            line_ids = [(0, 0, l) for l in bu]
            bu_move_vals = {
                'journal_id': self.incentive_definition_id.journal_id.id,
                'ref': self.name,
                'date': datetime.today(),
                'line_ids': line_ids,
                'hr_br_id':self.branch_id.id,
                'hr_bu_id':self.business_id.id,
            }
            print('bu move vals',bu_move_vals)
            self.env['account.move'].create(bu_move_vals).action_post()
        else:
            bu_own = []
            for line in self.line_ids:
                if line.sale_person_type in ['sale_person', 'gov_salesperson','retain']:
                    accured_account_id = line.business_id.incentive_account_id
                if line.sale_person_type in ['bu_br', 'gov_pooling']:
                    accured_account_id = line.business_id.pooling_account_id
                if line.sale_person_type == 'sale_manager':
                    accured_account_id = line.business_id.asm_account_id
                self.prepare_deduct_bu_own_sale(line, accured_account_id, bu_own)
            line_ids = [(0, 0, l) for l in bu_own]
            own_vals = {
                'journal_id': self.incentive_definition_id.journal_id.id,
                'ref': self.name,
                'date': datetime.today(),
                'line_ids': line_ids,
                'hr_bu_id':self.business_id.id,
            }
            self.env['account.move'].create(own_vals).action_post()

        # Change Incentive Item Line State
        # for line in self.line_ids:
        #     line.state = 'incentive_approved'
        # self.write({'state': 'incentive_approved'})
    
    def prepare_deduct_bu_own_sale(self, incentive_id, accured_account_id, res):
        amount = self.currency_id._convert(incentive_id.deduct_amount,
                                           self.env.user.company_id.currency_id,
                                           self.env.user.company_id,
                                           datetime.today(),
                                           )

        move_line = {'name': incentive_id.name,
                     'partner_id': incentive_id.partner_id.id,
                     'account_id': incentive_id.account_id.id,
                     'business_id': incentive_id.business_id.id,
                     'date': datetime.today(),
                     'amount_currency': - incentive_id.deduct_amount,
                     'credit': amount,
                     'currency_id': self.currency_id.id,
                     'incentive_id': self.id, }
        res.append(move_line)
        print('credit........',move_line)
        move_line = {'name': incentive_id.name,
                     'partner_id': incentive_id.partner_id.id,
                     'account_id': accured_account_id.id,
                     'business_id': incentive_id.business_id.id,
                     'date': datetime.today(),
                     'amount_currency': incentive_id.deduct_amount,
                     'debit': amount,
                     'currency_id': self.currency_id.id,
                     'incentive_id': self.id, }
        res.append(move_line)
        print('debit........',move_line)
        return res

   
                
                #   //////////////////////////////////////////////////////////////////


    def unlink(self):
        for rec in self:
            if rec.state not in ['draft','incentive_approved']:
                raise UserError(_('You cannot Delete this record'))
        return super(NormalIncentiveParent, self).unlink()

    def action_view_invoice(self):

        invoices = self.mapped('invoice_id')
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

    def action_view_sale_order(self):

        action = self.env.ref('sale_incentive.sale_target_sale_order').read()[0]
        sale_order_id = self.mapped('sale_order_id')
        print('sale order id', sale_order_id)

        if sale_order_id:
            action['domain'] = [('id', 'in', [sale_order_id.id])]

        else:
            action = {'type': 'ir.actions.act_window_close'}

        return action

    def action_move_items(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_account_moves_all_a") 
        domain = [('incentive_id', '=', self.id)]
        action['domain'] = [('incentive_id', '=', self.id)] if self.env.user.user_type_id == 'cfd' else [('incentive_id', '=', self.id),('account_id.bu_br_id', '=', self.env.user.current_bu_br_id.id)]
        print('DOMAIN ==>',action['domain'])
        return action

    name = fields.Char(string="Name", required=True, default=lambda self: _('New'), readonly=True, copy=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('incentive_approved', 'Incentive Posted'),
        ('request_incentive_approved', 'Request Incentive Approved'),
        ('boh_approved', 'BOH Approved'),
        ('saleadmin_approved','Sale Admin Approved'),
        ('salehead_approved','Sale Head Approved'),
        ('finance_account_approved', 'F & A Approved'),
        ('cca_dh_approved','CCA Dept. Approved'),
        ('cca_gm_approved','CCA GM Approved'),
        ('incentive_withdraw', 'Incentive Withdraw'),
        ('pooling_withdraw', 'Pooling Withdraw'),
        ('retain_withdraw', 'Retain Withdraw'),
        ('incentive_partially_withdraw','Incentive Partially Withdraw'),
        ('close', 'Close'),
        ('reject', 'Rejected'),
    ], string="Status", readonly=True, default="draft", tracking=True, required=True)

    sale_order_id = fields.Many2one('sale.order', string="Sale Order")
    invoice_id = fields.Many2one('account.move', string="Inv Number")
    sale_order_count = fields.Integer(string="Sale Order Count", compute="_get_order_count")

    invoice_count = fields.Integer(string="Invoice Count", compute="_get_invoice_count", readonly=True)
    invoice_ids = fields.Many2many("account.move", string="Invoices", compute="_get_invoice_ids", readonly=True)

    incentive_definition_id = fields.Many2one('normal.incentive.definition', string="Incentive Definition",
                                              required=True)

    user_id = fields.Many2one('res.users', string="User", required=True, default=lambda self: self.env.user)

    date = fields.Date(string="Incentive Created Date", default=fields.Date.today())

    approval_person = fields.Many2one('res.partner', string="Approval Person")

    branch_id = fields.Many2one('business.unit', string="Branch Name", required=False)

    currency_id = fields.Many2one('res.currency', readonly=True)
    incentive_invoice_count = fields.Integer(string="Incentive Bill Count", compute="_get_incentive_invoice_count",
                                             readonly=True)
    incentive_invoice_ids = fields.Many2many('account.move', string="Invoices", readonly=True)
    business_id = fields.Many2one('business.unit', string='Business Unit', required=False)
    move_id = fields.Many2one('account.move', 'Current Move')
    line_ids = fields.One2many('normal.incentive', 'parent_id', 'Normal Incentive')
    total = fields.Float('Total', compute='get_total')
    due_amount = fields.Float('Due Amount', compute='get_total')
    paid_amount = fields.Float('Paid Amount')
    manager = fields.Boolean('Manager')
    is_half_invoice_payment = fields.Boolean()
    incentive_request_id = fields.Many2one('incentive.request')
    ready_request_payment = fields.Boolean()
    invoice_amount = fields.Float()
    saleman_amount = fields.Float(compute='_compute_amount')
    pooling_amount = fields.Float(compute='_compute_amount')
    retain_amount = fields.Float(compute='_compute_amount')
    salemanager_amount = fields.Float(compute='_compute_amount')
    unit_or_part = fields.Selection([('unit', 'Unit'), ('part', 'Spare Part')], string='Units or Parts')

    @api.depends('line_ids')
    def _compute_amount(self):
        for rec in self:
            rec.saleman_amount =0.0
            rec.pooling_amount =0.0
            rec.retain_amount = 0.0
            rec.salemanager_amount =0.0
            for line in rec.line_ids:
                if line.sale_person_type in ['sale_person','gov_saleperson']:
                    rec.saleman_amount +=line.incentive_amount
                elif line.sale_person_type in ['bu_br','gov_pooling']:
                    rec.pooling_amount +=line.incentive_amount
                elif line.sale_person_type == 'retain':
                    rec.retain_amount +=line.incentive_amount
                elif line.sale_person_type == 'sale_manager':
                    rec.salemanager_amount +=line.incentive_amount
                else:
                    rec.saleman_amount =0.0
                    rec.pooling_amount =0.0
                    rec.retain_amount = 0.0
                    rec.salemanager_amount =0.0



    # @api.depends('incentive_definition_id')
    # def compute_request_payment(self):
    #     print('/xxxxxxxxxxxxxxxxxxxxxxxrequest payment')
    #     for rec in self:
    #         if rec.incentive_definition_id.payment_rule == 'invoice':
    #             if rec.invoice_id.state == 'posted':
    #                 rec.ready_request_payment = True
    #             else:
    #                 rec.ready_request_payment = False

    #         if rec.incentive_definition_id.payment_rule == 'payment':
    #             print('payment condiitonxxxxxxxxxxxxxxx')
    #             if rec.invoice_id.payment_state == 'paid':
    #                 rec.ready_request_payment = True
    #             else:
    #                 rec.ready_request_payment = False



    # def compute_half_inv_payment(self):
    #     for rec in self:
    #         for line in rec.line_ids.filtered(lambda x: x.sale_person_type in ['sale_person', 'gov_salesperson']):



    def get_total(self):
        for rec in self:
            for line in rec.line_ids:
                rec.total += line.incentive_amount
            rec.due_amount = rec.total - rec.paid_amount

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('normal.incentive.main', sequence_date=None) or _('New')
        result = super(NormalIncentiveParent, self).create(vals)
        return result

    def create_br_entry(self, incentive_id, accured_account_id, br):
        amount = self.currency_id._convert(incentive_id.incentive_amount,
                                           self.env.user.company_id.currency_id,
                                           self.env.user.company_id,
                                           datetime.today(),
                                           )
        move_line = {'name': incentive_id.name,
                     'partner_id': self.business_id.partner_id.id,
                     'account_id': accured_account_id.id,
                     'business_id': incentive_id.branch_id.id,
                     'date': datetime.today(),
                     'amount_currency': -incentive_id.incentive_amount,
                     'credit': amount,
                     'currency_id': self.currency_id.id,
                     'incentive_id': self.id, }
        br.append(move_line)
        return br

    def create_bu_entry(self, incentive_id, bu):
        amount = self.currency_id._convert(incentive_id.incentive_amount,
                                           self.env.user.company_id.currency_id,
                                           self.env.user.company_id,
                                           datetime.today(),
                                           )
        move_line = {'name': incentive_id.name,
                     'partner_id': self.branch_id.partner_id.id,
                     'account_id': incentive_id.account_id.id,
                     'business_id': incentive_id.business_id.id,
                     'date': datetime.today(),
                     'amount_currency': incentive_id.incentive_amount,
                     'debit': amount,
                     'currency_id': self.currency_id.id,
                     'incentive_id': self.id, }
        bu.append(move_line)
        return bu

    def create_entry(self, incentive_id, br, bu):
        if incentive_id.sale_person_type in ['sale_person', 'gov_salesperson', 'retain']:
            accured_account_id = incentive_id.branch_id.incentive_account_id
        if incentive_id.sale_person_type in ['bu_br', 'gov_pooling']:
            accured_account_id = incentive_id.branch_id.pooling_account_id
        br = self.create_br_entry(incentive_id, accured_account_id, br)
        bu = self.create_bu_entry(incentive_id, bu)
        return bu, br

    def incentive_approved(self):
        bu = []
        br = []
        amount = 0.0
        line_total_amount =0.0
        amount_currency =0.0
        if self.branch_id and not self.manager:
            for items in self.line_ids:
                amount = self.currency_id._convert(items.incentive_amount,
                                               self.env.user.company_id.currency_id,
                                               self.env.user.company_id,
                                               datetime.today(),
                                               )
                # amount += items.incentive_amount
                line_total_amount += amount
                print(amount,'xxxxxxxxxxxxxxxxx')
                bu, br = self.create_entry(items, br, bu)
                items.state = 'incentive_approved'

                amount_currency += items.incentive_amount
            # amount = self.currency_id._convert(amount,
            #                                    self.env.user.company_id.currency_id,
            #                                    self.env.user.company_id,
            #                                    datetime.today(),
            #                                    )

            # Br
            move_line = {'name': self.name,
                         'partner_id': self.business_id.partner_id.id,
                         'account_id': self.branch_id.aff_account_receivable_id.id,
                         'business_id': self.branch_id.id,
                         'date': datetime.today(),
                         'amount_currency': amount_currency,
                         'debit': line_total_amount,
                         'currency_id': self.currency_id.id,
                         'incentive_id': self.id, }
            br.append(move_line)
            line_ids = [(0, 0, l) for l in br]
            br_move_vals = {
                'journal_id': self.incentive_definition_id.journal_id.id,
                'ref': self.name,
                'date': datetime.today(),
                'line_ids': line_ids,
                'hr_br_id':self.branch_id.id,
            }
            print('br move vals',br_move_vals)
            self.env['account.move'].with_context(default_move_type='entry').create(br_move_vals).action_post()

            # BU
            move_line = {'name': self.name,
                         'partner_id': self.branch_id.partner_id.id,
                         'account_id': self.business_id.aff_account_payable_id.id,
                         'business_id': self.business_id.id,
                         'date': datetime.today(),
                         'amount_currency': -amount_currency,
                         'credit': line_total_amount,
                         'currency_id': self.currency_id.id,
                         'incentive_id': self.id, }
            bu.append(move_line)
            line_ids = [(0, 0, l) for l in bu]
            bu_move_vals = {
                'journal_id': self.incentive_definition_id.journal_id.id,
                'ref': self.name,
                'date': datetime.today(),
                'line_ids': line_ids,
                'hr_bu_id':self.business_id.id,
                'hr_br_id':self.branch_id.id,
            }
            print('bu move vals',bu_move_vals)
            self.env['account.move'].with_context(default_move_type='entry').create(bu_move_vals).action_post()
        else:
            bu_own = []
            for line in self.line_ids:
                if line.sale_person_type in ['sale_person', 'gov_salesperson','retain']:
                    accured_account_id = line.business_id.incentive_account_id
                if line.sale_person_type in ['bu_br', 'gov_pooling']:
                    accured_account_id = line.business_id.pooling_account_id
                if line.sale_person_type == 'sale_manager':
                    accured_account_id = line.business_id.asm_account_id
                self.prepare_bu_own_sale(line, accured_account_id, bu_own)
            line_ids = [(0, 0, l) for l in bu_own]
            own_vals = {
                'journal_id': self.incentive_definition_id.journal_id.id,
                'ref': self.name,
                'date': datetime.today(),
                'line_ids': line_ids,
                'hr_bu_id':self.business_id.id,
            }
            self.env['account.move'].with_context(default_move_type='entry').create(own_vals).action_post()

        # Change Incentive Item Line State
        for line in self.line_ids:
            line.state = 'incentive_approved'
        self.write({'state': 'incentive_approved'})


        # return self.write({'state': 'incentive_approved'})

    def prepare_bu_own_sale(self, incentive_id, accured_account_id, res):
        amount = self.currency_id._convert(incentive_id.incentive_amount,
                                           self.env.user.company_id.currency_id,
                                           self.env.user.company_id,
                                           datetime.today(),
                                           )

        move_line = {'name': incentive_id.name,
                     'partner_id': incentive_id.partner_id.id,
                     'account_id': incentive_id.account_id.id,
                     'business_id': incentive_id.business_id.id,
                     'date': datetime.today(),
                     'amount_currency': incentive_id.incentive_amount,
                     'debit': amount,
                     'currency_id': self.currency_id.id,
                     'incentive_id': self.id, }
        res.append(move_line)
        move_line = {'name': incentive_id.name,
                     'partner_id': incentive_id.partner_id.id,
                     'account_id': accured_account_id.id,
                     'business_id': incentive_id.business_id.id,
                     'date': datetime.today(),
                     'amount_currency': -incentive_id.incentive_amount,
                     'credit': amount,
                     'currency_id': self.currency_id.id,
                     'incentive_id': self.id, }
        res.append(move_line)
        return res

    @api.depends('incentive_invoice_ids')
    def _get_incentive_invoice_count(self):
        for line in self:
            line.incentive_invoice_count = len(line.incentive_invoice_ids)

    @api.depends('sale_order_id')
    def _get_invoice_ids(self):
        for line in self:
            invoices = []
            order = line.sale_order_id
            logging.info(order.invoice_ids)
            if order.invoice_ids:
                for temp in order.invoice_ids.ids:
                    invoices.append(temp)
            line.invoice_ids = invoices

    @api.depends('invoice_id')
    def _get_invoice_count(self):
        for line in self:
            line.invoice_count = len(line.invoice_id)

    @api.depends('sale_order_id')
    def _get_order_count(self):
        for rec in self:
            rec.sale_order_count = len(rec.sale_order_id)

    def action_close(self):
        self.state = 'close'
        for line in self.line_ids:
            line.state = 'close'


class NormalIncentive(models.Model):
    _name = 'normal.incentive'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Normal Incentive'
    _order = 'date desc'

    name = fields.Char(string="Name", required=True, default=lambda self: _('New'), readonly=True)

    partner_id = fields.Many2one('res.partner', string="Salesperson", required=False)
    parent_id = fields.Many2one('normal.incentive.main', 'Parent Incentive')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('incentive_approved', 'Incentive Posted'),
        ('request_incentive_approved', 'Request Incentive Approved'),
        ('boh_approved', 'BOH Approved'),
        ('finance_account_approved', 'F & A Approved'),
        ('cca_dh_approved','CCA Dept. Approved'),
        ('cca_gm_approved','CCA GM Approved'),
        ('incentive_withdraw', 'Incentive Withdraw'),
        ('pooling_withdraw', 'Pooling Withdraw'),
        ('retain_withdraw', 'Retain Withdraw'),
        ('close', 'Close'),
        ('reject', 'Rejected'),
    ], string="Status", readonly=True, default="draft", tracking=True, required=True,related="parent_id.state")

    sale_order_id = fields.Many2one('sale.order', string="Sale Order")
    sale_order_count = fields.Integer(string="Sale Order Count", compute="_get_order_count")
    invoice_id =  fields.Many2one('account.move')

    invoice_count = fields.Integer(string="Invoice Count", compute="_get_invoice_count", readonly=True)
    invoice_ids = fields.Many2many("account.move", string="Invoices", compute="_get_invoice_ids", readonly=True)

    incentive_definition_id = fields.Many2one('normal.incentive.definition', string="Incentive Definition",
                                              required=True)

    journal_id = fields.Many2one(related="incentive_definition_id.journal_id", string="Incentive Journal")

    account_id = fields.Many2one('account.account', string="Incentive Account")

    product_id = fields.Many2one(related="incentive_definition_id.product_id", string="Product for Invoicing")

    incentive_amount = fields.Float(string="Incentive Amount")

    sale_person_type = fields.Selection([
        ('sale_person', 'Salesperson'),
        ('bu_br', "Pooling BU/BR"),
        ('retain', 'Retain For Salesperson'),
        ('sale_manager', 'Area Sale Manager'),
        ('gov_salesperson', ' Gov Salesperson'),
        ('gov_pooling', 'Gov Pooling')
    ], string="Type", required=True)

    user_id = fields.Many2one('res.users', string="User", required=True, default=lambda self: self.env.user)

    date = fields.Date(string="Incentive Created Date", default=fields.Date.today())

    approval_person = fields.Many2one('res.partner', string="Approval Person")

    branch_id = fields.Many2one('business.unit', string="Branch Name", required=False,
                                domain="[('business_type','=','br')]")

    currency_id = fields.Many2one('res.currency', readonly=True)

    incentive_invoice_count = fields.Integer(string="Incentive Bill Count", compute="_get_incentive_invoice_count",
                                             readonly=True)
    incentive_invoice_ids = fields.Many2many('account.move', string="Invoices", readonly=True)
    business_id = fields.Many2one('business.unit', string='Business Unit', required=False,
                                  domain="[('business_type','=','bu')]")
    move_id = fields.Many2one('account.move', 'Current Move')
    paid_amount = fields.Float(string="Paid Amount")
    deduct_amount = fields.Float(string="Deduct Amount",compute='compute_deduct_amount')
    origin_incentive_amount = fields.Float(store=True)


    @api.depends('origin_incentive_amount','incentive_amount')
    def compute_deduct_amount(self):
        for rec in self:
            rec.deduct_amount = rec.origin_incentive_amount - rec.incentive_amount

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('normal.incentive', sequence_date=None) or _('New')

        result = super(NormalIncentive, self).create(vals)

        return result

    def unlink(self):
        for rec in self:
            if rec.state not in ['draft','incentive_approved']:
                raise UserError(_('You cannot Delete this record'))
        return super(NormalIncentive, self).unlink()


    @api.depends('incentive_invoice_ids')
    def _get_incentive_invoice_count(self):
        for line in self:
            line.incentive_invoice_count = len(line.incentive_invoice_ids)

    @api.depends('sale_order_id')
    def _get_invoice_ids(self):
        for line in self:
            invoices = []
            order = line.sale_order_id
            logging.info(order.invoice_ids)
            if order.invoice_ids:
                for temp in order.invoice_ids.ids:
                    invoices.append(temp)
            line.invoice_ids = invoices

    @api.depends('invoice_ids')
    def _get_invoice_count(self):
        for line in self:
            line.invoice_count = len(line.invoice_ids)

    @api.depends('sale_order_id')
    def _get_order_count(self):
        for rec in self:
            rec.sale_order_count = len(rec.sale_order_id)

    def incentive_approved(self):
        for rec in self:
            rec.state = 'incentive_approved'

    def withdraw_incentive(self):

        if not self.journal_id:
            raise ValidationError(_('Journal ID cannot be empty. Please select journal.'))

        if not self.account_id:
            raise ValidationError(_("Account ID cannot be empty."))

        if not self.product_id:
            raise ValidationError(_('Product ID cannot be empty.'))

        invoice_obj = self.env['account.move']
        invoice_line_obj = self.env['account.move.line']

        if self.incentive_definition_id.payment_rule == 'invoice':
            today_date = datetime.today().date()
            invoice_date = today_date
            for invoice in self.invoice_ids:
                invoice_date = invoice.date
            if self.sale_order_id.invoice_status != 'invoiced':
                raise ValidationError(
                    _("Sale order hasn't invoiced yet. After created invoice, incentive can be withraw"))

            inv_line = [
                (0, 0, {
                    'name': self.product_id.name or "",
                    'account_id': self.account_id.id,
                    'price_unit': self.incentive_amount,
                    'quantity': 1.0,
                    'product_uom_id': self.product_id.uom_id.id,
                    'product_id': self.product_id.id,
                })
            ]

            inv = invoice_obj.create({
                'invoice_date': invoice_date,
                'date': invoice_date,
                'invoice_origin': self.name or "",
                'move_type': 'in_invoice',
                'ref': False,
                'invoice_line_ids': inv_line,
                'currency_id': self.currency_id.id if self.currency_id else self.sale_order_id.currency_id.id,
                'journal_id': self.journal_id.id,
                'partner_id': self.partner_id.id,
                'user_id': self.user_id.id,
                'normal_incentive_id': self.id,
                'hr_br_id': self.branch_id.id,
                'hr_bu_id': self.business_id.id,
            })

            self.update({
                'state': 'incentive_withdraw',
                'incentive_invoice_ids': [inv.id],
            })
        elif self.incentive_definition_id.payment_rule == 'payment':
            today_date = datetime.today().date()
            invoice_date = today_date
            for invoice in self.invoice_ids:
                invoice_date = invoice.date
            # if self.sale_order_id.invoice_status != 'invoiced':
            # 	raise ValidationError(_("Sale order hasn't invoiced yet. After created invoice, incentive can be withraw"))

            for invoice in self.invoice_ids:
                if invoice.invoice_payment_state != 'paid':
                    raise ValidationError(_("All invoices haven't paid yet. Please pay for unpaid invoices."))

            inv_line = [
                (0, 0, {
                    'name': self.product_id.name or "",
                    'account_id': self.account_id.id,
                    'price_unit': self.incentive_amount,
                    'quantity': 1.0,
                    'product_uom_id': self.product_id.uom_id.id,
                    'product_id': self.product_id.id,
                })
            ]

            inv = invoice_obj.create({
                'invoice_date': invoice_date,
                'date': invoice_date,
                'invoice_origin': self.name or "",
                'move_type': 'in_invoice',
                'ref': False,
                'invoice_line_ids': inv_line,
                'currency_id': self.currency_id.id if self.currency_id else self.sale_order_id.currency_id.id,
                'journal_id': self.journal_id.id,
                'partner_id': self.partner_id.id,
                'user_id': self.user_id.id,
                'normal_incentive_id': self.id,
                'hr_br_id': self.branch_id.id,
                'hr_bu_id': self.business_id.id,
            })

            inv.post()

            self.update({
                'state': 'incentive_withdraw',
                'incentive_invoice_ids': [inv.id],
            })
        else:
            if self.state == 'incentive_approved':
                incentive_amount = self.incentive_amount / 2;
                today_date = datetime.today().date()
                invoice_date = today_date
                for invoice in self.invoice_ids:
                    invoice_date = invoice.date
                if self.sale_order_id.invoice_status != 'invoiced':
                    raise ValidationError(
                        _("Sale order hasn't invoiced yet. After created invoice, incentive can be withraw"))

                inv_line = [
                    (0, 0, {
                        'name': self.product_id.name or "",
                        'account_id': self.account_id.id,
                        'price_unit': incentive_amount,
                        'quantity': 1.0,
                        'product_uom_id': self.product_id.uom_id.id,
                        'product_id': self.product_id.id,
                    })
                ]

                inv = invoice_obj.create({
                    'invoice_date': invoice_date,
                    'date': invoice_date,
                    'invoice_origin': self.name or " ",
                    'move_type': 'in_invoice',
                    'ref': False,
                    'invoice_line_ids': inv_line,
                    'currency_id': self.currency_id.id if self.currency_id else self.sale_order_id.currency_id.id,
                    'journal_id': self.journal_id.id,
                    'partner_id': self.partner_id.id,
                    'user_id': self.user_id.id,
                    'normal_incentive_id': self.id,
                    'hr_br_id': self.branch_id.id,
                    'hr_bu_id': self.business_id.id,
                })

                inv.post()

                self.update({
                    'state': 'incentive_partially_withdraw',
                    'incentive_invoice_ids': [inv.id],
                })
            elif self.state == 'incentive_partially_withdraw':
                incentive_amount = self.incentive_amount / 2;
                today_date = datetime.today().date()
                invoice_date = today_date
                for invoice in self.invoice_ids:
                    invoice_date = invoice.date
                for invoice in self.invoice_ids:
                    if invoice.invoice_payment_state != 'paid':
                        raise ValidationError(_("All invoices haven't paid yet. Please pay for unpaid invoices."))

                inv_line = [
                    (0, 0, {
                        'name': self.product_id.name or "",
                        'account_id': self.account_id.id,
                        'price_unit': incentive_amount,
                        'quantity': 1.0,
                        'product_uom_id': self.product_id.uom_id.id,
                        'product_id': self.product_id.id,
                    })
                ]

                inv = invoice_obj.create({
                    'invoice_date': invoice_date,
                    'date': invoice_date,
                    'invoice_origin': self.name or " ",
                    'move_type': 'in_invoice',
                    'ref': False,
                    'invoice_line_ids': inv_line,
                    'currency_id': self.currency_id.id if self.currency_id else self.sale_order_id.currency_id.id,
                    'journal_id': self.journal_id.id,
                    'partner_id': self.partner_id.id,
                    'user_id': self.user_id.id,
                    'normal_incentive_id': self.id,
                    'hr_br_id': self.branch_id.id,
                    'hr_bu_id': self.business_id.id,
                })

                inv.post()

                inv_ids = []

                for _id in self.incentive_invoice_ids:
                    inv_ids.append(_id.id)

                inv_ids.append(inv.id)

                self.update({
                    'state': 'incentive_withdraw',
                    'incentive_invoice_ids': inv_ids,
                })

    def action_view_sale_order(self):

        action = self.env.ref('sale_incentive.sale_target_sale_order').read()[0]
        sale_order_id = self.mapped('sale_order_id')
        print('sale order id', sale_order_id)

        if sale_order_id:
            action['domain'] = [('id', 'in', [sale_order_id.id])]

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


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    _description = 'Account Move Line'

    incentive_id = fields.Many2one('normal.incentive.main')
    personal_target_id = fields.Many2one('personal.sale.target')
    asm_id = fields.Many2one('area.incentive.definition')
    request_incentive_id = fields.Many2one('incentive.request')
