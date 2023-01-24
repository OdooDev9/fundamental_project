from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError,ValidationError
from datetime import date, datetime
import logging
class ReInstallment(models.Model):
    _name = 're.installment.plan'
    _description = 'Reinstallment Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    order_id = fields.Many2one('sale.order', string='Sale Order')
    installment_plan_id = fields.Many2one('installment.plan', string="Installment Plan")

    installment_ids = fields.One2many('sale.installment.line', 're_installment_id', 'Installments')
    down_payment_amt = fields.Float(string="Down Payment With Taxed", compute='_compute_down_payment_amt', readonly=True,help="Down Payment that is calculated by down payment plus amount tax",digits=(12,2))

    second_payment_date = fields.Date(readonly=True, states={'draft': [('readonly', False)]})
    installment_amt = fields.Float(string="Installment Amount", compute='_compute_installment_amt', readonly=True, states={'draft': [('readonly', False)]},digits=(12,2))
    payable_amt = fields.Float(string="Payable Amount", compute='_compute_payable_amt', readonly=True, states={'draft': [('readonly', False)]},digits=(12,2))
    tenure = fields.Integer(string="Tenure(Peroid)", readonly=True, states={'draft': [('readonly', False)]})

    payment_circle_count = fields.Integer(string="Payment Every (Month)",default=1,readonly=True, states={'draft': [('readonly', False)]})
    fine_threshold = fields.Integer(string="Fine Threshold", help="To start fine calculation!")

    tenure_type = fields.Selection([
            ('month','months'),
            ('year','years'),
        ], string="Tenure Type",default="month",required=True)

    tenure_amt = fields.Float(string="Sale Amount")
    tenure_amount_untaxed = fields.Float(string="Tenure Untaxed Amount")
    tenure_amount_tax = fields.Float(string="Taxes")

    down_payment_type = fields.Selection([
                ('percent','Percentage(%)'),
                ('fix', 'Fixed')
            ],string="Down Payment Type",required=False,readonly=True,states={'draft': [('readonly', False)]},default="percent")

    down_payment_percent = fields.Float(string="Down Payment(%)",default=0.0,readonly=True,states={'draft': [('readonly', False)]})
    down_payment_fixed = fields.Float(string="Down Payment(Fixed)",default=0.0,readonly=True,states={'draft': [('readonly', False)]})

    interest_rate = fields.Float(string="Interest Rate(%)",default=0.0,required=True)
    interest_start_from = fields.Integer(string="Interest Start From",default=1,help="Interest Start Index")
    fine_rate = fields.Float(string="Fine Rate(%)",default=0.0,required=True)
    fine_discount = fields.Float(string="Fine Discount")

    start_invoice_date = fields.Date(string="Start Invoice Date",required=True,readonly=True,states={'draft':[('readonly',False)]},default=fields.Datetime.now)
    contract_date = fields.Date(string="Contract Date",required=True,readonly=True,states={'draft': [('readonly',False)]},default=fields.Datetime.now)
    state = fields.Selection([('draft', 'Draft'),('approved_finance_head','Approved Finance Head'),('approved_corp_finance_head','Approved Corporate Finance Head'),('confirm','Running'), ('close', 'Close')], string='State', default='draft', tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id.id)
    name = fields.Char(string='Sequence', required=True, readonly=True, default='New', copy=False)
    partner_id = fields.Many2one('res.partner')
    invoice_count = fields.Integer(compute='_get_invoice_count')
    down = fields.Boolean()
    note = fields.Text()
    hr_bu_id = fields.Many2one('business.unit', 'Business Unit',domain="[('business_type','=','bu')]")
    hr_br_id = fields.Many2one('business.unit', 'Branch',domain="[('business_type','=','br')]")
    total_interest = fields.Float(compute='compute_interest')
    amount_residual = fields.Float(compute='compute_residual_amount')

    bu_br_user_approve = fields.Boolean(compute='compute_bu_br_user_approve')
    is_cor  = fields.Boolean(compute='compute_cor_user_approve')

    def compute_cor_user_approve(self):
        if self.env.user.user_type_id == 'cfd':
            self.is_cor = True
        else:
            self.is_cor = False
            
    def compute_bu_br_user_approve(self):
        for rec in self:                
            if self.env.user.user_type_id == 'bu':
                rec.bu_br_user_approve = True      
            else:
                rec.bu_br_user_approve = False


    def action_approve_finance_head(self):
        if self.state == 'draft':
            self.state = 'approved_finance_head'
    
    def action_approve_corp_finance_head(self):
        if self.state  == 'approved_finance_head':
            self.state = 'approved_corp_finance_head'

    def compute_interest(self):
        for rec in self:
            amount = 0.0
            for line in rec.installment_ids:
                amount += line.interest_amount
            rec.total_interest = amount

    def compute_residual_amount(self):
        for rec in self:
            rec.amount_residual = rec.tenure_amt + rec.total_interest
            invoice_ids = self.env['account.move'].search([('re_contract_id', '=', rec.id)])
            if invoice_ids:
                for invoice in invoice_ids:
                    rec.amount_residual -= invoice.amount_total_signed

    def _get_invoice_count(self):
        for rec in self:
            invoices = self.env['account.move'].search([('re_contract_id', '=', rec.id)])
            rec.invoice_count = len(invoices)

    def action_invoice_wizard(self):
        view = self.env.ref('payment_installment_kanak.view_installment_advance_payment_inv')
        res = {
            'name': _('Create Invoice'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'installment.invoice.wizard',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': dict(self.env.context, default_recontract_id=self.id, default_down=self.down),
        }
        return res

    def action_invoice_view(self):
        form_view = self.env.ref('account.view_move_form').id
        tree_view = self.env.ref('account.view_out_invoice_tree').id
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_invoice_type")
        action['domain'] = [('re_contract_id', '=', self.id)]
        action['views'] = [(tree_view, 'tree'), (form_view, 'form')]
        return action

    def action_confirm(self):
        for rec in self:
            rec.state = 'confirm'
            rec.compute_installment()

    def action_close(self):
        for rec in self:
            rec.state = 'close'

    @api.onchange('installment_plan_id')
    def _onchange_installment_plan_id(self):
        for record in self:
            if record.installment_plan_id:
                record.tenure = record.installment_plan_id.tenure
                record.tenure_type = record.installment_plan_id.tenure_type
                record.down_payment_type = record.installment_plan_id.down_payment_type
                record.down_payment_percent = record.installment_plan_id.down_payment_percent
                record.down_payment_fixed = record.installment_plan_id.down_payment_fixed
                record.interest_rate = record.installment_plan_id.interest_rate
                record.interest_start_from = record.installment_plan_id.interest_start_from
                record.fine_rate = record.installment_plan_id.fine_rate
                record.payment_circle_count = record.installment_plan_id.payment_circle_count
                record.fine_threshold = record.installment_plan_id.fine_threshold

    @api.depends('tenure_amt', 'down_payment_percent', 'down_payment_fixed', 'down_payment_type')
    def _compute_down_payment_amt(self):
        for record in self:
            value = 0.0
            if record.down_payment_type == 'percent':
                percent = record.down_payment_percent / 100
                value = percent * record.tenure_amt
            else:
                value = record.down_payment_fixed
            record.down_payment_amt = value

    @api.depends('tenure', 'payable_amt')
    def _compute_installment_amt(self):
        for record in self:
            value = 0.0
            if record.tenure:
                if record.payment_circle_count > 0.0:
                    value = record.payable_amt / (record.tenure / record.payment_circle_count)
            record.installment_amt = value

    @api.depends('down_payment_amt')
    def _compute_payable_amt(self):
        for record in self:
            value = 0.0
            if record.tenure_amt:
                value = record.tenure_amt - record.down_payment_amt
            record.payable_amt = value

    def compute_installment(self):
        for order in self:
            order.total_interest = 0.0
            amount_total = order.payable_amt
            tenure = order.tenure
            installment_ids = []
            today_date = self.start_invoice_date + relativedelta(months=order.payment_circle_count)
            interest_rate = order.interest_rate
            without_interest_amount = order.installment_amt
            if order.down_payment_amt:
                pass
            if order.installment_amt:
                index = 1
                interest_start = order.interest_start_from
                payment_date = order.second_payment_date or today_date
                amount = order.installment_amt
                total_remaining_amount = order.tenure_amt - order.down_payment_amt
                interest_amount = 0.0
                installment_ids = [(2, line_id.id, False) for line_id in self.installment_ids]

                while tenure > 0:
                    if tenure == 1:
                        amount = amount_total
                    if index >= interest_start:
                        interest_amount = total_remaining_amount * (interest_rate / 100)
                    installment_ids.append((0, 0, {
                        'index': index,
                        'without_interest_amount': order.installment_amt,
                        'interest_rate': interest_rate,
                        'interest_amount': interest_amount,
                        'total_remaining_amount': total_remaining_amount,
                        'payment_date': payment_date,
                        'fine_rate': order.fine_rate,
                        'description': '%s installment' % index,
                    }))
                    total_remaining_amount = total_remaining_amount - order.installment_amt
                    index += 1
                    tenure -= order.payment_circle_count
                    payment_date += relativedelta(months=order.payment_circle_count)
                    amount_total -= order.installment_amt
            last_month =order.tenure/order.payment_circle_count
            latest_installment_amt = order.installment_amt * (last_month - 1)
            latest_without_interest_amt = order.payable_amt - latest_installment_amt
                
            last_obj = installment_ids[-1][-1]
            last_obj['without_interest_amount']= latest_without_interest_amt   
            if installment_ids:
                order.installment_ids = installment_ids
        return True
    def action_installment_modify(self):
        self.ensure_one()
        view = self.env.ref('payment_installment_kanak.modify_reinstallment_form')
        new_wizard = self.env['modify.installment'].create({
            'name': self.name,
            're_contract_id': self.id,
        })
        new_wizard.onchange_contract()
        return {
            'name': _('Modify Installment'),
            'view_mode': 'form',
            'res_model': 'modify.installment',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': new_wizard.id,
            'context': self.env.context,
        }

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('re.installment.plan') or 'New'
        result = super(ReInstallment, self).create(vals)
        return result

    class AccountMove(models.Model):
        _inherit = 'account.move'

        re_contract_id = fields.Many2one('re.installment.plan')

    class SaleOrder(models.Model):
        _inherit = 'sale.order'

        contract_count = fields.Integer(compute='_get_contract_count')

        def _get_contract_count(self):
            for rec in self:
                contracts = self.env['re.installment.plan'].search([('order_id', '=', rec.id)])
                rec.contract_count = len(contracts)

        def action_recontract(self):
            # print("*"*100)
            # installment_ids = self.invoice_ids[-1].amount_residual
            # amount = sum(installment_ids.mapped('amount'))
            # paid_amount = sum(installment_ids.mapped('paid_amount'))
            # recontract_amount = amount-paid_amount
            # print('recontract_amount ==> ',recontract_amount)
            # print("fine_amount ==> ",sum(self.invoice_ids[-1].installment_ids.mapped('fine_amount')))
            view = self.env.ref('payment_installment_kanak.re_contract_wizard_form')
            context = dict(self.env.context, default_order_id=self.id, default_installment_plan_id=self.installment_plan_id.id)
            context['default_amount'] = self.invoice_ids[-1].amount_residual + sum(self.invoice_ids[-1].installment_ids.mapped('fine_amount'))
            res = {
                'name': _('Re-Contract'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 're.contract.wizard',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'context': context,
            }
            return res

        def action_view_recontract(self):
            action = self.env["ir.actions.actions"]._for_xml_id("payment_installment_kanak.re_installment_plan_action")
            action['domain'] = [('order_id', '=', self.id)]
            return action
