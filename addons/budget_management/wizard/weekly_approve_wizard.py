from odoo import models,fields,api, _
from datetime import date
from odoo.exceptions import MissingError

class WeeklyApproval(models.TransientModel):
    _name = 'weekly.approval.wizard'

    @api.model
    def default_get(self, fields):
        res = super(WeeklyApproval, self).default_get(fields)
        amount = 0.0
        active_id = self.env['weekly.budget.request'].browse(self._context.get('active_id'))
        res.update({
                    'amount': active_id.total,
                    'currency_id': active_id.currency_id.id,
                    'memo': active_id.name,
                    'business_id': active_id.business_id.id,
                    'business_type': active_id.business_id.business_type,
                    'date': date.today()})
        return res
    
    def _get_cfd_domain(self):
        return [('bu_br_id', '=', self.env['business.unit'].search([('business_type','=','cfd')], limit=1).id),('type','in',('cash','bank'))]

    journal_id = fields.Many2one('account.journal', string='Transfer Journal', domain=_get_cfd_domain)
    receive_journal_id = fields.Many2one('account.journal', string='Received Journal')
    div_journal_id = fields.Many2one('account.journal', string="Received Journal")
    amount = fields.Float('Amount')
    currency_id = fields.Many2one('res.currency', string='Currency')
    date = fields.Date('Date')
    memo = fields.Char('Memo')

    business_id = fields.Many2one('business.unit',string='Business Unit')
    business_type = fields.Selection(related='business_id.business_type')

    # By THA
    def create_cfd_entry(self, weekly_id):
        res = []
        cfd_id = self.env['business.unit'].search([('business_type','=','cfd')])[0]
        cfd_cash_and_bank_account_id = self.journal_id.default_account_id
        if not cfd_cash_and_bank_account_id:
            raise MissingError(_('Missing cash/bank account for CFD/HO/HQ!!'))      
        amount = self.currency_id._convert(self.amount,
                                    self.env.user.company_id.currency_id,
                                    self.env.user.company_id,
                                    self.date,
                           )
        #Business aff acc received
        move_line = {'name': self.memo,
                     'partner_id': weekly_id.business_id.partner_id.id,#Partner BU/BR
                     'account_id': cfd_id.aff_account_receivable_id.id, #HO/CFD Receivable Account
                     'business_id': cfd_id.id, #HO/CFD side
                     'date': self.date,
                     'debit': amount,
                     'amount_currency': self.amount,
                     'currency_id': self.currency_id.id,
                     'weekly_budget_id': weekly_id.id, }
        res.append(move_line)

        #CFD cash out
        move_line = {'name': self.memo,
                     'partner_id': weekly_id.business_id.partner_id.id,#Partner BU/BR
                     'account_id': cfd_cash_and_bank_account_id.id,#CFD cash/bank Account
                     'business_id': cfd_id.id,#HO/CFD side
                     'date': self.date,
                     'credit': amount,
                     'amount_currency': -self.amount,
                     'currency_id': self.currency_id.id,
                     'weekly_budget_id': weekly_id.id, }
        res.append(move_line)
        line_ids = [(0, 0, l) for l in res]
        move_vals = {
            'partner_id': cfd_id.partner_id.id, # HO Side for Journal Entry
            'journal_id': self.journal_id.id, # Transfer Journal
            'ref': self.memo,
            'date': self.date,
            'line_ids': line_ids,
            'currency_id': self.currency_id.id,
            'weekly_budget_id': weekly_id.id
        }
        move_vals.update({
            'hr_bu_id': cfd_id.id
        })

        move_id = self.env['account.move'].create(move_vals)
        return move_id.action_post()

    def create_bu_br_entry(self, weekly_id):
        res = []
        cfd_id = self.env['business.unit'].search([('business_type','=','cfd')])[0]
        # partner_id = cfd_id.partner_id
        # partner_id = self.env['business.unit'].search([('business_type','=','cfd')])[0].partner_id#comment by THA
        amount = self.currency_id._convert(self.amount,
                                    self.env.user.company_id.currency_id,
                                    self.env.user.company_id,
                                    self.date,
                                )
        # Bank/Cash Receive (Business Unit)
        move_line = {'name': self.memo,
                     'partner_id': cfd_id.partner_id.id, # Partner HO/CFD
                     'account_id': self.receive_journal_id.default_account_id.id, # BU/BR receivable account
                     'business_id': weekly_id.business_id.id, #Bu/Br side
                     'date': self.date,
                     'debit': amount,
                     'amount_currency': self.amount,
                     'currency_id': self.currency_id.id,
                     'weekly_budget_id': weekly_id.id, }
        res.append(move_line)

        #Aff:Payble For CFD
        move_line = {'name': self.memo,
                     'partner_id': cfd_id.partner_id.id, #Partner HO/CFD
                     # 'account_id': weekly_id.business_id.aff_account_payable_id.id,#comment by THA
                     'account_id': weekly_id.business_id.aff_account_payable_id.id,# Bu/Br Payable
                     'business_id': weekly_id.business_id.id, # Bu/Br side
                     'date': self.date,
                     'credit': amount,
                     'amount_currency': -self.amount,
                     'currency_id': self.currency_id.id,
                     'weekly_budget_id': weekly_id.id, }
        res.append(move_line)
        line_ids = [(0, 0, l) for l in res]
        move_vals = {
            'journal_id': self.receive_journal_id.id, # Receive Journal
            'partner_id' : weekly_id.business_id.partner_id.id, # Bu/Br side
            'ref': self.memo,
            'date': self.date,
            'line_ids': line_ids,
            'currency_id': self.currency_id.id,
            'weekly_budget_id': weekly_id.id
        }
        if self.business_id.business_type == 'br':
            move_vals.update({
                'hr_br_id': self.business_id.id
            })
        else:
            move_vals.update({
                'hr_bu_id': self.business_id.id
            })
        move_id = self.env['account.move'].create(move_vals)
        move_id.action_post()

        return True

    # By THA
    def create_div_entry(self, weekly_id):
        res = []
        cfd_cash_and_bank_account_id = False
        partner_id = weekly_id.business_id.partner_id
        cfd_id = self.env['business.unit'].search([('business_type','=','cfd')])[0]
        cfd_journal_ids = self.env['account.journal'].search([('bu_br_id','=',cfd_id.id),('type','=','cash'),('is_transit_jr','=',False)])
        for journal in cfd_journal_ids:
            if journal.default_account_id.currency_id.id == self.currency_id.id:
                cfd_cash_and_bank_account_id = journal.default_account_id
        if not cfd_cash_and_bank_account_id:
            raise MissingError(_('No cash/bank account for CFD/HO/HQ!!'))      
        amount = self.currency_id._convert(self.amount,
                                    self.env.user.company_id.currency_id,
                                    self.env.user.company_id,
                                    self.date,
                                )
        move_line = {'name': self.memo,
                     'partner_id': partner_id.id,
                     'account_id': self.div_journal_id.default_account_id.id,
                     'business_id': weekly_id.business_id.id,
                     'date': self.date,
                     'debit': amount,
                     'amount_currency': self.amount,
                     'currency_id': self.currency_id.id,
                     'weekly_budget_id': weekly_id.id, }
        res.append(move_line)

        move_line = {'name': self.memo,
                     'partner_id': partner_id.id,
                     'account_id': cfd_cash_and_bank_account_id.id,
                     'business_id': cfd_id.id,
                     'date': self.date,
                     'credit': amount,
                     'amount_currency': -self.amount,
                     'currency_id': self.currency_id.id,
                     'weekly_budget_id': weekly_id.id, }
        res.append(move_line)
        line_ids = [(0, 0, l) for l in res]
        move_vals = {
            'partner_id': partner_id.id,
            'journal_id': self.div_journal_id.id,
            'ref': self.memo,
            'date': self.date,
            'line_ids': line_ids,
            'currency_id': self.currency_id.id,
            'weekly_budget_id': weekly_id.id,
        }
        if self.business_id.business_type == 'br':
            move_vals.update({
                'hr_br_id': self.business_id.id
            })
        else:
            move_vals.update({
                'hr_bu_id': self.business_id.id
            })
        move_id = self.env['account.move'].create(move_vals)
        return move_id.action_post()

    def create_entry(self):
        weekly_id = self.env['weekly.budget.request'].browse(self._context.get('active_id'))
        if self.business_id.business_type == 'bu' or self.business_id.business_type == 'br':
            self.create_cfd_entry(weekly_id)
            self.create_bu_br_entry(weekly_id)
        # else:
        #     self.create_div_entry(weekly_id)
        return weekly_id.write({'state': 'paid','received_date':self.date})

    def action_approval(self):
        return self.create_entry()
        