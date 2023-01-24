from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError
import logging
from datetime import datetime

class AreaIncentiveDefinition(models.Model):
    _name = 'area.incentive.definition'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Area Rule Definition'

    def _default_currency(self):
        return self.env.user.company_id.currency_id.id

    def action_view_sale_order(self):
        action = self.env.ref('sale_incentive.sale_target_sale_order').read()[0]
        sale_order_ids = self.mapped('sale_order_ids')
        if len(sale_order_ids) >= 1:
            action['domain'] = [('id', 'in', sale_order_ids.ids)]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action
    
    def action_move_items(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_account_moves_all_a")
        action['domain'] = [('asm_id', '=', self.id)]
        return action

    name = fields.Char('Name')
    user_id = fields.Many2one('res.users', string='Area Manager')
    partner_id = fields.Many2one('res.partner', string='Area Manager')
    date_start = fields.Date('Start Date')
    date_end = fields.Date('End Date')
    target = fields.Float('Target', compute='compute_saletarget')
    sale_total = fields.Float('Sale Total', compute='compute_saletarget')
    target_reached = fields.Float('Reached Target', compute='_compute_target_reached')
    incentive = fields.Float('Incentive Amount', compute='_compute_incentive_amount')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=_default_currency)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('request_incentive_approved', 'Request Incentive Approved'),
        ('incentive_approved', 'Incentive Approved'),
        ('reject', 'Rejected'),
        ('incentive_withdraw', 'Incentive Withdraw'),
        ('incentive_partially_withdraw', 'Incentive Partially Withdraw'),
    ], string="Status", readonly=True, default="draft", tracking=True)
    branch_ids = fields.Many2many('business.unit', 'area_ince_branch_ref',string='Branches',domain="[('business_type','=','br')]")
    business_id = fields.Many2one('business.unit', string='Business Unit',domain="[('business_type','=','bu')]")
    incentive_performance_range_ids = fields.One2many('incentive.performance.range', 'area_rule_id',
                                                      string="Incentive Performance Range")
    incentive_calculation = fields.Selection([('agent', 'Fixed Amount Division to Multiple Agent'),
                                            ('percentage', 'Fixed Percentage Division to Multiple Agent')
                                            ], string="Incentive Calculation", default='agent')
    approval_person = fields.Many2one('res.users', 'Approval Person')
    journal_id = fields.Many2one('account.journal', string="Incentive Journal")
    account_id = fields.Many2one("account.account", string="Incentive Account", domain="[('bu_br_id','=',business_id)]")
    product_id = fields.Many2one("product.product", string="Product for Invoicing")
    sale_order_ids = fields.Many2many('sale.order', string="Sale Orders", readonly=True,compute='_compute_sale_order_ids')
    sale_order_count = fields.Integer(string="Sale Order Count", compute="_get_sale_order", readonly=True)
    incentive_invoice_ids = fields.Many2many('account.move', string="Invoices", readonly=True)
    incentive_invoice_count = fields.Integer(string="Incentive Bill Count", compute="_get_incentive_invoice_count", readonly=True)
    incentive_currency_id = fields.Many2one('res.currency','Incentive Currency')


    @api.depends('incentive_invoice_ids')
    def _get_incentive_invoice_count(self):
        for line in self:
            line.incentive_invoice_count = len(line.incentive_invoice_ids)

    @api.depends('sale_order_ids')
    def _get_sale_order(self):
        for line in self:
            line.sale_order_count = len(line.sale_order_ids)

    @api.depends('branch_ids')
    def _compute_sale_order_ids(self):
        for line in self:
            orders = []
            target_ids = self.env['sale.team.target'].search([('branch_id', 'in', line.branch_ids.ids), ('start_date', '>=', line.date_start),
                                                                ('end_date', '<=', line.date_end)])
            if target_ids:
                for target in target_ids:
                    for sale in target.sale_order_ids:
                        orders.append(sale.id)

            line.sale_order_ids = orders

    @api.depends('branch_ids')
    def compute_saletarget(self):
        for rec in self:
            target = saletotal = 0.0
            target_ids = self.env['sale.team.target'].search([('branch_id', 'in', rec.branch_ids.ids), ('start_date', '>=', rec.date_start), ('end_date', '<=', rec.date_end)])
            if target_ids:
                for sale_team in target_ids:
                    target += sale_team.target
            rec.target = target
            personal_ids = self.env['personal.sale.target'].search([('branch_id', 'in', rec.branch_ids.ids), ('start_date', '>=', rec.date_start), ('end_date', '<=', rec.date_end)])
            if personal_ids:
                for personal in personal_ids:
                    saletotal += personal.sale_total
            rec.sale_total = saletotal

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
                line.incentive = 0.0
                continue

            amount = 0.0
            define_incentive_amount = 0.0
            target_reached = line.target_reached
            if line.incentive_calculation == 'agent':
                for record in line.incentive_performance_range_ids:
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
                for record in line.incentive_performance_range_ids:
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

            line.incentive = define_incentive_amount

    def incentive_approved(self):
        res = []
        amount = self.currency_id._convert(self.incentive,
                                            self.env.user.company_id.currency_id,
                                            self.env.user.company_id,
                                            datetime.today(),
                                        )
        move_line = {'name': self.name,
                     'partner_id': self.user_id.partner_id.id,
                     'account_id': self.account_id.id,
                     'business_id': self.business_id.id,
                     'date': datetime.today(),
                     'amount_currency': self.incentive,
                     'debit': amount,
                     'currency_id': self.currency_id.id,
                     'asm_id': self.id, }
        res.append(move_line)
        move_line = {'name': self.name,
                     'partner_id': self.user_id.partner_id.id,
                     'account_id': self.business_id.asm_account_id.id,
                     'business_id': self.business_id.id,
                     'date': datetime.today(),
                     'amount_currency': -self.incentive,
                     'credit': amount,
                     'currency_id': self.currency_id.id,
                     'asm_id': self.id, }
        res.append(move_line)
        line_ids = [(0, 0, l) for l in res]
        vals = {
            'journal_id': self.journal_id.id,
            'ref': self.name,
            'date': datetime.today(),
            'line_ids': line_ids,
        }
        self.env['account.move'].create(vals).action_post()
        return self.write({'state':'incentive_approved'})

    def withdraw_incentive(self):
       return True



class IncentiveCalculationRuleInherited(models.Model):
    _inherit = 'incentive.performance.range'
    _description = 'Incentive Calculation Rule'

    area_rule_id = fields.Many2one('area.incentive.definition', string='Area Incentive Rule')
    currency_id = fields.Many2one(related='area_rule_id.incentive_currency_id',string="Currency")


