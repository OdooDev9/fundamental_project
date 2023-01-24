
from odoo import fields, models, api


class SubPartPaymentConfirm(models.TransientModel):
    _name = 'installment.invoice.wizard'

    @api.model
    def _default_product_id(self):
        product_id = self.env['ir.config_parameter'].sudo().get_param('sale.default_deposit_product_id')
        return self.env['product.product'].browse(int(product_id)).exists()


    advance_payment_method = fields.Selection([
        ('delivered', 'Regular invoice'),
        ('down', 'Down payment'),
        ], string='Create Invoice', default='delivered', required=True,
        help="A standard invoice is issued with all the order lines ready for invoicing, \
        according to their invoicing policy (based on ordered or delivered quantity).")
    product_id = fields.Many2one('product.product', string='Down Payment Product', domain=[('type', '=', 'service')],
                                 default=_default_product_id)
    amount = fields.Float('Amount')
    down = fields.Boolean()
    recontract_id = fields.Many2one('re.installment.plan')

    def _prepare_invoice_values(self, order, name, amount, product_id, product_uom):
        invoice_vals = {
            'move_type': 'out_invoice',
            'invoice_origin': name,
            'invoice_user_id': self.env.uid,
            'narration': self.recontract_id.note,
            'partner_id': self.recontract_id.partner_id.id,
            'hr_bu_id': self.recontract_id.hr_bu_id.id,
            'hr_br_id': self.recontract_id.hr_br_id.id,
            'partner_shipping_id': order.partner_shipping_id.id,
            'currency_id': self.recontract_id.currency_id.id,
            'team_id': order.team_id.id,
            'source_id': order.source_id.id,
            're_contract_id': self.recontract_id.id,
            'invoice_line_ids': [(0, 0, {
                'name': name,
                'price_unit': amount,
                'quantity': 1.0,
                'product_id': product_id and product_id.id or False,
                'product_uom_id': product_uom and product_uom.id or False,
            })],
        }

        return invoice_vals

    def create_invoice(self):
        order = self.recontract_id.order_id
        name = self.recontract_id.note
        product_id = product_uom = False
        if self.advance_payment_method == 'down':
            amount = self.recontract_id.down_payment_amt
            product_id = self.product_id
            product_uom = self.product_id.uom_id
            self.recontract_id.down = True
            name = 'Down payment (' + self.recontract_id.name + ' )'
        else:
            amount = self.recontract_id.tenure_amt
            if self.down:
                amount = amount - self.recontract_id.down_payment_amt

        invoice_vals = self._prepare_invoice_values(order, name, amount, product_id, product_uom)
        recontract_id = self.recontract_id
        if self.advance_payment_method != 'down':
            invoice_vals.update({
                'installment_plan_id': recontract_id.installment_plan_id.id,
                'down_payment_amt': recontract_id.down_payment_amt,
                'second_payment_date': recontract_id.second_payment_date,
                'installment_amt': recontract_id.installment_amt,
                'payable_amt': recontract_id.payable_amt,
                'tenure': recontract_id.tenure,
                'payment_circle_count': recontract_id.payment_circle_count,
                'fine_threshold': recontract_id.fine_threshold,
                'tenure_type': recontract_id.tenure_type,
                'tenure_amt': recontract_id.tenure_amt,
                'tenure_amount_untaxed': recontract_id.tenure_amt,
                'tenure_amount_tax': recontract_id.tenure_amount_tax,
                'down_payment_type': recontract_id.down_payment_type,
                'down_payment_percent': recontract_id.down_payment_percent,
                'down_payment_fixed': recontract_id.down_payment_fixed,
                'interest_rate': recontract_id.interest_rate,
                'interest_start_from': recontract_id.interest_start_from,
                'fine_rate': recontract_id.fine_rate,
                'fine_discount': recontract_id.fine_discount,
                'start_invoice_date': recontract_id.start_invoice_date,
                'contract_date': recontract_id.contract_date,
            })
            interest_product = self.env['product.product'].search([('name', '=', 'Interest'), ('type', '=', 'service'),
                                                                   ('business_id', '=', recontract_id.hr_bu_id.id)])
            invoice_vals['invoice_line_ids'].append((0, 0, {'name': interest_product[0].name,
                                                            'price_unit': recontract_id.total_interest,
                                                            'quantity': 1.0,
                                                            'product_id': interest_product[0] and interest_product[0].id or False,
                                                            'product_uom_id': interest_product[0].uom_id.id or False,
                                                            }))

        invoice = self.env['account.move'].with_company(order.company_id)\
            .sudo().create(invoice_vals).with_user(self.env.uid)
        invoice.compute_installment()
        invoice.message_post_with_view('mail.message_origin_link',
                    values={'self': invoice, 'origin': order},
                    subtype_id=self.env.ref('mail.mt_note').id)
        return invoice