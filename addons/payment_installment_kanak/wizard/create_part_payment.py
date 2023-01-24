# -*- coding: utf-8 -*-

from odoo import fields, models


class SubPartPaymentConfirm(models.Model):
    _name = 'sub.part.payment'
    _description = 'Sub Part Payment'
    _order = 'index'

    part_amt = fields.Float(string="Amount")

    def part_payment_confirm(self):
        if self.part_amt > 0:
            line_vals = {
                    'index': 1,
                    'amount': self.part_amt,
                    'payment_date': fields.Date.today(),
                    'description': 'Part Payment',
                    'invoice_id': self.env.context['active_id'],
                }
            line_installment = self.env['account.move'].browse(self.env.context['active_id']).installment_ids.filtered(lambda x: x.index != 0)
            for line in line_installment:
                line.update({'index': line.index+1})
            inv_line_id = self.env['invoice.installment.line'].create(line_vals)
            amt = self.env['account.move'].browse(self.env.context['active_id']).installment_ids.filtered(lambda x: x.state == 'draft' and x.description != 'Part Payment')
            previous_amount = sum(amt.mapped('amount'))
            if len(amt)>0:
                adj_amt = self.part_amt/len(amt)
            else:
                adj_amt = 0
            for l in amt:
                l.amount -= adj_amt
            if self.part_amt == previous_amount:
                amt.filtered(lambda x: x.state == 'draft').unlink()
            account_move = self.env['account.move'].browse(self.env.context['active_id'])
            sol = self.env['sale.order.line'].search([('id', 'in', account_move.invoice_line_ids.mapped('sale_line_ids').ids)]).order_id
            line_installment = sol.installment_ids.filtered(lambda x: x.index != 0)
            for line in line_installment:
                line.update({'index': line.index+1})
            line_vals = {
                    'index': 1,
                    'amount': self.part_amt,
                    'payment_date': fields.Date.today(),
                    'description': 'Part Payment',
                    'sale_id': sol.id
                }
            sale_line_id = self.env['sale.installment.line'].create(line_vals)
            inv_line_id.sinst_line_id = sale_line_id.id
            amt_1 = sol.installment_ids.filtered(lambda x: x.state == 'draft' and x.description != 'Part Payment')
            previous_amount = sum(amt_1.mapped('amount'))
            adj_amt_1 = self.part_amt/len(amt_1)
            for l in amt_1:
                l.amount -= adj_amt_1
            if self.part_amt == previous_amount:
                amt_1.filtered(lambda x: x.state == 'draft').unlink()
            return self.env['account.payment']\
           .with_context(active_ids=self.env.context['active_ids'], active_model='account.move', active_id=self.env.context['active_id'], line_model='invoice.installment.line', line_id=inv_line_id.id, default_amount=self.part_amt)\
    .action_register_payment()
