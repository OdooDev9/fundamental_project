# -*- coding: utf-8 -*-
from attr import field
from odoo import models, fields, api, _

class AccountAccountInherit(models.Model):
    _inherit = "account.account"
    current_debit = fields.Float('Debit', compute='_compute_current_balance')  
    current_credit = fields.Float('Credit', compute='_compute_current_balance')  

    def _compute_current_balance(self):
        balances = {
            read['account_id'][0]: read['balance']
            for read in self.env['account.move.line'].read_group(
                domain=[('account_id', 'in', self.ids)],
                fields=['balance', 'account_id'],
                groupby=['account_id'],
            )
        }
        debit = {
            read['account_id'][0]: read['debit']
            for read in self.env['account.move.line'].read_group(
                domain=[('account_id', 'in', self.ids)],
                fields=['debit', 'account_id'],
                groupby=['account_id'],
            )
        }
        credit = {
            read['account_id'][0]: read['credit']
            for read in self.env['account.move.line'].read_group(
                domain=[('account_id', 'in', self.ids)],
                fields=['credit', 'account_id'],
                groupby=['account_id'],
            )
        }
        for record in self:
            record.current_balance = balances.get(record.id, 0) 
            record.current_debit = debit.get(record.id, 0) 
            record.current_credit = credit.get(record.id, 0) 

    @api.model 
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = super(AccountAccountInherit, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        if 'current_debit' in fields:
            for line in res:
                if '__domain' in line:
                    lines = self.search(line['__domain'])
                    total_invoice_due = 0.0
                    for record in lines:
                        total_invoice_due += record.current_debit
                    line['current_debit'] = total_invoice_due
        if 'current_credit' in fields:
            for line in res:
                if '__domain' in line:
                    lines = self.search(line['__domain'])
                    total_invoice_due = 0.0
                    for record in lines:
                        total_invoice_due += record.current_debit
                    line['current_credit'] = total_invoice_due   
        if 'current_balance' in fields:  
            for line in res:
                if '__domain' in line:
                    lines = self.search(line['__domain'])
                    total_invoice_due = 0.0
                    for record in lines:
                        total_invoice_due += record.current_balance
                    line['current_balance'] = total_invoice_due   

        return res

    def open_entries(self):
        # mvl = account move line
        mvl = self.env["account.move.line"].search([('account_id', 'in', self.ids)])
        move_ids = mvl.move_id
        action = {
            'name': _('Entries'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False},
            'view_mode': 'tree',
            'domain': [('id', 'in', move_ids.ids)],
        }
        return action
    
    def open_payments(self):
        mvl = self.env["account.move.line"].search([('account_id', 'in', self.ids)])
        move_ids = mvl.move_id
        payment = self.env["account.payment"].search([('move_id', 'in', move_ids.ids)])
        action = {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'create': False},
            'view_mode': 'tree',
            'domain': [('id', 'in', payment.ids)],
        }
        return action 

class BusinessUnitInherit(models.Model):
    _inherit = "business.unit"
    
    def open_entries_lines(self):
        # action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_line_select")
        action = {
            'name': _('Entries Lines'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'context': {'create': False},
            'view_mode': 'tree',
            'domain': ['|', ('move_id.hr_bu_id', 'in', self.ids), ('move_id.hr_br_id', 'in', self.ids)],
        }
        return action

    def open_entries(self):
        # mvl = account move line
        # mvl = self.env["account.move.line"].search(['|', ('move_id.hr_bu_id', 'in', self.ids), ('move_id.hr_br_id', 'in', self.ids)])
        # move_ids = mvl.move_id
        action = {
            'name': _('Entries'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False},
            'view_mode': 'tree',
            'domain': ['|',('hr_bu_id', 'in', self.ids),('hr_br_id', 'in', self.ids)],
        }
        return action

    def open_payments(self):
        
        payment = self.env["account.payment"].search(['|', ('hr_bu_id', 'in', self.ids), ('hr_br_id', 'in', self.ids)])
        action = {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'create': False},
            'view_mode': 'tree',
            'domain': [('id', 'in', payment.ids)],
        }
        return action    

