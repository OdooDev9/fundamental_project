import datetime

from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _


class RequestQuotation(models.Model):
    _inherit = 'request.quotation'

    installment_plan_id = fields.Many2one(
        'installment.plan', string="Installment Plan", domain=[('state', '=', 'approved_finance')])
    installment_ids = fields.One2many(
        'request.quotation.installment.line', 'request_quotation_id', 'Installments')
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
        # print("self.in.sefe.wefefe.......",self.installment_plan_id.tenure)
        record = self
        if record.installment_plan_id:
                record.tenure = record.installment_plan_id.tenure
                # print("*"*10)
                # print(record.installment_plan_id.tenure,"tenure")
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
            #
            # for line in self.order_line:
            #     if line.is_interest:
            #         amount_untaxed -= line.price_subtotal

            record.tenure_amount_untaxed = amount_untaxed

    #
    @api.depends("amount_total")
    def _compute_tenure_amt(self):
        for record in self:
            amount_total = record.amount_total
            # for line in self.order_line:
            #     if line.is_interest:
            #         amount_total -= line.price_total
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
            self.installment_amt = self.payable_amt / self.installment_amt
            # self.with_context({'installment_amt': self.installment_amt}
            #                   ).tenure = self.payable_amt / self.installment_amt

    @api.depends("tenure", "payable_amt")
    def _compute_installment_amt(self):
        for record in self:
            value = 0.0
            if record.tenure:
                if record.payment_circle_count > 0.0:
                    value = record.payable_amt / \
                            (record.tenure / record.payment_circle_count)
            record.installment_amt = value

    @api.depends("down_payment_amt")
    def _compute_payable_amt(self):
        for record in self:
            value = 0.0
            if record.tenure_amt:
                value = record.tenure_amt - record.down_payment_amt
            record.payable_amt = value

    @api.depends('req_quotation_line', 'installment_plan_id')
    def compute_installment(self):
        # if self.installment_ids:
        #     self.installment_ids.unlink()
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
        # order_line_id = self.order_line.filtered(
        #     lambda x: x.product_id == interest_product)
        # if order_line_id:
        #     order_line_id.price_unit = total_interest
        # else:
        # if total_interest:
        #         sol = self.env['sale.order.line'].create({
        #             'product_id': interest_product.id,
        #             'order_id': self.id,
        #             'name': interest_product.product_tmpl_id.name,
        #             'product_uom_qty': 1.0,
        #             'product_uom': interest_product.product_tmpl_id.uom_id.id,
        #             'price_unit': total_interest,
        #             'is_interest': True,
        #         })

    @api.model
    def create(self, vals):
        result = super(RequestQuotation, self).create(vals)
        result.compute_installment()
        return result

    def write(self, values):
        result = super(RequestQuotation, self).write(values)
        print("values ==> ", values)
        if 'installment_plan_id' in values or 'req_quotation_line' in values:
            self.compute_installment()
        return result

    def action_installment_modify(self):
        self.ensure_one()
        new_wizard = self.env['request.quotation.modify.installment'].create({
            'name': self.name,
            'quotation_id': self.id,
        })
        new_wizard.onchange_quotation_id()
        return {
            'name': _('Modify Installment'),
            'view_mode': 'form',
            'res_model': 'request.quotation.modify.installment',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': new_wizard.id,
            'context': self.env.context,
        }

    def _create_sale_order(self):
        request = super(RequestQuotation, self)._create_sale_order()
        request.write({
            'installment_plan_id': self.installment_plan_id.id,
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
            'fine_discount': self.fine_discount
        })
        # request._onchange_installment_plan_id()
        request.compute_installment()
        # print("DAKSMD\n"*10)
        return request


class RequestQuotationInstallmentLine(models.Model):
    _name = 'request.quotation.installment.line'
    _inherit = 'sale.installment.line'

    request_quotation_id = fields.Many2one('request.quotation')
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
