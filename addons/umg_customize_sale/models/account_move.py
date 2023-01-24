from odoo import models, fields, _
from  datetime import datetime, date
from odoo.exceptions import UserError



class AccountMove(models.Model):
    _inherit = 'account.move'

    broker_fees_id = fields.Many2one('broker.fees', string='Broker Fees')
    service_type = fields.Boolean(string="Service Type")
    broker_button = fields.Boolean('Hide Button',default=False)
    

    def unlink(self):
        for result in self:
            if result.state not in ['draft']:
                raise UserError(_('Cannot delete a bill which is in state \'%s\'.') % (result.state,))
            tbl_broker = self.env['broker.fees']
            if result.broker_fees_id and result.move_type=='in_invoice':
                result.broker_fees_id.write({'broker_bill': False})
        res = super(AccountMove, self).unlink()
        return res


    def action_approve_finance_pic(self):
        self.write({'state':'approved_finance_pic'})
    
    def action_approve_finance_head(self):
        self.write({'state':'approved_finance_head'})

    
    

    def compute_commission(self):
        for rec in self:
            amount = 0.0
            br_discount_amount =0.0
            for line in rec.invoice_line_ids:
                commission = line.product_id.commission if line.product_id.commission > 0.0 else line.product_id.categ_id.commission
                # amount += (line.price_unit * line.quantity) * (commission/100)
                # amount += line.price_subtotal * (commission/100)
                # br_discount_amount += line.price_subtotal- (line.br_dis_value/100)
                # print(br_discount_amount,'xxxxxxxxxxxxx')
                if rec.discount_type == 'percentage':
                    amount += ((line.price_unit * line.quantity) - ((line.price_unit * line.quantity) * line.discount/100)) * commission/100 - (((line.price_unit * line.quantity) - ((line.price_unit * line.quantity) * line.discount/100)) * line.br_dis_value/100)
                else:
                    amount += (((line.price_unit * line.quantity) - line.discount) * commission/100) - line.br_dis_value
                
            if amount > 0.0 and rec.hr_br_id:
                commission_id = self.env['sale.commission'].search([('invoice_id', '=', rec.id)])
                # if not commission_id:
                self.env['sale.commission'].create({'invoice_id': rec.id,
                                                    'business_id': rec.hr_bu_id.id,
                                                    'branch_id': rec.hr_br_id.id,
                                                    'date': datetime.today().date(),
                                                    'currency_id': rec.currency_id.id,
                                                    'amount': amount,
                                                    'name': 'commission for ' + str(rec.hr_br_id.name),})
            # else:
                #     commission_id.write({'invoice_id': rec.id,
                #                          'business_id': rec.hr_bu_id.id,
                #                          'branch_id': rec.hr_br_id.id,
                #                          'date': datetime.today().date(),
                #                          'currency_id': rec.currency_id.id,
                #                          'amount': amount - rec.br_discount_amount,
                #                          'name': 'commission for ' + str(rec.hr_br_id.name),
                #                          })

    def action_post(self):
        if self.payment_id:
            self.payment_id.action_post()
        else:
            self._post(soft=False)
            
        if self.move_type == 'out_invoice':
            self.compute_commission()
        return False
    
    def action_reverse(self):
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_view_account_move_reversal")

        if self.is_invoice():
            action['name'] = _('Credit Note')
        comission_obj = self.env['sale.commission'].search([('invoice_id','=',self.id),('state','=','draft')])
        comission_obj.unlink()

        return action
    
    def action_view_commission(self):
        action = self.env.ref('umg_customize_sale.sale_commission_action').read()[0]
        _ids = []
        for com in self.env['sale.commission'].search([]):
           
            if self.id == com.invoice_id.id:
                _ids.append(com.id)
        action['domain'] = [('id', '=', _ids)]
        return action

    def button_draft(self):
        AccountMoveLine = self.env['account.move.line']
        excluded_move_ids = []

        if self._context.get('suspense_moves_mode'):
            excluded_move_ids = AccountMoveLine.search(AccountMoveLine._get_suspense_moves_domain() + [('move_id', 'in', self.ids)]).mapped('move_id').ids

        for move in self:
            if move in move.line_ids.mapped('full_reconcile_id.exchange_move_id'):
                raise UserError(_('You cannot reset to draft an exchange difference journal entry.'))
            if move.tax_cash_basis_rec_id or move.tax_cash_basis_origin_move_id:
                # If the reconciliation was undone, move.tax_cash_basis_rec_id will be empty;
                # but we still don't want to allow setting the caba entry to draft
                # (it'll have been reversed automatically, so no manual intervention is required),
                # so we also check tax_cash_basis_origin_move_id, which stays unchanged
                # (we need both, as tax_cash_basis_origin_move_id did not exist in older versions).
                raise UserError(_('You cannot reset to draft a tax cash basis journal entry.'))
            if move.restrict_mode_hash_table and move.state == 'posted' and move.id not in excluded_move_ids:
                raise UserError(_('You cannot modify a posted entry of this journal because it is in strict mode.'))
            # We remove all the analytics entries for this journal
            move.mapped('line_ids.analytic_line_ids').unlink()

        self.mapped('line_ids').remove_move_reconcile()
        self.write({'state': 'draft', 'is_move_sent': False})

        comission_obj = self.env['sale.commission'].search([('invoice_id','=',move.id),('state','=','draft')])
        comission_obj.unlink()
