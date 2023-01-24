import re
from attr import field
from odoo import api, fields, models, _
from datetime import date,datetime
from odoo.exceptions import AccessError, UserError, ValidationError

class RetainIncentiveApproval(models.TransientModel):
    _name = 'incentive.retain.wizard'
    _description = 'Retain Incentive Approval Wizard'

    @api.model
    def default_get(self, fields):
        res = super(RetainIncentiveApproval, self).default_get(fields)
        amount = 0.0
        bu = set()
        for request_ids in self.env.context.get('active_ids'):
            request_incentive_obj = self.env['incentive.request'].browse(request_ids)
            bu.add(request_incentive_obj.business_id)
            if len(bu) >1:
                raise UserError(_('Your Incentive is not Retain Payment, Business Unit is many differences'))
        # request_incentive_id = self.env['incentive.request'].browse(self._context.get('active_id'))

            amount += request_incentive_obj.retain_amount
            currency_id = self.env.ref('base.MMK') 
            for req_line in request_incentive_obj.incentive_request_line:
                for incen in req_line.normal_incentive_id:
                    for line in incen.line_ids.filtered(lambda x: x.sale_person_type == 'retain'):
                        partner_id = line[0].partner_id.id

                        res.update({'partner_id': partner_id,
                                    'amount': amount,
                                    'source_amount':amount,
                                    'currency_id': currency_id.id,
                                    'memo': request_incentive_obj.name,
                                    'date': date.today()})
        return res

    # @api.model
    # def default_get(self, fields):
    #     res = super(RetainIncentiveApproval, self).default_get(fields)
    #     amount = 0.0
    #     incentive_id = self.env['normal.incentive.main'].browse(self._context.get('active_id'))
    #     for line in incentive_id.line_ids.filtered(lambda x: x.sale_person_type == 'retain'):
    #         if incentive_id.incentive_definition_id.payment_rule == 'invoice':
    #             amount = line.incentive_amount
    #             partner_id = line.partner_id
    #         elif incentive_id.incentive_definition_id.payment_rule == 'both':
    #             # if incentive_id.paid_amount > 0.0:
    #             #     amount = incentive_id.due_amount
    #             #     partner_id = line.partner_id
    #             # else:
    #             amount = line.incentive_amount/2
    #             partner_id = line.partner_id
    #     # else:
    #         elif incentive_id.incentive_definition_id.payment_rule == 'payment':

    #             if incentive_id.invoice_id.filtered(lambda x: x.amount_residual > 0.0):
    #                 amount = 0.0
    #                 partner_id = line.partner_id
    #             else:
    #                 amount = line.incentive_amount
    #                 partner_id = line.partner_id

    #         res.update({'partner_id': partner_id.id,
    #                     'amount': amount,
    #                     'source_amount':amount,
    #                     'currency_id': incentive_id.currency_id.id,
    #                     'memo': incentive_id.name,
    #                     'date': date.today()})
    #     return res
        #     amount += line.incentive_amount
        #     partner_id = line.partner_id
        # res.update({'partner_id': partner_id.id,
        #             'amount': amount,
        #             'source_amount':amount,
        #             'currency_id': incentive_id.currency_id.id,
        #             'memo': incentive_id.name,
        #             'date': date.today()})
        # return res

    journal_id = fields.Many2one('account.journal', string='Transfer Journal')
    receive_journal_id = fields.Many2one('account.journal', string='Received Journal')
    amount =fields.Monetary(currency_field='currency_id', store=True, readonly=False,string ='Incentive Amount')
    source_amount =fields.Monetary(currency_field='currency_id', store=True, readonly=False,string ='Incentive Amount')
    currency_id = fields.Many2one('res.currency', string='Currency')

    date = fields.Date('Date')
    memo = fields.Char('Memo')
    partner_id = fields.Many2one('res.partner')


    def create_cfd_entry(self, request_incentive_id):
        res = []
        cfd_id = self.env['business.unit'].search([('business_type','=','cfd')])[0]
        partner_id = request_incentive_id.branch_id.partner_id if request_incentive_id.branch_id else request_incentive_id.business_id.partner_id
        amount = request_incentive_id.retain_amount/request_incentive_id.exchange_rate
        # amount = self.amount/request_incentive_id.exchange_rate
        move_line = {'name': self.memo,
                     'partner_id': partner_id.id,
                     'account_id': self.journal_id.default_account_id.id,
                     'business_id': cfd_id.id,
                     'date': self.date,
                     'amount_currency': -self.amount,
                     'credit': amount,
                     'currency_id': self.currency_id.id,
                     'request_incentive_id': request_incentive_id.id, }
        res.append(move_line)

        move_line = {'name': self.memo,
                     'partner_id': partner_id.id,
                     'account_id': cfd_id.aff_account_receivable_id.id,
                     'business_id': cfd_id.id,
                     'date': self.date,
                     'amount_currency': self.amount,
                     'debit': amount,
                     'currency_id': self.currency_id.id,
                     'request_incentive_id': request_incentive_id.id, }
        res.append(move_line)
        line_ids = [(0, 0, l) for l in res]
        move_vals = {
            'partner_id': partner_id.id,
            'journal_id': self.journal_id.id,
            'ref': self.memo,
            'date': self.date,
            'line_ids': line_ids,
        }
        move_id = self.env['account.move'].create(move_vals)
        move_id.action_post()
        # return move_id.action_post()

    def create_bu_br_entry(self, request_incentive_id, partner_id):
        res = []
        branch_id = request_incentive_id.branch_id
        business_id = request_incentive_id.business_id
        # amount = self.currency_id._convert(self.amount,
        #                                             self.env.user.company_id.currency_id,
        #                                             self.env.user.company_id,
        #                                             datetime.today(),
        #                                         )
        # amount = self.amount/request_incentive_id.exchange_rate
        amount = request_incentive_id.retain_amount / request_incentive_id.exchange_rate
        # Bank/Cash Receive
        move_line = {'name': self.memo,
                     'partner_id': partner_id.id,
                     'account_id': self.receive_journal_id.default_account_id.id,
                     'business_id': branch_id and branch_id.id or business_id.id or False,
                     'date': self.date,
                     'amount_currency': self.amount,
                     'debit': amount,
                     'currency_id': self.currency_id.id,
                     'request_incentive_id': request_incentive_id.id, }
        res.append(move_line)

        #Aff:Payble For CFD
        move_line = {'name': self.memo,
                     'partner_id': partner_id.id,
                     'account_id': branch_id and branch_id.aff_account_payable_id.id or business_id.aff_account_payable_id.id,
                     'business_id': branch_id and branch_id.id or business_id.id or False,
                     'date': self.date,
                     'amount_currency': -self.amount,
                     'credit': amount,
                     'currency_id': self.currency_id.id,
                     'request_incentive_id': request_incentive_id.id, }
        res.append(move_line)
        line_ids = [(0, 0, l) for l in res]
        move_vals = {
            'journal_id': self.receive_journal_id.id,
            'ref': self.memo,
            'date': self.date,
            'line_ids': line_ids,
            'hr_br_id':branch_id.id,
            'hr_bu_id':business_id.id,
        }
        move_id = self.env['account.move'].create(move_vals)
        move_id.action_post()

        # Cash Move To Saleperson
        # Bank/Cash to Saleperson
        res = []
        move_line = {'name': self.memo,
                     'partner_id': self.partner_id.id,
                     'account_id': self.receive_journal_id.default_account_id.id,
                     'business_id': branch_id and branch_id.id or business_id.id or False,
                     'date': self.date,
                     'amount_currency': -self.amount,
                     'credit': amount,
                     'currency_id': self.currency_id.id,
                     'request_incentive_id': request_incentive_id.id, }
        res.append(move_line)

        #Close Accured Sale
        move_line = {'name': self.memo,
                     'partner_id': self.partner_id.id,
                     'account_id': branch_id and branch_id.incentive_account_id.id or business_id.incentive_account_id.id,
                     'business_id': branch_id and branch_id.id or business_id.id or False,
                     'date': self.date,
                     'amount_currency': self.amount,
                     'debit': amount,
                     'currency_id': self.currency_id.id,
                     'request_incentive_id': request_incentive_id.id, }
        res.append(move_line)
        line_ids = [(0, 0, l) for l in res]
        move_vals = {
            'journal_id': self.receive_journal_id.id,
            'ref': self.memo,
            'date': self.date,
            'line_ids': line_ids,
            'hr_br_id':branch_id.id,
            'hr_bu_id':business_id.id,
        }
        move_id = self.env['account.move'].create(move_vals)
        move_id.action_post()

        return True

    def create_entry(self):
        for request_id in self.env.context.get('active_ids'):

            request_incentive_id = self.env['incentive.request'].browse(request_id)
        # request_incentive_id = self.env['incentive.request'].browse(self._context.get('active_id'))
            partner_id = self.env['business.unit'].search([('business_type','=','cfd')])[0].partner_id
            self.create_cfd_entry(request_incentive_id)
            self.create_bu_br_entry(request_incentive_id,partner_id)
            request_incentive_id.paid_amount+=self.amount
            for req_line in request_incentive_id.incentive_request_line:
                for line in req_line.normal_incentive_id:
                    line.state = 'retain_withdraw'
            # for line in request_incentive_id.line_ids:
            #     line.state = 'retain_withdraw'
            request_incentive_id.write({'state': 'retain_withdraw'})

    # def create_entry(self):
    #     incentive_id = self.env['normal.incentive.main'].browse(self._context.get('active_id'))
    #     partner_id = self.env['business.unit'].search([('business_type','=','cfd')])[0].partner_id
    #     self.create_cfd_entry(incentive_id)
    #     self.create_bu_br_entry(incentive_id,partner_id)
    #     incentive_id.paid_amount+=self.amount
    #     for line in incentive_id.line_ids:
    #         line.state = 'retain_withdraw'
    #     return incentive_id.write({'state': 'retain_withdraw'})

    def normal_approval(self):
        return self.create_entry()
