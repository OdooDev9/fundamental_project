import datetime

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


class AccountMove(models.Model):
    _inherit = "account.move"

    installment_ids = fields.One2many('invoice.installment.line', 'invoice_id', 'Installments')

    down_payment_amt = fields.Monetary(currency_field='currency_id', string="Down Payment", readonly=True,
                                       states={'draft': [('readonly', False)]})
    second_payment_date = fields.Date(readonly=True, states={'draft': [('readonly', False)]})

    installment_amt = fields.Monetary(currency_field='currency_id', string="Installment Amount",
                                      states={'draft': [('readonly', False)]})
    payable_amt = fields.Monetary(currency_field='currency_id', string="Payable Amount", readonly=True,
                                  states={'draft': [('readonly', False)]})
    tenure = fields.Integer(string="Tenure", states={'draft': [('readonly', False)]})
    payment_circle_count = fields.Integer(string="Payment Every (Month)", readonly=True)
    fine_threshold = fields.Integer(string="Fine Threshold", help="To start fine calculation!")
    tenure_type = fields.Selection([
        ('month', 'months'),
    ], string="Tenure Type", default="month", required=True)

    tenure_amt = fields.Monetary(currency_field='currency_id', string="Sale Amount")
    tenure_amount_untaxed = fields.Monetary(currency_field='currency_id', string="Untaxed Amount")
    tenure_amount_tax = fields.Monetary(currency_field='currency_id', string="Taxes")

    down_payment_type = fields.Selection([
        ('percent', 'Percentage(%)'),
        ('fix', 'Fixed')
    ], string="Down Payment Type", required=False, readonly=True, states={'draft': [('readonly', False)]},
        default="percent")

    down_payment_percent = fields.Float(string="Down Payment(%)", default=0.0, readonly=True,
                                        states={'draft': [('readonly', False)]})
    down_payment_fixed = fields.Float(string="Down Payment(Fixed)", default=0.0, readonly=True,
                                      states={'draft': [('readonly', False)]})

    interest_rate = fields.Float(string="Interest Rate(%)", default=0.0, required=True)
    interest_start_from = fields.Integer(string="Interest Start From", default=1, help="Interest Start Index")
    fine_rate = fields.Float(string="Fine Rate(%)", default=0.0, required=True)
    fine_discount = fields.Monetary(currency_field='currency_id', string="Fine Discount")

    start_invoice_date = fields.Date(string="Start Invoice Date", required=True, readonly=True,
                                     states={'draft': [('readonly', False)]}, default=fields.Datetime.now)
    contract_date = fields.Date(string="Contract Date", required=True, readonly=True,
                                states={'draft': [('readonly', False)]}, default=fields.Datetime.now)

    compute_installment = fields.Char(string="Compute")
    sale_installment = fields.Boolean(string="Sale Installment")
    part_payment = fields.Char(string="Part Payment")

    # installment_amt = fields.Float(string="Installment Amount", readonly=True, states={'draft': [('readonly', False)]})

    installment_plan_id = fields.Many2one('installment.plan', string="Installment Plan")

    fine_to_date = fields.Monetary(string="Fine To Date", compute="_compute_to_date")

    payment_to_date = fields.Monetary(string="Payment To Date", compute="_compute_to_date")

    discount_to_date = fields.Monetary(string="Discount", compute="_compute_to_date")

    current_amount = fields.Monetary(string="Current Amount", compute="_compute_current_overdue")

    current_overdue = fields.Monetary(string="Current Due", compute="_compute_current_overdue")

    current_fine = fields.Monetary(string="Current Fine", compute="_compute_current_overdue")
    period_amount = fields.Monetary(string="Peroid Amount", compute="_compute_current_overdue")

    future_due_amount = fields.Monetary(string="Future Due Amount", compute="_compute_current_overdue")
    payment_term_date = fields.Date(default=datetime.date.today())

    @api.depends('installment_ids')
    def _compute_current_overdue(self):
        for record in self:
            current = 0.0
            amount = 0.0
            fine = 0.0
            p_amount = 0.0
            future_due = 0.0
            active_index = 0
            for line in record.installment_ids:
                if line.is_active:
                    current = line.due_amount
                    amount = line.each_period_ar_amount
                    fine = line.fine_amount
                    p_amount = line.amount
                    active_index = line.index
                    break

            if active_index > 0:
                for line in record.installment_ids:
                    if line.index == active_index + 1:
                        future_due = line.each_period_ar_amount
                        break
            else:
                for line in record.installment_ids:
                    if line.index == 1:
                        future_due = line.each_period_ar_amount
                        break

            record.current_overdue = current
            record.current_amount = amount
            record.current_fine = fine
            record.period_amount = p_amount
            record.future_due_amount = future_due

    @api.depends('installment_ids')
    def _compute_to_date(self):
        for record in self:
            fine = 0.0
            payment = 0.0
            discount = 0.0
            for line in record.installment_ids:
                if line.fine_amount > 0.0:
                    fine += line.fine_amount
                if line.paid_amount > 0.0:
                    payment += line.paid_amount
                if line.fine_discount > 0.0:
                    discount += line.fine_discount
                if line.interest_discount > 0.0:
                    discount += line.interest_discount

            record.fine_to_date = fine
            record.payment_to_date = payment
            record.discount_to_date = discount

    @api.depends("amount_total")
    def _compute_tenure_amt(self):
        for record in self:
            record.tenure_amt = record.amount_total

    def compute_installment(self):
        total_interest = 0.0
        for order in self:
            amount_total = order.amount_residual
            tenure = order.tenure
            installment_ids = []
            if order.installment_amt:
                index = 1
                if order.amount_residual:
                    installment_ids = []
                    interest_rate = order.interest_rate
                    # payment_start_date =
                    while tenure > 0:
                        index = 1
                        interest_start = order.interest_start_from
                        payment_date = order.second_payment_date or date.today()
                        total_remaining_amount = order.tenure_amt - order.down_payment_amt
                        interest_amount = 0.0
                        installment_ids = [(2, line_id.id, False) for line_id in self.installment_ids]
                        ar_balance = 0.0
                        payment_start_date = order.start_invoice_date #order.contract_date
                        while tenure > 0:
                            if index >= interest_start:
                                interest_amount = total_remaining_amount * (interest_rate / 100)
                            # print("==>", index, payment_date, payment_start_date)
                            # payment_start_date = payment_date + timedelta(days=1)
                            payment_end_date = payment_date + relativedelta(months=order.payment_circle_count)
                            installment_ids.append((0, 0, {
                                'index': index,
                                'without_interest_amount': order.installment_amt,
                                'interest_rate': interest_rate,
                                'interest_amount': interest_amount,
                                'total_remaining_amount': total_remaining_amount,
                                'payment_date': payment_date,
                                'payment_start_date': payment_start_date,
                                'payment_end_date': payment_end_date,
                                'fine_rate': order.fine_rate,
                                'description': '%s installment' % index,
                            }))
                            payment_start_date = payment_date + timedelta(days=1)

                            # ar_balance += interest_amount
                            total_interest += interest_amount
                            total_remaining_amount = total_remaining_amount - order.installment_amt
                            index += 1
                            tenure -= order.payment_circle_count
                            payment_date += relativedelta(months=order.payment_circle_count)
                            amount_total -= order.installment_amt
                    last_month = order.tenure / order.payment_circle_count
                    latest_installment_amt = order.installment_amt * (last_month - 1)
                    latest_without_interest_amt = order.payable_amt - latest_installment_amt

                    last_obj = installment_ids[-1][-1]
                    last_obj['without_interest_amount'] = latest_without_interest_amt
                if installment_ids:
                    ar_balance += order.payable_amt + total_interest

                    installment_ids[0][2]['is_active'] = True
                    installment_ids[0][2]['ar_balance_previous'] = ar_balance
                    order.installment_ids = installment_ids
            interest_product = self.env['product.product'].search([('name', '=', 'Interest'), ('type', '=', 'service'),
                                                                   ('business_id', '=', self.hr_bu_id.id)])
            order_line_id = self.invoice_line_ids.filtered(lambda x: x.product_id == interest_product)
            if order_line_id:
                order_line_id.price_unit = total_interest


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    is_fine_line = fields.Boolean(default=False)
