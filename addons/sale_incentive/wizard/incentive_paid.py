from re import T
from odoo import api, fields, models, _
from datetime import date,datetime
from odoo.exceptions import AccessError, UserError, ValidationError

class NormalIncentiveApproval(models.TransientModel):
    _name = 'incentive.approval.wizard'
    _description = 'Normal Incentive Approval Wizard'


    @api.model
    def default_get(self, fields):

        res = super(NormalIncentiveApproval, self).default_get(fields)
        amount = 0.0
        currency_id = self.env.ref('base.MMK') 
        partner_id = None
        request_incentive_id = self.env['incentive.request'].browse(self._context.get('active_id'))
        if not request_incentive_id.exchange_rate:
            raise UserError(_('Please, Define Myanmar Currency Exchange for Incentive Payment'))

       
        if request_incentive_id.manager == True:
            for req_line in request_incentive_id.incentive_request_line:
                for incen in req_line.normal_incentive_id:
                    for line in incen.line_ids.filtered(lambda x: x.sale_person_type  in ['sale_manager']): 
                        partner_id = line.partner_id.id
            amount = request_incentive_id.manager_amount
        else:
            for req_line in request_incentive_id.incentive_request_line:
                for incen in req_line.normal_incentive_id:
                    for line in incen.line_ids.filtered(lambda x: x.sale_person_type  in ['sale_person', 'gov_salesperson']): 
                       
                        partner_id = line.partner_id.id
            amount = request_incentive_id.saleman_amount
            

     
           
        
        res.update({    'partner_id':partner_id,
                        'amount': amount,
                        'currency_id': currency_id.id,
                        'memo': request_incentive_id.name,
                        'date': date.today()})
        return res

        # for line in incentive_id.line_ids.filtered(lambda x: x.sale_person_type in ['sale_person', 'gov_salesperson']):
        #     if incentive_id.incentive_definition_id.payment_rule == 'invoice':
        #         amount = line.incentive_amount
        #         partner_id = line.partner_id
        #     elif incentive_id.incentive_definition_id.payment_rule == 'both':
        #         if incentive_id.paid_amount > 0.0:
        #             amount = incentive_id.due_amount
        #             partner_id = line.partner_id
        #         else:
        #             amount = line.incentive_amount/2
        #             partner_id = line.partner_id
        #     # else:
        #     elif incentive_id.incentive_definition_id.payment_rule == 'payment':

        #         if incentive_id.invoice_id.filtered(lambda x: x.amount_residual > 0.0):
        #             amount = 0.0
        #             partner_id = line.partner_id
        #         else:
        #             amount = line.incentive_amount
        #             partner_id = line.partner_id

           

    # @api.model
    # def default_get(self, fields):
    #     res = super(NormalIncentiveApproval, self).default_get(fields)
    #     amount = 0.0
    #     incentive_id = self.env['normal.incentive.main'].browse(self._context.get('active_id'))
    #     for line in incentive_id.line_ids.filtered(lambda x: x.sale_person_type in ['sale_person', 'gov_salesperson']):
    #         if incentive_id.incentive_definition_id.payment_rule == 'invoice':
    #             amount = line.incentive_amount
    #             partner_id = line.partner_id
    #         elif incentive_id.incentive_definition_id.payment_rule == 'both':
    #             if incentive_id.paid_amount > 0.0:
    #                 amount = incentive_id.due_amount
    #                 partner_id = line.partner_id
    #             else:
    #                 amount = line.incentive_amount/2
    #                 partner_id = line.partner_id
    #         # else:
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

        # for line in incentive_id.line_ids.filtered(lambda x: x.sale_person_type in ['sale_person', 'gov_salesperson']):
        #     amount += line.incentive_amount
        #     partner_id = line.partner_id
        # if incentive_id.manager:
        #     amount = incentive_id.line_ids.filtered(lambda x: x.sale_person_type=='sale_manager').incentive_amount
        #     partner_id = incentive_id.line_ids.filtered(lambda x: x.sale_person_type=='sale_manager').partner_id
        # res.update({'partner_id': partner_id.id,
        #             'amount': amount,
        #             'source_amount':amount,
        #             'currency_id': incentive_id.currency_id.id,
        #             'memo': incentive_id.name,
        #             'date': date.today()})
        # return res

    journal_id = fields.Many2one('account.journal', string='Transfer Journal', domain="[('type', 'in', ['bank', 'cash'])]")
    receive_journal_id = fields.Many2one('account.journal', string='Received Journal', domain="[('type', 'in', ['bank', 'cash'])]")
    amount =fields.Monetary(currency_field='currency_id', store=True, readonly=False,string='Incentive Amount')
    # source_amount =fields.Monetary(currency_field='currency_id', store=True, readonly=False,string='Source Incentive Amount')
    currency_id = fields.Many2one('res.currency', string='Currency')
    date = fields.Date('Date')
    memo = fields.Char('Memo')
    partner_id = fields.Many2one('res.partner')

    # @api.onchange('currency_id')
    # def _onchange_currency(self):
    #     for rec in self:
    #         rec.amount = rec.env.user.company_id.currency_id._convert(rec.source_amount,rec.currency_id,rec.env.user.company_id,self.date)
    # def create_cfd_entry(self, incentive_id):
    #     res = []
    #     cfd_id = self.env['business.unit'].search([('business_type','=','cfd')])[0]
    #     partner_id = incentive_id.branch_id.partner_id if incentive_id.branch_id else incentive_id.business_id.partner_id
    #     amount = 0.0
    #     currency_amount = 0.0
    #     for incen in incentive_id.line_ids.filtered(lambda x: x.sale_person_type in ['bu_br', 'gov_pooling']):
    #         amount +=incen.incentive_amount
    #         currency_amount = self.env.user.company_id.currency_id._convert(amount,
    #                                                 self.currency_id,
    #                                                 self.env.user.company_id,
    #                                                 datetime.today(),
    #                                             )
    #     incentive_amount = self.currency_id._convert(self.amount+currency_amount,
    #                                                 self.env.user.company_id.currency_id,
    #                                                 self.env.user.company_id,
    #                                                 datetime.today(),
    #                                             )
    #     move_line = {'name': self.memo,
    #                  'partner_id': partner_id.id,
    #                  'account_id': self.journal_id.default_account_id.id,
    #                  'business_id': cfd_id.id,
    #                  'date': self.date,
    #                  'amount_currency': -(self.amount+amount),
    #                  'credit':incentive_amount,
    #                  'currency_id': self.currency_id.id,
    #                  'incentive_id': incentive_id.id, }
    #     res.append(move_line)

    #     move_line = {'name': self.memo,
    #                  'partner_id': partner_id.id,
    #                  'account_id': cfd_id.aff_account_receivable_id.id,
    #                  'business_id': cfd_id.id,
    #                  'date': self.date,
    #                  'amount_currency': self.amount+amount,
    #                  'debit': incentive_amount,
    #                  'currency_id': self.currency_id.id,
    #                  'incentive_id': incentive_id.id, }
    #     res.append(move_line)
    #     line_ids = [(0, 0, l) for l in res]
    #     move_vals = {
    #         'journal_id': self.journal_id.id,
    #         'ref': self.memo,
    #         'date': self.date,
    #         'line_ids': line_ids,
    #     }
    #     move_id = self.env['account.move'].create(move_vals)
    #     move_id.action_post()
    #     res = []
    #     # Bank Pooling
    #     if amount > 0.0:
    #         amount_currency = amount
    #         amount = self.currency_id._convert(amount,
    #                                             self.env.user.company_id.currency_id,
    #                                             self.env.user.company_id,
    #                                             datetime.today(),
    #                                         )
    #         move_line = {'name': self.memo,
    #                     'partner_id': partner_id.id,
    #                     'account_id': cfd_id.aff_account_payable_id.id,
    #                     'business_id': cfd_id.id,
    #                     'date': self.date,
    #                     'amount_currency': -amount_currency,
    #                     'credit': amount,
    #                     'currency_id': self.currency_id.id,
    #                     'incentive_id': incentive_id.id, }
    #         res.append(move_line)

    #         if not self.journal_id.bank_pooling_account:
    #             raise UserError(_('Define bank pooling account in transfer journal.'))  

    #         move_line = {'name': self.memo,
    #                     'partner_id': partner_id.id,
    #                     'account_id': self.journal_id.bank_pooling_account.id,
    #                     'business_id': cfd_id.id,
    #                     'date': self.date,
    #                     'amount_currency': amount_currency,
    #                     'debit': amount,
    #                     'currency_id': self.currency_id.id,
    #                     'incentive_id': incentive_id.id, }
    #         res.append(move_line)
    #         line_ids = [(0, 0, l) for l in res]
    #         move_vals = {
    #             'journal_id': self.journal_id.id,
    #             'partner_id': partner_id.id,
    #             'ref': self.memo,
    #             'date': self.date,
    #             'line_ids': line_ids,
    #         }
    #         move_id = self.env['account.move'].create(move_vals)
    #         move_id.action_post()
    #     return True

    def create_cfd_entry(self, request_incentive_id):
        res = []
        cfd_id = self.env['business.unit'].search([('business_type','=','cfd')])[0]
        partner_id = request_incentive_id.branch_id.partner_id if request_incentive_id.branch_id else request_incentive_id.business_id.partner_id
        amount = 0.0
        pooling_currency_amount = 0.0
        # for incen in incentive_id.line_ids.filtered(lambda x: x.sale_person_type in ['bu_br', 'gov_pooling']):
        #     amount +=incen.incentive_amount
        #     currency_amount = self.env.user.company_id.currency_id._convert(amount,
        #                                             self.currency_id,
        #                                             self.env.user.company_id,
        #                                             datetime.today(),
        #                                         )
        # incentive_amount = self.currency_id._convert(self.amount+currency_amount,
        #                                             self.env.user.company_id.currency_id,
        #                                             self.env.user.company_id,
        #                                             datetime.today(),
        #                                         )
        pooling_currency_amount += request_incentive_id.pooling_amount
        amount = pooling_currency_amount/request_incentive_id.exchange_rate
        incentive_amount = (pooling_currency_amount + self.amount)/request_incentive_id.exchange_rate
        
        move_line = {'name': self.memo,
                     'partner_id': partner_id.id,
                     'account_id': self.journal_id.default_account_id.id,
                     'business_id': cfd_id.id,
                     'date': self.date,
                     'amount_currency': - (pooling_currency_amount + self.amount),
                     'credit':incentive_amount,
                     'currency_id': self.currency_id.id,
                     'request_incentive_id': request_incentive_id.id, }
        res.append(move_line)

        move_line = {'name': self.memo,
                     'partner_id': partner_id.id,
                     'account_id': cfd_id.aff_account_receivable_id.id,
                     'business_id': cfd_id.id,
                     'date': self.date,
                     'amount_currency': pooling_currency_amount + self.amount,
                     'debit': incentive_amount,
                     'currency_id': self.currency_id.id,
                     'request_incentive_id': request_incentive_id.id, }
        res.append(move_line)
        line_ids = [(0, 0, l) for l in res]
        move_vals = {
            'journal_id': self.journal_id.id,
            'ref': self.memo,
            'date': self.date,
            'line_ids': line_ids,
        }
        move_id = self.env['account.move'].create(move_vals)
        move_id.action_post()
        res = []
        # Bank Pooling
        if amount > 0.0:
            amount_currency = amount
            # amount = self.currency_id._convert(amount,
            #                                     self.env.user.company_id.currency_id,
            #                                     self.env.user.company_id,
            #                                     datetime.today(),
            #                                 )
            move_line = {'name': self.memo,
                        'partner_id': partner_id.id,
                        'account_id': cfd_id.aff_account_payable_id.id,
                        'business_id': cfd_id.id,
                        'date': self.date,
                        'amount_currency': -pooling_currency_amount,
                        'credit': amount,
                        'currency_id': self.currency_id.id,
                        'request_incentive_id': request_incentive_id.id, }
            res.append(move_line)

            if not self.journal_id.bank_pooling_account:
                raise UserError(_('Define bank pooling account in transfer journal.'))  

            move_line = {'name': self.memo,
                        'partner_id': partner_id.id,
                        'account_id': self.journal_id.bank_pooling_account.id,
                        'business_id': cfd_id.id,
                        'date': self.date,
                        'amount_currency': pooling_currency_amount,
                        'debit': amount,
                        'currency_id': self.currency_id.id,
                        'request_incentive_id': request_incentive_id.id, }
            res.append(move_line)
            line_ids = [(0, 0, l) for l in res]
            move_vals = {
                'journal_id': self.journal_id.id,
                'partner_id': partner_id.id,
                'ref': self.memo,
                'date': self.date,
                'line_ids': line_ids,
            }
            move_id = self.env['account.move'].create(move_vals)
            move_id.action_post()
        return True
    def create_bu_br_entry(self, request_incentive_id):
        res = []
        partner_id = self.env['business.unit'].search([('business_type','=','cfd')])[0].partner_id
        branch_id = request_incentive_id.branch_id
        business_id = request_incentive_id.business_id
        pooling_amount = 0.0
        pooling_currency_amount = 0.0
        pooling_currency_amount += request_incentive_id.pooling_amount
        pooling_amount = pooling_currency_amount/request_incentive_id.exchange_rate
        incentive_amount = self.amount/request_incentive_id.exchange_rate
        # incentive_amount = (pooling_currency_amount + self.amount)/request_incentive_id.exchange_rate
        # for incen in request_incentive_id.line_ids.filtered(lambda x: x.sale_person_type in ['bu_br', 'gov_pooling']):
        #     amount+=incen.incentive_amount
        #     currency_amount = self.env.user.company_id.currency_id._convert(amount,
        #                                             self.currency_id,
        #                                             self.env.user.company_id,
        #                                             datetime.today(),
        #                                         )
        
        # incentive_amount = self.currency_id._convert(self.amount,
        #                                         self.env.user.company_id.currency_id,
        #                                         self.env.user.company_id,
        #                                         datetime.today(),
        #                                     )
        # pooling_amount = self.currency_id._convert(currency_amount,
        #                                         self.env.user.company_id.currency_id,
        #                                         self.env.user.company_id,
        #                                         datetime.today(),
        #                                     )
        # Bank/Cash Receive
        move_line = {'name': self.memo,
                     'partner_id': partner_id.id,
                     'account_id': self.receive_journal_id.default_account_id.id,
                     'business_id': not request_incentive_id.manager and  branch_id and branch_id.id or business_id.id or False,
                     'date': self.date,
                     'amount_currency': self.amount,
                     'debit': incentive_amount,
                     'currency_id': self.currency_id.id,
                     'request_incentive_id': request_incentive_id.id, }
        res.append(move_line)

        #Aff:Payble For CFD
        move_line = {'name': self.memo,
                     'partner_id': partner_id.id,
                     'account_id': not request_incentive_id.manager and branch_id and branch_id.aff_account_payable_id.id or business_id.aff_account_payable_id.id,
                     'business_id': not request_incentive_id.manager and  branch_id and branch_id.id or business_id.id or False,
                     'date': self.date,
                     'amount_currency': -(self.amount+pooling_currency_amount),
                     'credit': incentive_amount+pooling_amount,
                     'currency_id': self.currency_id.id,
                     'request_incentive_id': request_incentive_id.id,  }
        res.append(move_line)

        #Aff:Receivable For CFD
        if pooling_amount > 0.0:
            move_line = {'name': self.memo,
                        'partner_id': partner_id.id,
                        'account_id': not request_incentive_id.manager and branch_id and branch_id.aff_account_receivable_id.id or business_id.aff_account_receivable_id.id,
                        'business_id': not request_incentive_id.manager and branch_id and branch_id.id or business_id.id or False,
                        'date': self.date,
                        'amount_currency': pooling_currency_amount,
                        'debit': pooling_amount,
                        'currency_id': self.currency_id.id,
                        'request_incentive_id':request_incentive_id.id, }
            res.append(move_line)

        line_ids = [(0, 0, l) for l in res]
        move_vals = {
            'journal_id': self.receive_journal_id.id,
            'ref': self.memo,
            'date': self.date,
            'line_ids': line_ids,
            'hr_bu_id':business_id.id,
            'hr_br_id':branch_id.id,
        }
        move_id = self.env['account.move'].create(move_vals)
        move_id.action_post()

        # Cash Move To Saleperson
        # Bank/Cash to Saleperson
        res = []
        move_line = {'name': self.memo,
                     'partner_id': self.partner_id.id,
                     'account_id': self.receive_journal_id.default_account_id.id,
                     'business_id':not request_incentive_id.manager and branch_id and branch_id.id or business_id.id or False,
                     'date': self.date,
                     'amount_currency': -self.amount,
                     'credit': incentive_amount,
                     'currency_id': self.currency_id.id,
                     'request_incentive_id':request_incentive_id.id, }
        res.append(move_line)

        #Close Accured Sale
        if request_incentive_id.manager:
            incentive_account_id = business_id.asm_account_id
        else:
            incentive_account_id = branch_id and branch_id.incentive_account_id or business_id.incentive_account_id
        move_line = {'name': self.memo,
                        'partner_id': self.partner_id.id,
                        'account_id': incentive_account_id.id,
                        'business_id':not request_incentive_id.manager and branch_id and branch_id.id or business_id.id or False,
                        'date': self.date,
                        'amount_currency': self.amount,
                        'debit': incentive_amount,
                        'currency_id': self.currency_id.id,
                        'request_incentive_id':request_incentive_id.id, }
        res.append(move_line)
      
        line_ids = [(0, 0, l) for l in res]
        move_vals = {
            'journal_id': self.receive_journal_id.id,
            'ref': self.memo,
            'date': self.date,
            'line_ids': line_ids,
            'hr_bu_id':business_id.id,
            'hr_br_id':branch_id.id,
        }
        move_id = self.env['account.move'].create(move_vals)
        move_id.action_post()

        return True

    # def create_bu_br_entry(self, incentive_id):
    #     res = []
    #     partner_id = self.env['business.unit'].search([('business_type','=','cfd')])[0].partner_id
    #     branch_id = incentive_id.branch_id
    #     business_id = incentive_id.business_id
    #     amount = 0.0
    #     currency_amount = 0.0
    #     for incen in incentive_id.line_ids.filtered(lambda x: x.sale_person_type in ['bu_br', 'gov_pooling']):
    #         amount+=incen.incentive_amount
    #         currency_amount = self.env.user.company_id.currency_id._convert(amount,
    #                                                 self.currency_id,
    #                                                 self.env.user.company_id,
    #                                                 datetime.today(),
    #                                             )
        
    #     incentive_amount = self.currency_id._convert(self.amount,
    #                                             self.env.user.company_id.currency_id,
    #                                             self.env.user.company_id,
    #                                             datetime.today(),
    #                                         )
    #     pooling_amount = self.currency_id._convert(currency_amount,
    #                                             self.env.user.company_id.currency_id,
    #                                             self.env.user.company_id,
    #                                             datetime.today(),
    #                                         )
    #     # Bank/Cash Receive
    #     move_line = {'name': self.memo,
    #                  'partner_id': partner_id.id,
    #                  'account_id': self.receive_journal_id.default_account_id.id,
    #                  'business_id': not incentive_id.manager and branch_id and branch_id.id or business_id.id or False,
    #                  'date': self.date,
    #                  'amount_currency': self.amount,
    #                  'debit': incentive_amount,
    #                  'currency_id': self.currency_id.id,
    #                  'incentive_id': incentive_id.id, }
    #     res.append(move_line)

    #     #Aff:Payble For CFD
    #     move_line = {'name': self.memo,
    #                  'partner_id': partner_id.id,
    #                  'account_id': not incentive_id.manager and branch_id and branch_id.aff_account_payable_id.id or business_id.aff_account_payable_id.id,
    #                  'business_id': not incentive_id.manager and branch_id and branch_id.id or business_id.id or False,
    #                  'date': self.date,
    #                  'amount_currency': -(self.amount+amount),
    #                  'credit': incentive_amount+amount,
    #                  'currency_id': self.currency_id.id,
    #                  'incentive_id': incentive_id.id, }
    #     res.append(move_line)

    #     #Aff:Receivable For CFD
    #     if amount > 0.0:
    #         move_line = {'name': self.memo,
    #                     'partner_id': partner_id.id,
    #                     'account_id': not incentive_id.manager and branch_id and branch_id.aff_account_receivable_id.id or business_id.aff_account_receivable_id.id,
    #                     'business_id': not incentive_id.manager and branch_id and branch_id.id or business_id.id or False,
    #                     'date': self.date,
    #                     'amount_currency': amount,
    #                     'debit': pooling_amount,
    #                     'currency_id': self.currency_id.id,
    #                     'incentive_id': incentive_id.id, }
    #         res.append(move_line)

    #     line_ids = [(0, 0, l) for l in res]
    #     move_vals = {
    #         'journal_id': self.receive_journal_id.id,
    #         'ref': self.memo,
    #         'date': self.date,
    #         'line_ids': line_ids,
    #     }
    #     move_id = self.env['account.move'].create(move_vals)
    #     move_id.action_post()

    #     # Cash Move To Saleperson
    #     # Bank/Cash to Saleperson
    #     res = []
    #     move_line = {'name': self.memo,
    #                  'partner_id': self.partner_id.id,
    #                  'account_id': self.receive_journal_id.default_account_id.id,
    #                  'business_id': not incentive_id.manager and branch_id and branch_id.id or business_id.id or False,
    #                  'date': self.date,
    #                  'amount_currency': -self.amount,
    #                  'credit': incentive_amount,
    #                  'currency_id': self.currency_id.id,
    #                  'incentive_id': incentive_id.id, }
    #     res.append(move_line)

    #     #Close Accured Sale
    #     if incentive_id.manager:
    #         incentive_account_id = business_id.asm_account_id
    #     else:
    #         incentive_account_id = branch_id and branch_id.incentive_account_id or business_id.incentive_account_id
    #     move_line = {'name': self.memo,
    #                  'partner_id': self.partner_id.id,
    #                  'account_id': incentive_account_id.id,
    #                  'business_id': not incentive_id.manager and branch_id and branch_id.id or business_id.id or False,
    #                  'date': self.date,
    #                  'amount_currency': self.amount,
    #                  'debit': incentive_amount,
    #                  'currency_id': self.currency_id.id,
    #                  'incentive_id': incentive_id.id, }
    #     res.append(move_line)
    #     line_ids = [(0, 0, l) for l in res]
    #     move_vals = {
    #         'journal_id': self.receive_journal_id.id,
    #         'ref': self.memo,
    #         'date': self.date,
    #         'line_ids': line_ids,
    #     }
    #     move_id = self.env['account.move'].create(move_vals)
    #     move_id.action_post()

    #     return True

    def create_entry(self):
        request_incentive_id = self.env['incentive.request'].browse(self._context.get('active_id'))
        self.create_cfd_entry(request_incentive_id)
        self.create_bu_br_entry(request_incentive_id)
        request_incentive_id.paid_amount+=self.amount
        request_incentive_id.journal_id = self.journal_id.id
        request_incentive_id.receive_journal_id = self.receive_journal_id.id
        for req_line in request_incentive_id.incentive_request_line:
            for line in req_line.normal_incentive_id:
                line.state = 'incentive_withdraw'
        return request_incentive_id.write({'state': 'incentive_withdraw'})

        

        # Normal Incentive Entry
        # incentive_id = self.env['normal.incentive.main'].browse(self._context.get('active_id'))
        # self.create_cfd_entry(incentive_id)
        # self.create_bu_br_entry(incentive_id)
        # incentive_id.paid_amount+=self.amount
        # for line in incentive_id.line_ids:
        #     line.state = 'incentive_withdraw'
        # return incentive_id.write({'state': 'incentive_withdraw'})

    def normal_approval(self):
        # Saleman Payment from Incentive Request
        request_incentive_id = self.env['incentive.request'].browse(self._context.get('active_id'))
        if not request_incentive_id.exchange_rate:
            raise UserError(_('Please, Define Myanmar Currency Exchange for Incentive Payment'))

        return self.create_entry()

        # //Normal Incentive Paid From Wizard
        # incentive_id = self.env['normal.incentive.main'].browse(self._context.get('active_id'))
        # if incentive_id.incentive_definition_id.payment_rule == 'payment':
        #     if incentive_id.invoice_id.payment_state != 'paid':
        #         raise ValidationError(_("All invoices haven't paid yet. Please pay for unpaid invoices."))


        # return self.create_entry()


# ************************* Sale Target***************************************************

class SaleTargetIncentive(models.Model):
    _name = 'sale.target.incentive.wizard'
    _description = 'Sale Target Incentive'

    @api.model
    def default_get(self, fields):
        res = super(SaleTargetIncentive, self).default_get(fields)
        amount = 0.0
        incentive_id = self.env['personal.sale.target'].browse(self._context.get('active_id'))
        if incentive_id.payment_rule == 'invoice':
            amount = incentive_id.incentive_amount
        elif incentive_id.payment_rule == 'both':
            if incentive_id.paid_amount > 0.0:
                amount = incentive_id.due_amount
            else:
                amount = incentive_id.incentive_amount/2
        else:
            if incentive_id.invoice_ids.filtered(lambda x: x.amount_residual > 0.0):
                amount = 0.0
            else:
                amount = incentive_id.incentive_amount

        res.update({
                    'amount': amount,
                    'currency_id': incentive_id.currency_id.id,
                    'memo': incentive_id.name,
                    'date': date.today()})
        return res

    journal_id = fields.Many2one('account.journal', string='Transfer Journal', domain="[('type', 'in', ['bank', 'cash'])]")
    receive_journal_id = fields.Many2one('account.journal', string='Received Journal', domain="[('type', 'in', ['bank', 'cash'])]")
    amount = fields.Float('Incentive Amount')
    currency_id = fields.Many2one('res.currency', string='Currency')
    date = fields.Date('Date')
    memo = fields.Char('Memo')

    def create_cfd_entry(self, incentive_id):
        res = []
        #CFD Cash Out Entry
        cfd_id = self.env['business.unit'].search([('business_type','=','cfd')])[0]
        partner_id = incentive_id.branch_id.partner_id if incentive_id.branch_id else incentive_id.business_id.partner_id
        amount= amount_currency = (self.amount+incentive_id.bu_br_incentive_amount) if incentive_id.paid_amount == 0.0 else self.amount
        amount = self.currency_id._convert(amount,
                                            self.env.user.company_id.currency_id,
                                            self.env.user.company_id,
                                            self.date,
                                        )
        move_line = {'name': self.memo,
                     'partner_id': partner_id.id,
                     'account_id': self.journal_id.default_account_id.id,
                     'business_id': cfd_id.id,
                     'date': self.date,
                     'amount_currency': -amount_currency,
                     'credit': amount,
                     'currency_id': self.currency_id.id,
                     'personal_target_id': incentive_id.id, }
        res.append(move_line)

        move_line = {'name': self.memo,
                     'partner_id': partner_id.id,
                     'account_id': cfd_id.aff_account_receivable_id.id,
                     'business_id': cfd_id.id,
                     'date': self.date,
                     'amount_currency': amount_currency,
                     'debit': amount,
                     'currency_id': self.currency_id.id,
                     'personal_target_id': incentive_id.id, }
        res.append(move_line)
        line_ids = [(0, 0, l) for l in res]
        move_vals = {
            'journal_id': self.journal_id.id,
            'ref': self.memo,
            'date': self.date,
            'line_ids': line_ids,
        }
        move_id = self.env['account.move'].create(move_vals)
        move_id.action_post()
        #Bank Pooling Entry
        if incentive_id.paid_amount == 0.0:
            res = []
            amount = self.currency_id._convert(incentive_id.bu_br_incentive_amount,
                                                self.env.user.company_id.currency_id,
                                                self.env.user.company_id,
                                                self.date,
                                            )
            if amount > 0.0:
                move_line = {'name': self.memo,
                            'partner_id': partner_id.id,
                            'account_id': cfd_id.aff_account_payable_id.id,
                            'business_id': cfd_id.id,
                            'date': self.date,
                            'amount_currency': -incentive_id.bu_br_incentive_amount,
                            'credit': amount,
                            'currency_id': self.currency_id.id,
                            'personal_target_id': incentive_id.id, }
                res.append(move_line)

                if not self.journal_id.bank_pooling_account:
                    raise UserError(_('Define bank pooling account in transfer journal.'))  

                move_line = {'name': self.memo,
                            'partner_id': partner_id.id,
                            'account_id': self.journal_id.bank_pooling_account.id,
                            'business_id': cfd_id.id,
                            'date': self.date,
                            'amount_currency': incentive_id.bu_br_incentive_amount,
                            'debit': amount,
                            'currency_id': self.currency_id.id,
                            'personal_target_id': incentive_id.id, }
                res.append(move_line)
                line_ids = [(0, 0, l) for l in res]
                move_vals = {
                    'journal_id': self.journal_id.id,
                    'partner_id': cfd_id.partner_id.id,
                    'ref': self.memo,
                    'date': self.date,
                    'line_ids': line_ids,
                }
                move_id = self.env['account.move'].create(move_vals)
                move_id.action_post()
        return True

    def create_bu_br_entry(self, incentive_id):
        res = []
        partner_id = self.env['business.unit'].search([('business_type','=','cfd')])[0].partner_id
        branch_id = incentive_id.branch_id
        business_id = incentive_id.business_id
        pooling_amount = self.currency_id._convert(incentive_id.bu_br_incentive_amount,
                                            self.env.user.company_id.currency_id,
                                            self.env.user.company_id,
                                            self.date,
                                        )
        incentive_amount = self.currency_id._convert(self.amount,
                                            self.env.user.company_id.currency_id,
                                            self.env.user.company_id,
                                            self.date,
                                        )
        # Bank/Cash Receive
        move_line = {'name': self.memo,
                     'partner_id': partner_id.id,
                     'account_id': self.receive_journal_id.default_account_id.id,
                     'business_id': branch_id and branch_id.id or business_id.id or False,
                     'date': self.date,
                     'amount_currency': self.amount,
                     'debit': incentive_amount,
                     'currency_id': self.currency_id.id,
                     'personal_target_id': incentive_id.id, }
        res.append(move_line)

        #Aff:Payble For CFD
        move_line = {'name': self.memo,
                     'partner_id': partner_id.id,
                     'account_id': branch_id and branch_id.aff_account_payable_id.id or business_id.aff_account_payable_id.id,
                     'business_id': branch_id and branch_id.id or business_id.id or False,
                     'date': self.date,
                     'amount_currency':-(self.amount+incentive_id.bu_br_incentive_amount) if incentive_id.paid_amount == 0.0 else -incentive_amount,
                     'credit': incentive_amount+pooling_amount if incentive_id.paid_amount == 0.0 else incentive_amount,
                     'currency_id': self.currency_id.id,
                     'personal_target_id': incentive_id.id, }
        res.append(move_line)

        #Aff:Receivable For CFD
        if pooling_amount > 0.0 and incentive_id.paid_amount == 0.0:
            move_line = {'name': self.memo,
                        'partner_id': partner_id.id,
                        'account_id': branch_id and branch_id.aff_account_receivable_id.id or business_id.aff_account_receivable_id.id,
                        'business_id': branch_id and branch_id.id or business_id.id or False,
                        'date': self.date,
                        'amount_currency': incentive_id.bu_br_incentive_amount,
                        'debit': pooling_amount,
                        'currency_id': self.currency_id.id,
                        'personal_target_id': incentive_id.id, }
            res.append(move_line)

        line_ids = [(0, 0, l) for l in res]
        move_vals = {
            'journal_id': self.receive_journal_id.id,
            'ref': self.memo,
            'date': self.date,
            'line_ids': line_ids,
        }
        move_id = self.env['account.move'].create(move_vals)
        move_id.action_post()

        # Cash Move To Saleperson
        # Bank/Cash to Saleperson
        res = []
        move_line = {'name': self.memo,
                     'partner_id': incentive_id.sale_person_id.partner_id.id,
                     'account_id': self.receive_journal_id.default_account_id.id,
                     'business_id': branch_id and branch_id.id or business_id.id or False,
                     'date': self.date,
                     'amount_currency': -self.amount,
                     'credit': incentive_amount,
                     'currency_id': self.currency_id.id,
                     'personal_target_id': incentive_id.id, }
        res.append(move_line)

        #Close Accured Sale
        move_line = {'name': self.memo,
                     'partner_id': incentive_id.sale_person_id.partner_id.id,
                     'account_id': branch_id and branch_id.incentive_account_id.id or business_id.incentive_account_id.id,
                     'business_id': branch_id and branch_id.id or business_id.id or False,
                     'date': self.date,
                     'amount_currency': self.amount,
                     'debit': incentive_amount,
                     'currency_id': self.currency_id.id,
                     'personal_target_id': incentive_id.id, }
        res.append(move_line)
        line_ids = [(0, 0, l) for l in res]
        move_vals = {
            'journal_id': self.receive_journal_id.id,
            'ref': self.memo,
            'date': self.date,
            'line_ids': line_ids,
        }
        move_id = self.env['account.move'].create(move_vals)
        move_id.action_post()

        return True

    def create_entry(self):
        incentive_id = self.env['personal.sale.target'].browse(self._context.get('active_id'))
        self.create_cfd_entry(incentive_id)
        self.create_bu_br_entry(incentive_id)
        paid_amount = incentive_id.paid_amount + self.amount
        due_amount = incentive_id.due_amount - self.amount
        if due_amount > 0.0:
            state = 'incentive_partially_withdraw'
        else:
            state = 'incentive_withdraw'
        return incentive_id.write({'state': state,'paid_amount':paid_amount})

    def normal_approval(self):
        return self.create_entry()
