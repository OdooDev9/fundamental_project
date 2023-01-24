from odoo import api, models, fields, _
from ast import literal_eval
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class BrokerFeesWizard(models.TransientModel):
    _name = 'broker.fees.wizard'
    _description = 'Broker Fees Wizard'

    partner_id = fields.Many2one('res.partner', string='Broker')
    payment_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed_amount', 'Fixed Amount'),
    ], default='percentage', string='Payment')
    fixed_amount = fields.Float(
        string="Fixed Amount", help="Fixed amount.")
    fixed_percentage = fields.Float(string="Fixed Percentage")
    product_id = fields.Many2one('product.product', string='Product',
                                 domain="[('detailed_type', '=', 'service'),('business_id', '=', hr_bu_id)]")
    quote_name = fields.Many2one('sale.order', string="Sale Order")
    total_amount = fields.Float(string="Total Amount", readonly=True)
    payment_amt = fields.Float(string="Payment Amount", compute='_compute_payment_amt')


    @api.onchange('fixed_percentage', 'fixed_amount')
    def _compute_payment_amt(self):
        for record in self:
            value = 0.0
            if record.payment_type == 'percentage':
                percent = record.fixed_percentage / 100
                value = percent * record.total_amount
                print(value)
            else:
                value = record.fixed_amount
            record.payment_amt = value

    @api.model
    def default_get(self, fields):
        res = super(BrokerFeesWizard, self).default_get(fields)
        sale_order = self.env['sale.order'].browse(self.env.context.get('active_id'))
        res.update({'quote_name': self.env.context.get('active_id'), 'total_amount': sale_order.amount_total})
        return res

    def brokser_fees(self):
        # sale_order = self.env['sale.order'].browse(self.env.context.get('active_id'))
        broker_fees_obj = self.env['broker.fees']
        for rec in self:
            broker_fees_obj.create({

                'quote_name': rec.quote_name.id,
                'partner_id': rec.partner_id.id,
                'payment_type': rec.payment_type,
                'product_id': rec.product_id.id,
                'fixed_amount': rec.fixed_amount,
                'fixed_percentage': rec.fixed_percentage,
                'payment_amt': rec.payment_amt,

            })

        return True


from odoo import api, models, fields, _
from ast import literal_eval
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class BrokerFeesWizard(models.TransientModel):
    _name = 'broker.fees.wizard'
    _description = 'Broker Fees Wizard'

    partner_id = fields.Many2one('res.partner', string='Broker')
    payment_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed_amount', 'Fixed Amount'),
    ], default='percentage', string='Payment')
    fixed_amount = fields.Float(
        string="Fixed Amount", help="Fixed amount.")
    fixed_percentage = fields.Float(string="Fixed Percentage")
    product_id = fields.Many2one('product.product', string='Product', domain="[('detailed_type', '=', 'service')]")
    quote_name = fields.Many2one('sale.order', string="Sale Order")
    total_amount = fields.Float(string="Total Amount", readonly=True)
    payment_amt = fields.Float(string="Payment Amount", compute='_compute_payment_amt')

    @api.onchange('fixed_percentage', 'fixed_amount')
    def _compute_payment_amt(self):

        for record in self:
            value = 0.0
            if record.payment_type == 'percentage':
                percent = record.fixed_percentage / 100;
                print(percent, '///////////////////')
                value = percent * record.total_amount
                print(value)
            else:
                value = record.fixed_amount
            record.payment_amt = value
            print(record, '///////////')

    @api.model
    def default_get(self, fields):
        res = super(BrokerFeesWizard, self).default_get(fields)
        sale_order = self.env['sale.order'].browse(self.env.context.get('active_id'))
        res.update({'quote_name': self.env.context.get('active_id'), 'total_amount': sale_order.amount_total})
        return res

    def brokser_fees(self):
        # sale_order = self.env['sale.order'].browse(self.env.context.get('active_id'))
        broker_fees_obj = self.env['broker.fees']
        for rec in self:
            broker_fees_obj.create({

                'quote_name': rec.quote_name.id,
                'partner_id': rec.partner_id.id,
                'payment_type': rec.payment_type,
                'product_id': rec.product_id.id,
                'fixed_amount': rec.fixed_amount,
                'fixed_percentage': rec.fixed_percentage,
                'payment_amt': rec.payment_amt,

            })

        return True


from odoo import api, models, fields, _
from ast import literal_eval
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class BrokerFeesWizard(models.TransientModel):
    _name = 'broker.fees.wizard'
    _description = 'Broker Fees Wizard'


    def _set_bu_domain(self):
        domain = [('id', 'in', [bu.id for bu in self.env.user.hr_bu_ids])]
        return domain
    def _set_br_domain(self):
        domain = [('id', 'in', [br.id for br in self.env.user.hr_br_ids])]
        return domain
    

    partner_id = fields.Many2one('res.partner', string='Broker')
    payment_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed_amount', 'Fixed Amount'),
    ], default='fixed_amount', string='Payment')
    fixed_amount = fields.Float(
        string="Fixed Amount", help="Fixed amount.")
    fixed_percentage = fields.Float(string="Fixed Percentage")
    product_id = fields.Many2one('product.product', string='Product', domain="[('detailed_type', '=', 'service')]")
    quote_name = fields.Many2one('sale.order', string="Sale Order")
    total_amount = fields.Float(string="Total Amount", readonly=True)
    payment_amt = fields.Float(string="Payment Amount", compute='_compute_payment_amt')
    hr_br_id = fields.Many2one('business.unit', string='Branch',domain=_set_br_domain)
    hr_bu_id = fields.Many2one('business.unit', string='Business Unit',domain=_set_bu_domain)
    invoice_name = fields.Many2one('account.move', string="Sale Invoice")
    phone_no = fields.Char(string="Kpay / Mobile Banking")
    bfoker_type = fields.Selection([
        ('upon_delivery', 'Upon Delivery'),
        ('ar', 'AR Finished'),
    ], default='upon_delivery', string='Type')
    attachment_id = fields.Many2many('ir.attachment','attachment',string="Attachment")

    @api.onchange('fixed_percentage', 'fixed_amount')
    def _compute_payment_amt(self):
        for record in self:
            value = 0.0
            if record.payment_type == 'percentage':
                percent = record.fixed_percentage / 100;
                value = percent * record.total_amount
                print(value)
            else:
                value = record.fixed_amount
            record.payment_amt = value

    @api.model
    def default_get(self, fields):
        res = super(BrokerFeesWizard, self).default_get(fields)
        # sale_order = self.env['sale.order'].browse(self.env.context.get('active_id'))
        # res.update({'quote_name': self.env.context.get('active_id'), 'total_amount': sale_order.amount_total,
        #             'hr_br_id': sale_order.hr_br_id.id, 'hr_bu_id': sale_order.hr_bu_id.id})
        invoice = self.env['account.move'].browse(self.env.context.get('active_id'))
        res.update({'invoice_name': self.env.context.get('active_id'), 'total_amount': invoice.amount_untaxed,
                    'hr_br_id': invoice.hr_br_id.id, 'hr_bu_id': invoice.hr_bu_id.id,'quote_name': invoice.sale_order_id.id})
        return res

    def request_brokser_fees(self):
        broker_fees_obj = self.env['broker.fees']
        for rec in self:
            brocker_id = broker_fees_obj.create({
                'quote_name': rec.quote_name.id,
                'partner_id': rec.partner_id.id,
                'payment_type': rec.payment_type,
                'product_id': rec.product_id.id,
                'fixed_amount': rec.fixed_amount,
                'fixed_percentage': rec.fixed_percentage,
                'payment_amt': rec.payment_amt,
                'hr_br_id': rec.hr_br_id.id,
                'hr_bu_id': rec.hr_bu_id.id,
                'phone_no': rec.phone_no,
                'invoice_name': rec.invoice_name.id,
                'bfoker_type': rec.bfoker_type,
                'attachment_id': rec.attachment_id

            })
            rec.attachment_id.write({'res_model': 'broker.fees','res_id': brocker_id.id})
            rec.invoice_name.write({'broker_fees_id': brocker_id.id,
                                  'broker_button': True})
