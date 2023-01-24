# -*- coding: utf-8 -*-
#################################################################################
# Author      : Kanak Infosystems LLP. (<http://kanakinfosystems.com/>)
# Copyright(c): 2012-Present Kanak Infosystems LLP.
# All Rights Reserved.
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <http://kanakinfosystems.com/license>
#################################################################################
from odoo import api, fields, models, Command, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from odoo.tools import float_compare, date_utils, email_split, email_re, html_escape, is_html_empty
from odoo.tools.misc import formatLang, format_date, get_lang
from dateutil.relativedelta import relativedelta
from datetime import date, timedelta
from collections import defaultdict
from contextlib import contextmanager
from itertools import zip_longest
from hashlib import sha256
from json import dumps

import ast
import json
import re
import warnings


class InstallmentPlan(models.Model):
    _name = 'installment.plan'
    _description = 'Installment Plan'

    name = fields.Char(string="Name", required=True)
    tenure_type = fields.Selection([
        ('month', 'months'),
    ], string="Tenure Type", default="month")
    tenure = fields.Integer(string="Tenure", required=True)

    down_payment_type = fields.Selection([
        ('percent', 'Percentage(%)'),
        ('fix', 'Fixed')
    ], string="Down Payment Type", required=True, default="percent")

    down_payment_percent = fields.Float(string="Down Payment(%)", default=0.0)
    down_payment_fixed = fields.Float(
        string="Down Payment(Fixed)", default=0.0)

    payment_circle_count = fields.Integer(
        string="Payment Every(Month)", default=1, help="Payment Circle Count")
    fine_threshold = fields.Integer(
        string="Fine Threshold", default=7, help="To start fine calculation!")

    interest_rate = fields.Float(
        string="Interest Rate(%)", default=0.0, required=True)
    interest_start_from = fields.Integer(
        string="Interest Start From", default=1, help="Interest Start Index")
    fine_rate = fields.Float(string="Fine Rate(%)", default=0.0, required=True)

    branch_id = fields.Many2one(
        'business.unit', string="Branch Name", domain="[('business_type','=','br')]")

    is_bu_user = fields.Boolean(string="Is Bu User", search="_search_field")

    show_plan_for_bu = fields.Boolean(
        string="Show Plan", search="_search_field_plan")

    user_id = fields.Many2one(
        'res.users', string='Salesperson', index=True, default=lambda self: self.env.user)
    business_id = fields.Many2one('business.unit', string="Business Unit",
                                  default=lambda self: self.env.user.current_bu_br_id.id)
    state = fields.Selection([
        ('new', 'New'),
        ('approved_finance', 'Approved F & A Head'),
        ('cancel', 'Cancel'),
    ], string="State", default="new")

    def action_approve(self):
        for rec in self:
            rec.state = 'approved_finance'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'

    def action_new(self):
        for rec in self:
            rec.state = 'new'

    def _search_field_plan(self, operator, value):
        field_id = self.search([]).filtered(
            lambda x: x.show_plan_for_bu == value)
        return [('id', operator, [x.id for x in field_id] if field_id else False)]

    def _search_field(self, operator, value):
        field_id = self.search([]).filtered(lambda x: x.is_bu_user == value)
        return [('id', operator, [x.id for x in field_id] if field_id else False)]

    @api.ondelete(at_uninstall=False)
    def _unlink_except_draft_or_cancel(self):
        for rec in self:
            if rec.state not in ('new', 'cancel'):
                raise UserError(_('You can not delete a confirmed installment. You must first cancel it.'))


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    plan_branches = fields.Many2many(
        'business.unit', string="Branches", domain="[('business_type','=','br')]")

    installment_plan_id = fields.Many2one(
        'installment.plan', string="Installment Plan")

    installment_ids = fields.One2many(
        'sale.installment.line', 'sale_id', 'Installments')
    down_payment_amt = fields.Monetary(string="Down Payment With Taxed", compute="_compute_down_payment_amt",
                                       readonly=True,
                                       help="Down Payment that is calculated by down payment plus amount tax")

    second_payment_date = fields.Date(
        readonly=True, states={'draft': [('readonly', False)]})
    installment_amt = fields.Monetary(string="Installment Amount", compute="_compute_installment_amt", readonly=True,
                                      states={
                                          'draft': [('readonly', False)]})
    payable_amt = fields.Monetary(string="Payable Amount", compute="_compute_payable_amt", readonly=True, states={
        'draft': [('readonly', False)]}, )
    tenure = fields.Integer(string="Tenure(Peroid)", readonly=True, states={
        'draft': [('readonly', False)]})

    payment_circle_count = fields.Integer(
        string="Payment Every (Month)", default=1, readonly=True, states={'draft': [('readonly', False)]})
    fine_threshold = fields.Integer(
        string="Fine Threshold", help="To start fine calculation!")

    tenure_type = fields.Selection([
        ('month', 'months'),
        ('year', 'years'),
    ], string="Tenure Type", default="month", required=True)

    tenure_amt = fields.Monetary(
        compute="_compute_tenure_amt", string="Sale Amount")
    tenure_amount_untaxed = fields.Monetary(
        compute="_compute_amount_untaxed", string="Tenure Untaxed Amount")
    tenure_amount_tax = fields.Monetary(
        compute="_compute_amount_tax", string="Taxes")

    down_payment_type = fields.Selection([
        ('percent', 'Percentage(%)'),
        ('fix', 'Fixed')
    ], string="Down Payment Type", required=False, readonly=True, states={'draft': [('readonly', False)]},
        default="percent")

    down_payment_percent = fields.Float(
        string="Down Payment(%)", default=0.0, readonly=True, states={'draft': [('readonly', False)]})
    down_payment_fixed = fields.Monetary(currency_field='currency_id', string="Down Payment(Fixed)", default=0.0,
                                         readonly=True, states={
            'draft': [('readonly', False)]})

    interest_rate = fields.Float(
        string="Interest Rate(%)", default=0.0, required=True)
    interest_start_from = fields.Integer(
        string="Interest Start From", default=1, help="Interest Start Index")
    fine_rate = fields.Float(string="Fine Rate(%)", default=0.0, required=True)
    fine_discount = fields.Monetary(currency_field='currency_id', string="Fine Discount")

    start_invoice_date = fields.Date(string="Start Invoice Date", required=True, readonly=True, states={
        'draft': [('readonly', False)]}, default=fields.Datetime.now)
    contract_date = fields.Date(string="Contract Date", required=True, readonly=True, states={
        'draft': [('readonly', False)]}, default=fields.Datetime.now)

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

    @api.depends('amount_tax')
    def _compute_amount_tax(self):
        for record in self:
            record.tenure_amount_tax = record.amount_tax

    @api.depends('amount_untaxed')
    def _compute_amount_untaxed(self):
        for record in self:
            amount_untaxed = record.amount_untaxed

            for line in self.order_line:
                if line.is_interest:
                    amount_untaxed -= line.price_subtotal

            record.tenure_amount_untaxed = amount_untaxed

    @api.depends("amount_total")
    def _compute_tenure_amt(self):
        for record in self:

            amount_total = record.amount_total
            for line in self.order_line:
                if line.is_interest:
                    amount_total -= line.price_total
            record.tenure_amt = amount_total

    @api.depends('tenure_amount_tax', 'tenure_amount_untaxed', 'down_payment_percent', 'down_payment_fixed',
                 'down_payment_type')
    def _compute_down_payment_amt(self):
        for record in self:
            value = 0.0
            if record.down_payment_type == 'percent':
                percent = record.down_payment_percent / 100
                value = percent * record.tenure_amount_untaxed
            else:
                value = record.down_payment_fixed
            record.down_payment_amt = value + record.tenure_amount_tax

    @api.onchange("installment_amt")
    def _onchange_installment_amt_tenure(self):
        if self.installment_amt:
            self.with_context({'installment_amt': self.installment_amt}
                              ).tenure = self.payable_amt / self.installment_amt

    @api.depends("tenure", "payable_amt")
    def _compute_installment_amt(self):
        for record in self:
            value = 0.0
            if record.tenure:
                if record.payment_circle_count > 0.0:
                    value = record.payable_amt / \
                            (record.tenure / record.payment_circle_count)
            record.installment_amt = value

    def onchange(self, values, field_name, field_onchange):
        return super(SaleOrder, self.with_context(recursive_onchanges=False)).onchange(values, field_name,
                                                                                       field_onchange)

    @api.depends("down_payment_amt", "order_line")
    def _compute_payable_amt(self):
        for record in self:
            value = 0.0
            if record.tenure_amt:
                value = record.tenure_amt - record.down_payment_amt
            record.payable_amt = value

    def action_draft(self):
        orders = self.filtered(lambda s: s.state in ['cancel', 'sent'])
        # orders.installment_ids.unlink()
        # orders.write({'down_payment_amt': 0.0, 'installment_amt': 0.0, 'second_payment_date': False, 'payable_amt': 0.0, 'tenure': 1})
        res = super(SaleOrder, self).action_draft()
        return res

    def compute_installment(self):
        total_remaining_amount = 0.0
        total_interest = 0
        for order in self:
            amount_total = order.payable_amt
            tenure = order.tenure
            installment_ids = []
            today_date = self.start_invoice_date + \
                         relativedelta(months=order.payment_circle_count)
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
                installment_ids = [(2, line_id.id, False)
                                   for line_id in self.installment_ids]

                while tenure > 0:
                    # if amount_total < 0.0:
                    #   raise UserError(_("Installment Amount Or Number Of Installment Mismatch Error."))
                    if tenure == 1:
                        amount = amount_total
                    if index >= interest_start:
                        interest_amount = total_remaining_amount * \
                                          (interest_rate / 100)

                    installment_ids.append((0, 0, {
                        'index': index,
                        # 'amount': amount,
                        'without_interest_amount': order.installment_amt,
                        'interest_rate': interest_rate,
                        'interest_amount': interest_amount,
                        'total_remaining_amount': total_remaining_amount,
                        'payment_date': payment_date,
                        'fine_rate': order.fine_rate,
                        'description': '%s installment' % index,
                    }))
                    # installment_ids[-1].append({'interest_amount': latest_without_interest_amt})

                    total_interest += interest_amount
                    total_remaining_amount = total_remaining_amount - order.installment_amt

                    index += 1
                    tenure -= order.payment_circle_count
                    payment_date += relativedelta(
                        months=order.payment_circle_count)
                    amount_total -= order.installment_amt

                last_month = order.tenure / order.payment_circle_count
                print(last_month, '>>>>>>>>>>>>>>>>>>>>>>')

                latest_installment_amt = order.installment_amt * (last_month - 1)
                latest_without_interest_amt = order.payable_amt - latest_installment_amt

                last_obj = installment_ids[-1][-1]
                last_obj['without_interest_amount'] = latest_without_interest_amt
            if installment_ids:
                order.installment_ids = installment_ids

        product_categs = self.env['product.category'].search(
            [('business_id', '=', self.hr_bu_id.id), ('name', '=', 'Services')])
        if not product_categs:
            product_categs = self.env['product.category'].create({'name': 'Services',
                                                                  'business_id': self.hr_bu_id.id})
        interest_product = self.env['product.product'].search([('name', '=', 'Interest'), ('type', '=', 'service'),
                                                               ('business_id', '=', self.hr_bu_id.id)])

        if not interest_product:
            interest_product = self.env['product.product'].create({'name': 'Interest',
                                                                   'type': 'service',
                                                                   'business_id': self.hr_bu_id.id,
                                                                   'categ_id': product_categs.id})
        order_line_id = self.order_line.filtered(
            lambda x: x.product_id == interest_product)
        if order_line_id:
            order_line_id.price_unit = total_interest
        else:
            if total_interest:
                sol = self.env['sale.order.line'].create({
                    'product_id': interest_product.id,
                    'order_id': self.id,
                    'name': interest_product.product_tmpl_id.name,
                    'product_uom_qty': 1.0,
                    'product_uom': interest_product.product_tmpl_id.uom_id.id,
                    'price_unit': total_interest,
                    'is_interest': True,
                })

    @api.model
    def create(self, vals):
        if 'company_id' in vals:
            self = self.with_company(vals['company_id'])
        if vals.get('name', _('New')) == _('New'):
            seq_date = None
            if 'date_order' in vals:
                seq_date = fields.Datetime.context_timestamp(
                    self, fields.Datetime.to_datetime(vals['date_order']))
            # vals['name'] = self.env['ir.sequence'].next_by_code('sale.order', sequence_date=seq_date) or _('New')

        # Makes sure partner_invoice_id', 'partner_shipping_id' and 'pricelist_id' are defined
        if any(f not in vals for f in ['partner_invoice_id', 'partner_shipping_id', 'pricelist_id']):
            partner = self.env['res.partner'].browse(vals.get('partner_id'))
            addr = partner.address_get(['delivery', 'invoice'])
            vals['partner_invoice_id'] = vals.setdefault(
                'partner_invoice_id', addr['invoice'])
            vals['partner_shipping_id'] = vals.setdefault(
                'partner_shipping_id', addr['delivery'])
            vals['pricelist_id'] = vals.setdefault(
                'pricelist_id', partner.property_product_pricelist.id)
        result = super(SaleOrder, self).create(vals)
        if not vals.get('installment_plan_id'):
            return result
        result.compute_installment()
        return result

    def write(self, values):
        result = super(SaleOrder, self).write(values)
        if 'order_line' in values or 'installment_plan_id' in values:
            self.compute_installment()
        return result

    def _prepare_invoice(self):
        res = super(SaleOrder, self)._prepare_invoice()
        installment_ids = []

        for order in self:

            ar_balance = 0.0
            for line in order.installment_ids:
                if line.index == 0:
                    continue
                ar_balance += line.without_interest_amount
                ar_balance += line.interest_amount
            payment_start_date = order.start_invoice_date
            for line in order.installment_ids:
                payment_end_date = line.payment_date + relativedelta(months=order.payment_circle_count)
                if line.index == 0:
                    installment_ids.append((0, 0, {
                        'index': line.index,
                        'without_interest_amount': line.without_interest_amount,
                        'amount': line.amount,
                        'interest_rate': line.interest_rate,
                        'interest_amount': line.interest_amount,
                        'total_remaining_amount': line.total_remaining_amount,
                        'payment_start_date': payment_start_date,
                        'payment_end_date': payment_end_date,
                        'payment_date': line.payment_date,
                        'fine_rate': line.fine_rate,
                        'description': line.description,
                        'ar_balance': ar_balance,
                        'sinst_line_id': line.id,
                    }))
                elif line.index == 1:
                    installment_ids.append((0, 0, {
                        'index': line.index,
                        'without_interest_amount': line.without_interest_amount,
                        'amount': line.amount,
                        'interest_rate': line.interest_rate,
                        'interest_amount': line.interest_amount,
                        'total_remaining_amount': line.total_remaining_amount,
                        'payment_start_date': payment_start_date,
                        'payment_end_date': payment_end_date,
                        'payment_date': line.payment_date,
                        'fine_rate': line.fine_rate,
                        'description': line.description,
                        'ar_balance_previous': ar_balance,
                        'is_active': True,
                        'sinst_line_id': line.id,
                    }))
                else:
                    installment_ids.append((0, 0, {
                        'index': line.index,
                        'without_interest_amount': line.without_interest_amount,
                        'amount': line.amount,
                        'interest_rate': line.interest_rate,
                        'interest_amount': line.interest_amount,
                        'total_remaining_amount': line.total_remaining_amount,
                        'payment_start_date': payment_start_date,
                        'payment_end_date': payment_end_date,
                        'payment_date': line.payment_date,
                        'fine_rate': line.fine_rate,
                        'description': line.description,
                        'sinst_line_id': line.id,
                    }))
                payment_start_date = line.payment_date + timedelta(days=1)
        res.update({'installment_ids': installment_ids})
        res.update({
            'down_payment_amt': self.down_payment_amt,
            'second_payment_date': self.second_payment_date,
            'installment_amt': self.installment_amt,
            'payable_amt': self.payable_amt,
            'tenure': self.tenure,
            'payment_circle_count': self.payment_circle_count,
            'fine_threshold': self.fine_threshold,
            'tenure_type': self.tenure_type,
            'tenure_amt': self.tenure_amt,
            'tenure_amount_untaxed': self.tenure_amount_untaxed,
            'tenure_amount_tax': self.tenure_amount_tax,
            'down_payment_type': self.down_payment_type,
            'down_payment_percent': self.down_payment_percent,
            'down_payment_fixed': self.down_payment_fixed,
            'interest_rate': self.interest_rate,
            'interest_start_from': self.interest_start_from,
            'fine_rate': self.fine_rate,
            'fine_discount': self.fine_discount,
            'start_invoice_date': self.start_invoice_date,
            'contract_date': self.contract_date,
            'hr_bu_id': self.hr_bu_id.id,
            'hr_br_id': self.hr_br_id.id,
            'service_type': self.service_type or False,
            'br_discount_amount': self.br_discount_amount,
            'discount_type': self.discount_type,
            'discount_value': self.discount_value,
            'br_discount': self.br_discount,
            'discount_view': self.discount_view,
            'unit_or_part': self.unit_or_part,
            'sale_order_id': self.id,
            'is_gov_tender': self.is_gov_tender,
        })

        return res


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    installments = fields.Integer(string="#Installments")
    is_interest = fields.Boolean(string="Interest?")


class SaleInstallmentLine(models.Model):
    _name = 'sale.installment.line'
    _description = 'Sale Installment Line'
    _order = 'payment_date'
    _rec_name = 'description'

    state = fields.Selection([
        ('draft', 'Future Due'),
        ('follow_up', 'Follow Up'),
        ('remind', 'Remind'),
        ('need_action', 'Need Action'),
        ('take_action', 'Take Action'),
        ('paid', 'Paid'),
        ('skip', 'Skip Payment'),
    ], default='draft', string="Status")
    total_remaining_amount = fields.Monetary(currency_field='currency_id',
                                             string="Remaing AR Balance", default=0.0)
    total_remaining_amount_view = fields.Monetary(
        string="Remaing AR Balance", compute="_compute_for_view")

    interest_rate = fields.Float(
        string="Interest Rate(%)", default=0.0)
    interest_rate_view = fields.Float(
        string="Interest Rate(%)", compute="_compute_for_view")

    without_interest_amount = fields.Monetary(currency_field='currency_id', store=True, readonly=True,
                                              string="Amount(Without Interest)", default=0.0)
    without_interest_amount_view = fields.Monetary(
        string="Amount(Without Interest)", compute="_compute_for_view")

    interest_amount = fields.Monetary(currency_field='currency_id',
                                      string="Interest Amount", default=0.0)
    interest_amount_view = fields.Monetary(
        string="Interest Amount", compute="_compute_for_view")

    due_amount = fields.Monetary(currency_field='currency_id', string="Due Amount", default=0.0)

    fine_current_period = fields.Monetary(currency_field='currency_id',
                                          string="Fine(Current Peroid)", default=0.0)
    fine_previous_period = fields.Monetary(currency_field='currency_id',
                                           string="Fine(Previous Peroid)", default=0.0)
    fine_discount = fields.Monetary(currency_field='currency_id',
                                    string="Fine Discount", default=0.0)
    interest_discount = fields.Monetary(currency_field='currency_id',
                                        string="Interest Discount", default=0.0)

    fine_amount = fields.Monetary(currency_field='currency_id',
                                  string="Fine Amount", default=0.0)
    each_period_ar_amount = fields.Monetary(
        compute="_compute_each_period_ar_amount", string="Each Period Ar Amount")
    each_period_ar_amount_view = fields.Monetary(
        compute="_compute_for_view", string="Each Period Ar Amount")

    amount = fields.Monetary(compute="_compute_amount")
    amount_view = fields.Monetary(compute="_compute_for_view")

    paid_amount = fields.Monetary(string="Paid Amount")
    rv_date = fields.Char(string="RV Date", readonly=True)
    rv_no = fields.Char(string="RV No.", readonly=True)

    fine_paid = fields.Monetary(currency_field='currency_id',
                                string="Fine Paid(Auto depend on Paid)", readonly=True)
    principal_paid = fields.Monetary(currency_field='currency_id',
                                     string="Principal Paid(Auto depend on Paid)", readonly=True)
    fine_amount = fields.Monetary(currency_field='currency_id', string="Fine Amount")
    fine_rate = fields.Monetary(currency_field='currency_id', string="Fine Rate", default=0.0)
    index = fields.Integer(string="#No")
    sale_id = fields.Many2one('sale.order', 'Sale Order', ondelete="cascade")
    payment_date = fields.Date()
    description = fields.Char()
    fine_threshold = fields.Integer(string="Fine Threshold")

    ar_balance_previous = fields.Monetary(currency_field='currency_id',
                                          string="Previous Ar Balance", default=0.0)
    ar_balance = fields.Monetary(string="AR Balance", default=0.0, digits=(
        12, 5), compute='_compute_ar_balance')
    re_installment_id = fields.Many2one('re.installment.plan')
    currency_id = fields.Many2one('res.currency', related="sale_id.currency_id")

    @api.depends('ar_balance_previous', 'fine_current_period', 'fine_discount', 'interest_discount', 'paid_amount')
    def _compute_ar_balance(self):
        for record in self:
            if record.ar_balance_previous > 0.0:
                ar_balance = record.paid_amount
                # ar_balance = record.paid_currency_id._convert(record.partial_paid_amount, record.invoice_currency_id,
                #                                               record.env.company, record.payment_date)
                record.ar_balance = record.ar_balance_previous + record.fine_current_period - \
                                    record.fine_discount - record.interest_discount - ar_balance
            else:
                record.ar_balance = 0.0

    @api.depends('total_remaining_amount', 'interest_rate', 'without_interest_amount', 'interest_amount', 'amount',
                 'each_period_ar_amount')
    def _compute_for_view(self):
        for line in self:
            line.total_remaining_amount_view = round(
                line.total_remaining_amount) if line.total_remaining_amount else 0
            line.interest_rate_view = round(
                line.interest_rate) if line.interest_rate else 0
            line.without_interest_amount_view = round(
                line.without_interest_amount) if line.without_interest_amount else 0
            line.interest_amount_view = round(
                line.interest_amount) if line.interest_amount else 0
            line.amount_view = round(line.amount) if line.amount else 0
            line.each_period_ar_amount_view = round(
                line.each_period_ar_amount) if line.each_period_ar_amount else 0

    @api.depends('without_interest_amount', 'interest_amount')
    def _compute_each_period_ar_amount(self):
        for record in self:
            record.each_period_ar_amount = record.without_interest_amount + record.interest_amount

    @api.depends('without_interest_amount', 'interest_amount', 'due_amount')
    def _compute_amount(self):
        for record in self:
            record.amount = record.without_interest_amount + \
                            record.interest_amount + record.due_amount


class InvoiceInstallmentLine(models.Model):
    _name = 'invoice.installment.line'
    _description = 'Invoice Installment Line'
    _order = 'payment_date'
    _rec_name = 'description'

    state = fields.Selection([
        ('draft', 'Future Due'),
        ('current_due', 'Current Due'),
        ('follow_up', 'Follow Up'),
        ('remind', 'Remind'),
        ('need_action', 'Need Action'),
        ('take_action', 'Take Action'),
        ('paid', 'Paid'),
        ('skip', 'Skip Payment'),
    ], default='draft', string="Status", compute="_compute_state")
    is_active = fields.Boolean(string="Active", default=False)
    total_remaining_amount = fields.Monetary(currency_field='invoice_currency_id',
                                             string="Remaing AR Balance", default=0.0, readonly=True)
    interest_rate = fields.Monetary(currency_field='invoice_currency_id',
                                    string="Interest Rate(%)", default=0.0, readonly=True)
    without_interest_amount = fields.Monetary(currency_field='invoice_currency_id',
                                              string="Amount(Without Interest)", default=0.0, readonly=True)
    interest_amount = fields.Monetary(currency_field='invoice_currency_id',
                                      string="Interest Amount", default=0.0, readonly=True)
    due_amount = fields.Monetary(currency_field='invoice_currency_id',
                                 string="Due Amount", default=0.0, readonly=True)
    fine_current_period = fields.Monetary(currency_field='invoice_currency_id',
                                          string="Fine(Current Peroid)", default=0.0, readonly=False)
    fine_previous_period = fields.Monetary(currency_field='invoice_currency_id',
                                           string="Fine(Previous Peroid)", default=0.0, readonly=False)
    fine_discount = fields.Monetary(currency_field='invoice_currency_id', string="Fine Discount", default=0.0, digits=(
        12, 2), readonly=True, states={'current_due': [('readonly', False)]})
    fine_discount_approval = fields.Selection([
        ('draft', 'Draft'),
        ('cfd_approved', 'CFD Approved')
    ], string="Fine Discount State", default='draft', readonly=True)
    interest_discount = fields.Monetary(currency_field='invoice_currency_id', string="Interest Discount", default=0.0,
                                        digits=(
                                            12, 2), readonly=True, states={'current_due': [('readonly', False)]})
    interest_discount_approval = fields.Selection([
        ('draft', 'Draft'),
        ('cfd_approved', 'CFD Approved')
    ], default='draft', readonly=True)
    fine_amount = fields.Monetary(currency_field='invoice_currency_id', string="Fine Amount",
                                  compute="_compute_fine_amount", readonly=True)
    amount = fields.Monetary(currency_field='invoice_currency_id', string="Amount", digits=(
        12, 2), compute="_compute_amount", readonly=True)
    each_period_ar_amount = fields.Monetary(currency_field='invoice_currency_id',
                                            compute="_compute_each_period_ar_amount", string="Each Period Ar Amount",
                                            readonly=True)
    paid_amount = fields.Monetary(currency_field='invoice_currency_id',
                                  string="Paid Amount", readonly=True)
    fine_paid = fields.Monetary(currency_field='invoice_currency_id',
                                string="Fine Paid(Auto depend on Paid)", readonly=True)
    principal_paid = fields.Monetary(currency_field='invoice_currency_id',
                                     string="Principal Paid(Auto depend on Paid)", readonly=True)
    fine_rate = fields.Monetary(currency_field='invoice_currency_id', string="Fine Rate", default=0.0, readonly=True)
    index = fields.Integer(string="#No", readonly=True)
    invoice_id = fields.Many2one('account.move', 'Invoice', ondelete="cascade")
    payment_id = fields.Many2one('account.payment', "Payment")
    sale_id = fields.Many2one('sale.order', 'Sale Order', ondelete="cascade")
    payment_start_date = fields.Date(readonly=True)
    payment_end_date = fields.Date(readonly=True)
    payment_date = fields.Date(readonly=True)
    description = fields.Char(readonly=True)
    paid = fields.Boolean()
    skip_paid = fields.Boolean()

    invoice_currency_id = fields.Many2one(
        related="invoice_id.currency_id", string="Invoice Currency")
    paid_currency_id = fields.Many2one('res.currency', string="Paid Currency")

    rv_date = fields.Char(string="RV Date", readonly=True)
    rv_no = fields.Char(string="RV No.", readonly=True)

    sinst_line_id = fields.Many2one(
        'sale.installment.line', 'Sale Installment Line')
    is_fine_calculated = fields.Boolean(
        string="Fine Calculated", default=False)

    ar_balance_previous = fields.Monetary(currency_field='invoice_currency_id',
                                          string="Ar Balance Previous", default=0.0)
    ar_balance = fields.Monetary(currency_field='invoice_currency_id', string="AR Balance",
                                 compute="_compute_ar_balance")

    fine_threshold = fields.Integer(string="Fine Threshold")

    partial_paid_amount = fields.Monetary(currency_field='invoice_currency_id',
                                          string="Partial Paid Amount", readonly=True)

    def action_fine_discount_cfd_approved(self):
        for rec in self:
            if rec.fine_discount and rec.state == 'current_due' and rec.fine_discount_approval == 'draft':
                rec.fine_discount_approval = 'cfd_approved'
                rec._compute_ar_balance()
                rec._compute_amount()
            else:
                raise ValidationError(_('Fine Discount Amount should not be ZERO.'))

    def action_interest_discount_cfd_approved(self):
        for rec in self:
            if rec.interest_discount and rec.state == 'current_due' and rec.interest_discount_approval == 'draft':
                rec.interest_discount_approval = 'cfd_approved'
                rec._compute_ar_balance()
                rec._compute_amount()
            else:
                raise ValidationError(_('Interest Discount Amount should not be ZERO.'))

    def action_rv_numbers(self):
        if self.rv_no:
            action = self.env.ref('account.action_account_payments').read()[0]
            # print(f"===>{self.rv_no.split(',')}",action.get('doamin'))
            action['domain'] = [('name', 'in', self.rv_no.split(','))]
            # action['target'] = 'new'
            return action

    def _compute_state(self):
        for line in self:

            if line.paid or line.amount == line.partial_paid_amount or line.amount == line.paid_amount:
                line.state = 'paid'
                return True

            if line.skip_paid:
                line.state = 'skip'
                return True

            today = line.invoice_id.payment_term_date  # date.today()
            # today = date.today()
            if line.state not in ['paid', 'take_action', 'current_due']:

                # if today < line.payment_date:
                #     delta = line.payment_date - today
                #     if delta.days <= 7:
                #         line.state = 'follow_up'
                # else:
                next_month = line.payment_date + relativedelta(months=1)
                two_month = line.payment_date + relativedelta(months=2)
                delta = today - line.payment_date
                if delta.days >= 7 and today < next_month:
                    line.state = 'remind'
                elif next_month <= today < two_month:
                    line.state = 'need_action'
                elif today >= two_month:
                    line.state = 'take_action'
                    # line.skip_payment(context=None)
                if line.payment_start_date <= today <= line.payment_end_date:
                    # print(line.state, "(((*" * 10)
                    previous_due_state = line.invoice_id.installment_ids.filtered(lambda x: x.index == line.index - 1)
                    if previous_due_state.state != 'current_due':
                        line.state = 'current_due'
                        # today = line.invoice_id.payment_term_date  # date.today()
                        # if today > line.payment_date + relativedelta(days=line.invoice_id.fine_threshold):
                        #     # if line.index == 1:
                        #         amount = line.each_period_ar_amount + line.due_amount
                        #         amount = amount * (line.fine_rate / 100)
                        #         line.update({
                        #             'fine_current_period': amount,
                        #             'fine_amount': amount + line.fine_previous_period,
                        #             'amount': amount + line.fine_previous_period + line.each_period_ar_amount + line.due_amount
                        #         })
                        line.is_active = True
                        line.installment_fine_calculator()
                        line.installment_fine_tester()
                        # print("*"*100)
                        # print(line.amount,round(line.amount,2),line.paid_amount)
                        if round(line.amount, 2) == line.paid_amount:
                            line.state = 'paid'
                            line.paid = True
                            line.skip_payment(context=None)

                    # if
                    # if line.state == 'paid':
                    #     next_due_state = line.invoice_id.installment_ids.filtered(
                    #         lambda x: x.index == line.index + 1)
                    #     next_due_state.state = 'current_due'
            # previous_due_state = line.invoice_id.installment_ids.filtered(lambda x: x.index == line.index - 1)
            if not line.state:
                # if previous_due_state.state not in ['draft', 'current_due']:
                #     #     print(previous_due_state.state)
                #     line.state = 'current_due'
                #     line.is_active = True
                #     line.installment_fine_calculator()
                #     # today = line.invoice_id.payment_term_date  # date.today()
                #     # if today > line.payment_date + relativedelta(days=line.invoice_id.fine_threshold):
                #     #     if line.index == 1:
                #     #         amount = line.each_period_ar_amount + line.due_amount
                #     #         amount = amount * (line.fine_rate / 100)
                #     #         line.update({
                #     #             'fine_current_period': amount,
                #     #             'fine_amount': amount + line.fine_previous_period,
                #     #             'amount': amount + line.fine_previous_period + line.each_period_ar_amount + line.due_amount
                #     #         })
                #     # line.is_active = True
                #     line.installment_fine_tester()
                # else:
                line.state = 'draft'
            else:
                line.skip_payment(context=None)

    @api.depends('ar_balance_previous', 'fine_current_period', 'fine_discount', 'interest_discount', 'paid_amount')
    def _compute_ar_balance(self):
        for record in self:
            if record.ar_balance_previous > 0.0:
                ar_balance = record.paid_amount
                # ar_balance = record.paid_currency_id._convert(
                #     record.paid_amount, record.invoice_currency_id, record.env.company, record.payment_date)
                record.ar_balance = record.ar_balance_previous + record.fine_current_period - ar_balance
                if record.fine_discount_approval == 'cfd_approved':
                    record.ar_balance -= record.fine_discount
                if record.interest_discount_approval == 'cfd_approved':
                    record.ar_balance -= record.interest_discount
            else:
                record.ar_balance = 0.0

    @api.depends('without_interest_amount', 'interest_amount')
    def _compute_each_period_ar_amount(self):
        for record in self:
            record.each_period_ar_amount = record.without_interest_amount + record.interest_amount

    @api.depends('without_interest_amount', 'interest_amount', 'due_amount', 'fine_amount', 'fine_discount',
                 'interest_discount')
    def _compute_amount(self):
        for record in self:
            record.amount = record.without_interest_amount + record.interest_amount + \
                            record.due_amount + record.fine_amount
            if record.fine_discount_approval == 'cfd_approved':
                record.amount -= record.fine_discount
            if record.interest_discount_approval == 'cfd_approved':
                record.amount -= record.interest_discount

    @api.depends('fine_current_period', 'fine_previous_period')
    def _compute_fine_amount(self):
        for record in self:
            record.fine_amount = record.fine_current_period + record.fine_previous_period

    def print_invoice(self):
        return self.env.ref('account.action_report_payment_receipt').report_action(self.payment_id.id)

    def action_register_payment(self):
        ''' Open the account.payment.register wizard to pay the selected journal entries.
        :return: An action opening the account.payment.register wizard.
        '''
        amount = self.invoice_id.currency_id._convert(
            self.amount, self.env.company.currency_id, self.env.company, self.payment_date)
        paid_amount = self.invoice_id.currency_id._convert(
            self.paid_amount, self.env.company.currency_id, self.env.company, self.payment_date)
        partial_paid_amount = self.invoice_id.currency_id._convert(
            self.paid_amount, self.env.company.currency_id, self.env.company, self.payment_date)
        # amount = self.invoice_id.company_id.currency_id._convert(self.amount, self.env.company.currency_id, self.env.company,self.payment_date)

        return {
            'name': _('Register Payment'),
            'res_model': 'account.payment.register',
            'view_mode': 'form',
            'context': {
                'active_model': 'account.move',
                'active_ids': self.invoice_id.ids,
                'active_id': self.invoice_id.id,
                # 'default_amount': amount - partial_paid_amount,
                'default_installment_origin_amount': self.amount - self.paid_amount,
                'default_is_installment': True,
                'default_hr_bu_id': self.invoice_id.hr_bu_id.id,
                'default_hr_br_id': self.invoice_id.hr_br_id.id,
                'default_ref': self.invoice_id.name,
                'default_fine_amount': self.fine_amount - (
                            self.fine_paid + self.fine_discount) if self.fine_discount_approval == 'cfd_approved' else self.fine_amount - self.fine_paid,
                'default_interest_discount_amount': self.interest_discount if self.interest_discount_approval == 'cfd_approved' else 0.0,
                'installment_id': self.id,
                'installment_obj': self,
                # 'default_fine_amount':self.fine_amount,

                # 'invoice_installment_id':self.id,

            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    # def make_payment(self):
    #     #amount = self.env['account.payment']._compute_payment_amount(self.invoice_id,self.invoice_id.currency_id,self.invoice_id.journal_id,self.payment_date)
    #     amount = self.invoice_id.currency_id._convert(self.amount,self.env.company.currency_id,self.env.company,self.payment_date)
    #     return self.env['account.payment']\
    #         .with_context(active_ids=self.invoice_id.ids,
    #          active_model='account.move',
    #           active_id=self.invoice_id.id,
    #           line_model='invoice.installment.line',
    #           line_id=self.id,default_currency_id=self.invoice_id.currency_id.id,
    #           default_amount=amount, default_installment_origin_amount=self.amount ,
    #           default_is_installment=True,
    #           default_hr_bu_id=self.invoice_id.hr_bu_id.id,default_hr_br_id=self.invoice_id.hr_br_id.id,
    #           default_ref=self.invoice_id.name,
    #           default_partner_id=self.invoice_id.partner_id.id,
    #           default_payment_type='inbound',
    #           default_partner_type= 'customer',
    #           default_move_journal_types = ('bank', 'cash'))\
    #          .action_register_payment()

    def skip_payment(self, context='skip'):
        # self.installment_fine_calculator()
        # self.installment_fine_tester()
        line = self
        # line.state = 'paid'
        # line.sinst_line_id.state = 'paid'
        if context == 'skip':
            # line.installment_fine_tester()
            line.state = 'skip'
            line.skip_paid = True
        # else:
        # if line.index == 1:
        #     line.installment_fine_tester()
        # line.update({'paid_amount': 0.0})
        current = line
        line_installment = self.invoice_id.installment_ids.filtered(
            lambda x: x.index != 0)
        for line in line_installment:
            line.update({'index': line.index})

        paid_fine = 0.0

        today = fields.Datetime.today()
        dd = today.strftime("%d-%b-%y").split('-')

        if len(dd) == 3:
            current.update({
                'rv_date': dd[1]
            })

        today = current.invoice_id.payment_term_date  # date.today()
        if today > current.payment_date + relativedelta(days=current.invoice_id.fine_threshold):
            amount = current.each_period_ar_amount + current.due_amount
            amount = amount * (current.fine_rate / 100)
            # print(amount,"installment_fine_calculator")
            fine_counter, i = current.payment_date + relativedelta(
                    days=current.invoice_id.fine_threshold), 0
            while today > fine_counter:
                i += 1;
                # print(i, today, "fine counter ==> ", fine_counter, rec.payment_date)
                fine_counter = fine_counter + relativedelta(months=1)
            # print(amount, amount * i, "*" * 10, i)
            amount = amount * i
            # print(amount)
            # print("&" * 10)
            current.update({
                'fine_current_period': amount,
                'fine_amount': amount + current.fine_previous_period,
                'amount': amount + current.fine_previous_period + current.each_period_ar_amount + current.due_amount
            })
        line.installment_fine_calculator()
        line.installment_fine_tester()

        current.update({
            'is_active': False,
        })
        # a = False
        # if a:
        for nex in line_installment:
            if nex.index > current.index:
                # nex.update({
                #         'total_remaining_amount':current.total_remaining_amount - line.amount
                #     })
                if nex.index > 1:

                    if nex.index == current.index + 1:
                        due_amount = 0.0
                        fine_amount = 0.0
                        if 0.0 != current.amount:
                            # due_amount = current.amount - current.fine_amount - current.principal_paid
                            # due_amount = current.amount - current.paid_amount# - current.fine_amount
                            interest_discount = current.interest_discount if current.interest_discount_approval == 'cfd_approved' else 0.0
                            due_amount = (
                                                     current.each_period_ar_amount + current.due_amount) - current.principal_paid - interest_discount
                            if due_amount < 0:
                                due_amount = 0

                        fine_rate = nex.fine_rate
                        fine_amount = due_amount * (fine_rate / 100)
                        _amount = nex.without_interest_amount + \
                                  nex.interest_amount + due_amount + fine_amount
                        if context == 'skip':
                            nex.update({'state': 'current_due'})
                        # print("previous fine =>",current.fine_amount - current.fine_paid,current.index)
                        today = nex.invoice_id.payment_term_date
                        # print("today ==> ",today)
                        # print("payment_end_date"nex.payment_end_date)
                        if today > current.payment_end_date:
                        # if today > nex.payment_date + relativedelta(days=rec.invoice_id.fine_threshold)
                            nex.update({
                                'fine_previous_period': current.fine_amount - current.fine_paid - current.fine_discount if current.fine_discount_approval == 'cfd_approved' else current.fine_amount - current.fine_paid,
                                'due_amount': due_amount,
                                'amount': _amount,
                                'is_active': True,
                                'ar_balance_previous': current.ar_balance
                            })
                            # nex.update({
                                # 'fine_previous_period': current.fine_amount - current.fine_paid- current.fine_discount if current.fine_discount_approval == 'cfd_approved' else current.fine_amount - current.fine_paid,
                                # 'due_amount': due_amount,
                                # 'amount': _amount,
                                # 'is_active': True,
                                # 'ar_balance_previous': current.ar_balance,
                            # })

                            nex.installment_fine_calculator()

                            nex.sinst_line_id.update({
                                'due_amount': due_amount,
                                'fine_previous_period': current.fine_amount - paid_fine - current.fine_discount if current.fine_discount_approval == 'cfd+approved' else current.fine_amount - paid_fine,
                                'fine_amount': fine_amount,
                                'amount': _amount,
                            })
                if nex.index == 1:
                    nex.update({
                        'is_active': True
                    })

        current.sinst_line_id.update({
            'due_amount': current.due_amount,
            'fine_amount': current.fine_amount,
            'fine_previous_period': current.fine_previous_period,
            'fine_current_period': current.fine_current_period,
            'paid_amount': current.paid_amount,
            'fine_paid': current.fine_paid,
            'principal_paid': current.principal_paid,
            'ar_balance': current.ar_balance,
            'rv_date': current.rv_date,

        })

    def installment_fine_tester(self):
        records = self.search([('is_active', '=', True)])
        for rec in records:
            today = rec.invoice_id.payment_term_date  # date.today()
            if today > rec.payment_date + relativedelta(days=rec.invoice_id.fine_threshold):
                amount = rec.each_period_ar_amount + rec.due_amount
                amount = amount * (rec.fine_rate / 100)
                # print(amount,"installment_fine_calculator")
                fine_counter, i = rec.payment_date + relativedelta(
                        days=rec.invoice_id.fine_threshold), 0
                while today > fine_counter:
                    i += 1;
                    # print(i, today, "fine counter ==> ", fine_counter, rec.payment_date)
                    fine_counter = fine_counter + relativedelta(months=1)
                # print(amount, amount * i, "*" * 10, i)
                amount = amount * i
                # print(amount)
                # print("&" * 10)
                rec.update({
                    'fine_current_period': amount,
                    'fine_amount': amount + rec.fine_previous_period,
                    'amount': amount + rec.fine_previous_period + rec.each_period_ar_amount + rec.due_amount
                })
                rec._compute_ar_balance()

    def _compute_fine_current_amount(self):
        for rec in self:
            today = rec.invoice_id.payment_term_date  # date.today()
            if today > rec.payment_date + relativedelta(days=rec.invocie_id.fine_threshold):
                amount = rec.each_period_ar_amount + rec.due_amount
                amount = amount * (rec.fine_rate / 100)
                # print(amount,"_compute_fine_current_amount")
                # print(amount,"installment_fine_calculator")
                fine_counter, i = rec.payment_date+ relativedelta(
                        days=rec.invoice_id.fine_threshold), 0
                while today > fine_counter:
                    i += 1;
                    # print(i, today, "fine counter ==> ", fine_counter, rec.payment_date)
                    fine_counter = fine_counter + relativedelta(months=1)
                # print(amount, amount * i, "*" * 10, i)
                amount = amount * i
                # print(amount)
                # print("&" * 10)
                rec.update({
                    'fine_current_period': amount,
                    'fine_amount': amount + rec.fine_previous_period,
                    'amount': amount + rec.fine_previous_period + rec.each_period_ar_amount + rec.due_amount
                })
                rec._compute_ar_balance()

    @api.model
    def installment_fine_calculator_tester(self):
        records = self.search([('is_active', '=', True)])
        for rec in records:
            today = rec.invoice_id.payment_term_date  # date.today()
            if today > rec.payment_date + relativedelta(days=rec.invoice_id.fine_threshold):
                amount = rec.each_period_ar_amount + rec.due_amount
                amount = amount * (rec.fine_rate / 100)
                # print(amount,"installment_fine_calculator_tester")
                # print(amount,"installment_fine_calculator")
                fine_counter, i = rec.payment_date + relativedelta(
                        days=rec.invoice_id.fine_threshold), 0
                while today > fine_counter:
                    i += 1;
                    # print(i, today, "fine counter ==> ", fine_counter, rec.payment_date)
                    fine_counter = fine_counter + relativedelta(months=1)
                # print(amount, amount * i, "*" * 10, i)
                amount = amount * i
                # print(amount)
                # print("&" * 10)
                rec.update({
                    'fine_current_period': amount,
                    'fine_amount': amount + rec.fine_previous_period,
                    'amount': amount + rec.fine_previous_period + rec.each_period_ar_amount + rec.due_amount
                })
                rec._compute_ar_balance()

    @api.model
    def installment_fine_calculator(self):
        records = self.search([('is_active', '=', True)])
        for rec in records:
            today = rec.invoice_id.payment_term_date  # date.today()
            if today > rec.payment_date + relativedelta(days=rec.invoice_id.fine_threshold):

                # if not rec.is_fine_calculated:
                    amount = rec.each_period_ar_amount + rec.due_amount
                    amount = amount * (rec.fine_rate / 100)
                    # print(amount,"installment_fine_calculator")
                    fine_counter, i = rec.payment_date + relativedelta(
                            days=rec.invoice_id.fine_threshold), 0
                    while today > fine_counter:
                        i += 1;
                        # print(i, today, "fine counter ==> ", fine_counter, rec.payment_date)
                        fine_counter = fine_counter + relativedelta(months=1)
                    # print(amount, amount * i, "*" * 10, i)
                    amount = amount * i
                    # print(amount)
                    # print("&" * 10)
                    rec.update({
                        'fine_current_period': amount,
                        'fine_amount': amount + rec.fine_previous_period,
                        'amount': amount + rec.fine_previous_period + rec.each_period_ar_amount + rec.due_amount
                    })

                # next_month = rec.payment_date + relativedelta(months=1)
                # if today >= next_month:
                #   rec.update({
                #           'is_active':False,
                #       })
                #   next_payments = self.env['invoice.installment.line'].search([('invoice_id','=',rec.invoice_id.id)])

                #   for nex in next_payments:
                #       if nex.index == rec.index + 1:
                #           nex.update({
                #                   'is_active':True
                #               })

        # records = self.search([('state','not in',['paid','take_action'])])
        # for rec in records:
        #   today = date.today()

        #   if today < rec.payment_date:
        #       delta = rec.payment_date - today
        #       if delta.days <= 7:
        #           rec.update({
        #                   'state':'follow_up',
        #               })
        #   else:
        #       next_month = rec.payment_date + relativedelta(months=1)
        #       two_month = rec.payment_date + relativedelta(months=2)
        #       delta = today - rec.payment_date
        #       if delta.days >= 7 and today < next_month:
        #           rec.update({
        #                   'state':'remind'
        #               })
        #       elif today >= next_month and today < two_month:
        #           rec.update({
        #                   'state':'need_action'
        #               })
        #       elif today >= two_month:
        #           rec.update({
        #                   'state':'take_action'
        #               })

    # @api.model
    # def installment_reminder(self):
    #     tommorow = fields.Datetime.today() + relativedelta(days=1)
    #     day_after_tommorow = fields.Datetime.today() + relativedelta(days=2)
    #     records = self.search([('invoice_id.state', '=', 'posted'), '|', (
    #         'payment_date', '=', tommorow), ('payment_date', '=', day_after_tommorow)])
    #     for rec in records:
    #         template = self.env.ref(
    #             'payment_installment_kanak.mail_template_installment_reminder')
    #         template.send_mail(rec.id, force_send=False)
    #
    def open_line_form(self):

        self.ensure_one()
        return {
            'name': _('Installment Data'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'invoice.installment.line',
            'res_id': self.id,
            'context': {'create': False, 'edit': False},
        }
