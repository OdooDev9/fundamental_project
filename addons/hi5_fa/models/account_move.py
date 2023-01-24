from odoo import fields, models,api
from dateutil.relativedelta import relativedelta
from datetime import date, timedelta
import datetime

class AccountMove(models.Model):
    _inherit = "account.move"

    def get_invoice_data(self):
        assign_line_tbl = self.env['ar.assign.line']
        move_ids = self.env['account.move'].search([('state','=','posted'),('move_type','=','out_invoice')])#('id','=',7013)
        value = {}
        for rec in move_ids:
            future_due = rec.installment_ids.filtered(lambda x:x.state == 'draft')
            current_due = rec.installment_ids.filtered(lambda x:x.state == 'current_due')
            take_action_due = rec.installment_ids.filtered(lambda x:x.state == 'take_action')
            need_action = rec.installment_ids.filtered(lambda x:x.state == 'need_action')
            
            # if rec.invoice_date_due:
            #     take_action_month = rec.invoice_date_due + relativedelta(months=2)
            #     print('invoice_date_due================>>',take_action_month)
            # elif rec.invoice_payment_term_id:
            #     print(rec.name,"rec.invoice_date=-===============///",timedelta(days=30))
            #     # print('============days',rec.invoice_payment_term_id.line_ids.days)
            #     take_action_month = rec.invoice_date + timedelta(days=30)#rec.invoice_payment_term_id.line_ids.days)

                # print('invoice_payment_term_id================>>',take_action_month)
            if rec.installment_ids:
                if not current_due.state == 'current_due':
                    if future_due:
                        if future_due[0]:
                            future_assign_ids = self.env['ar.assign.line'].search([('installment_id','=',future_due[0].id)])
                            # print(future_assign_ids.id,'-------------------------------->>')
                            future_id = future_assign_ids.filtered(lambda x:x.due_type == 'draft')
                            if not future_assign_ids:
                                assign_line_tbl.create({'invoice_id':future_due[0].invoice_id.id,'installment_id' : future_due[0].id, 'due_type':'draft','due_amount':future_due[0].amount,'invoice_type': line.invoice_id.unit_or_part})
                
                for line in rec.installment_ids:
                    today = line.invoice_id.payment_term_date#date.today()
                    two_month = line.payment_date + relativedelta(months=2)
                    if line.payment_start_date and today and line.payment_end_date:
                        if line.payment_start_date <= today <= line.payment_end_date and line.state == 'current_due':
                            
                            current_assign_ids = self.env['ar.assign.line'].search([('installment_id','=',line.id)])
                            current_id = current_assign_ids.filtered(lambda x:x.due_type == 'current_due')
                            if not need_action:
                                if not take_action_due:
                                    if not current_id:
                                        assign_line_tbl.create({'invoice_id':line.invoice_id.id,'installment_id' : line.id, 'due_type':'current_due','due_amount': line.amount,'invoice_type': line.invoice_id.unit_or_part})

                        elif today >= two_month:
                            over_assign_ids = self.env['ar.assign.line'].search([('installment_id','=',line.id)])
                            take_action = over_assign_ids.filtered(lambda x:x.due_type == 'take_action')
                            if not take_action:
                                assign_id = assign_line_tbl.create({'invoice_id':line.invoice_id.id,'installment_id' : line.id, 'due_type': 'take_action','due_amount': line.amount,'invoice_type': line.invoice_id.unit_or_part})
            if rec.unit_or_part == False:
                service_today = datetime.date(2022, 12, 12)
                # service_today = '2023-04-05' #date.today()
                take_action_month = rec.invoice_date + timedelta(days=30)#rec.invoice_payment_term_id.line_ids.days)

                service = 'service'
                due_amount =0.0
                due_amount += rec.amount_residual
                days = rec.invoice_payment_term_id.line_ids.days
                due_date = rec.invoice_date + timedelta(days=days)
                
                # if rec.invoice_payment_term_id:
                take_action_month = due_date + relativedelta(months=2) if rec.invoice_payment_term_id else rec.invoice_date_due + relativedelta(months=2)
                    # print(rec.invoice_date,'invoice_date_due================>>',take_action_month)
                # else:
                #     take_action_month = rec.invoice_date_due + relativedelta(months=2)
                print(due_amount,'take_action_month=======>>>',take_action_month)
                if service_today >= take_action_month:
                    take_action_assign_ids = self.env['ar.assign.line'].search([('invoice_id','=',rec.id)])
                    if not take_action_assign_ids:
                        assign_line_tbl.create({'invoice_id':rec.id, 'due_type': 'take_action','due_amount': due_amount,'invoice_type':service })
                elif rec.invoice_date <= service_today <= take_action_month:
                    current_due_assign_ids = self.env['ar.assign.line'].search([('invoice_id','=',rec.id)])
                    if not current_due_assign_ids:
                        assign_line_tbl.create({'invoice_id':rec.id, 'due_type': 'current_due','due_amount': due_amount,'invoice_type':service })
                else:
                    future_due_assign_ids = self.env['ar.assign.line'].search([('invoice_id','=',rec.id)])
                    if not future_due_assign_ids:
                        assign_line_tbl.create({'invoice_id':rec.id, 'due_type': 'draft','due_amount': due_amount,'invoice_type':service })
                    



