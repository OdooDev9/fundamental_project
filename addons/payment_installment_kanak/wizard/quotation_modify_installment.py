from odoo import api, fields, models


class RequestQuotationModifyInstallment(models.TransientModel):
    _name = 'request.quotation.modify.installment'
    _description = 'Modify Sale Order Installment Manually'

    name = fields.Char(string="Name")
    tenure_type = fields.Selection([
        ('month', 'months'),
    ], string="Tenure Type", default="month")
    tenure = fields.Integer(string="Tenure")

    down_payment_type = fields.Selection([
        ('percent', 'Percentage(%)'),
        ('fix', 'Fixed')
    ], string="Down Payment Type")

    down_payment_percent = fields.Float(string="Down Payment(%)")
    down_payment_fixed = fields.Float(string="Down Payment(Fixed)")

    payment_circle_count = fields.Integer(string="Payment Every(Month)", help="Payment Circle Count")
    fine_threshold = fields.Integer(string="Fine Threshold", help="To start fine calculation!")

    interest_rate = fields.Float(string="Interest Rate(%)")
    interest_start_from = fields.Integer(string="Interest Start From", help="Interest Start Index")
    fine_rate = fields.Float(string="Fine Rate(%)")
    user_id = fields.Many2one(
        'res.users', string='Salesperson', index=True, default=lambda self: self.env.user)
    quotation_id = fields.Many2one('request.quotation', 'Request Quotation')

    @api.onchange('quotation_id')
    def onchange_quotation_id(self):
        if self.quotation_id:
            self.tenure_type = self.quotation_id.tenure_type
            self.tenure = self.quotation_id.tenure
            self.down_payment_percent = self.quotation_id.down_payment_percent
            self.down_payment_type = self.quotation_id.down_payment_type
            self.down_payment_fixed = self.quotation_id.down_payment_fixed
            self.payment_circle_count = self.quotation_id.payment_circle_count
            self.fine_threshold = self.quotation_id.fine_threshold
            self.interest_rate = self.quotation_id.interest_rate
            self.interest_start_from = self.quotation_id.interest_start_from
            self.fine_rate = self.quotation_id.fine_rate
            self.user_id = self.quotation_id.user_id

    def modify(self):
        vals = {'tenure_type':self.tenure_type,
                'tenure':self.tenure,
                'down_payment_percent': self.down_payment_percent,
                'down_payment_type': self.down_payment_type,
                'down_payment_fixed': self.down_payment_fixed,
                'payment_circle_count': self.payment_circle_count,
                'fine_threshold': self.fine_threshold,
                'interest_rate': self.interest_rate,
                'interest_start_from': self.interest_start_from,
                'fine_rate': self.fine_rate,
                'user_id': self.user_id
        }
        order_id = self.quotation_id.write(vals)
        self.quotation_id.compute_installment()
        return order_id