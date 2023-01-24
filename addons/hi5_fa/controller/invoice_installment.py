import json

from odoo import fields
from odoo.http import request
from odoo import http

class InvoiceInstallmentController(http.Controller):
    @http.route('/api/invoice-installment/list',type='http', auth='public', csrf=False, cors='*',methods=['GET'])
    def invoice_installment_list(self,**kwargs):
        user_id = request.env['res.users'].sudo().search([('id', '=', 6)])#request.env.user.id
        account_move_ids = request.env['account.move'].sudo().search([('state','=','posted'),('hr_bu_id','=',user_id.current_bu_br_id.id)])
        print('')
        print('Customer Count===>>',len(account_move_ids.partner_id))
        take_action_due_amount,current_due_amount,future_due_amount,unit_amount,part_amount = 0.0,0.0,0.0,0.0,0.0
        current_due_customer=future_due_customer=take_action_customer=service_ar_amount=0.0
        for account_move_id in account_move_ids:
            # print('Customer Count===>>',len(account_move_ids.ids))
            all_credit_customer = len(account_move_ids.mapped('partner_id'))
            take_action = account_move_id.installment_ids.filtered(lambda x:x.state == 'take_action')
            current_due = account_move_id.installment_ids.filtered(lambda x:x.state == 'current_due')
            future_due = account_move_id.installment_ids.filtered(lambda x:x.state == 'draft')

            unit_ar = account_move_id.filtered(lambda x:x.unit_or_part == 'unit')
            part_ar = account_move_id.filtered(lambda x:x.unit_or_part == 'part')
            if unit_ar:
                unit_amount += unit_ar.amount_residual
            elif part_ar:
                part_amount += part_ar.amount_residual

            if not current_due:
                if not take_action:
                    if future_due:
                        if future_due[0]:
                            future_due_customer += len(future_due[0].invoice_id.partner_id)
                            future_due_amount += future_due[0].amount
            elif not take_action:
                if current_due:
                    current_due_customer += len(current_due.invoice_id.partner_id)
                    current_due_amount += (current_due[-1].amount - current_due[-1].paid_amount)

            elif take_action:
                take_action_customer += len(take_action.invoice_id.partner_id)
                take_action_due_amount += (take_action[-1].amount - take_action[-1].paid_amount)
            if account_move_id.unit_or_part == False:
                service_ar_amount += account_move_id.amount_residual


        return json.dumps({'success':True,'message':None,'data':[
            {
            'all_credit_customers':sum(account_move_ids.mapped('amount_residual')),
            'all_credit_customer': all_credit_customer,
            'take_action_due_amount':take_action_due_amount,
            'take_action_customer': take_action_customer,
            'current_action_due_amount': current_due_amount,
            'current_due_customer': current_due_customer,
            'future_action_due_amount': future_due_amount,
            'future_due_customer': future_due_customer,
            'unit_ar_amount': unit_amount,
            'part_ar_amount': part_amount,
            'service_ar_amount': service_ar_amount
        }
        ]})