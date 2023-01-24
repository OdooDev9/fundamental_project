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
from odoo import fields, models
from odoo import tools, _
import logging

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_installment_modify(self):
        self.ensure_one()
        new_wizard = self.env['modify.installment'].create({
            'name':self.name,
            'order_id': self.id,
        })
        new_wizard.onchange_order()
        return {
            'name': _('Modify Installment'),
            'view_mode': 'form',
            'res_model': 'modify.installment',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': new_wizard.id,
            'context': self.env.context,
        }

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        return True
        if self.installment_ids:
            if not self.payment_term_id:
                count = 30
                index = 0
                inst_line_data = []
                payment_term = self.env['account.payment.term'].create({
                        'name': 'Payment Installment %s' % (self.partner_id.name),
                        'sale_order_id': self.id
                    })
                installment_line = self.installment_ids
                for inst_line in installment_line:
                    line_vals = (0, 0, {
                        'value': 'fixed',
                        'value_amount': inst_line.without_interest_amount,
                        'days': count,
                        'option': 'day_after_invoice_date',
                        'day_of_the_month': 0,
                        'sequence': index
                    })

                    inst_line_data.append(line_vals)
                    count += 30
                    index += 1
                payment_term.line_ids.update({'sequence': len(installment_line) + 1, 'value_amount': installment_line[-1:].amount, 'days': count+30})
                payment_term.line_ids = inst_line_data
                self.payment_term_id = payment_term and payment_term.id or False
        return res


class AccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"

    sale_order_id = fields.Many2one('sale.order')
