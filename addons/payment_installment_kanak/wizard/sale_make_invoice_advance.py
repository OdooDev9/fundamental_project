
import time

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    advance_payment_method = fields.Selection(selection_add=[
            ('fixed_installment','Installment Down Payment (fixed amount)')
        ],ondelete={'fixed_installment': 'set default'})

    @api.onchange('advance_payment_method')
    def onchange_advance_payment_method(self):
        if self.advance_payment_method == 'percentage':
            amount = self.default_get(['amount']).get('amount')
            return {'value': {'amount': amount}}

        if self.advance_payment_method == 'fixed_installment':
            if self._context.get('active_model') == 'sale.order' and self._context.get('active_id', False):
                sale_order = self.env['sale.order'].browse(self._context.get('active_id'))
                if sale_order.installment_ids:
                    amount = sale_order.down_payment_amt
                    return {'value':{'fixed_amount':amount}}
                else:
                    raise UserError(_('This sale order is not Installment.'))
        return {}

    def _create_invoice(self, order, so_line, amount):
        if (self.advance_payment_method == 'percentage' and self.amount <= 0.00) or (
                self.advance_payment_method == 'fixed' and self.fixed_amount <= 0.00):
            raise UserError(_('The value of the down payment amount must be positive.'))

        amount, name = self._get_advance_details(order)

        invoice_vals = self._prepare_invoice_values(order, name, amount, so_line)
        invoice_vals['hr_br_id'] = order.hr_br_id.id or False
        invoice_vals['hr_bu_id'] = order.hr_bu_id.id or False
        invoice_vals['unit_or_part'] = order.unit_or_part
        invoice_vals['sale_order_id'] = order.id

        if order.fiscal_position_id:
            invoice_vals['fiscal_position_id'] = order.fiscal_position_id.id

        invoice = self.env['account.move'].with_company(order.company_id) \
            .sudo().create(invoice_vals).with_user(self.env.uid)
        invoice.message_post_with_view('mail.message_origin_link',
                                       values={'self': invoice, 'origin': order},
                                       subtype_id=self.env.ref('mail.mt_note').id)
        return invoice