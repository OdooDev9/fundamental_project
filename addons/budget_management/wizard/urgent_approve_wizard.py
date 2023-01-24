from odoo import models,fields,api
from datetime import date

class UrgentApproval(models.TransientModel):
    _name = 'urgent.approval.wizard'

    @api.model
    def default_get(self, fields):
        res = super(UrgentApproval, self).default_get(fields)
        amount = 0.0
        active_id = self.env['urgent.budget.request'].browse(self._context.get('active_id'))
        res.update({
                    'amount': active_id.total,
                    'currency_id': active_id.currency_id.id,
                    'memo': active_id.name,
                    'business_id': active_id.business_id.id,
                    'date': date.today()})
        return res
    
    def _get_cfd_domain(self):
        return [('bu_br_id', '=', self.env['business.unit'].search([('code', '=', 'CFD')], limit=1).id)]

    journal_id = fields.Many2one('account.journal', string='Transfer Journal', domain=_get_cfd_domain)
    receive_journal_id = fields.Many2one('account.journal', string='Received Journal')
    amount = fields.Float('Amount')
    currency_id = fields.Many2one('res.currency', string='Currency')
    date = fields.Date('Date')
    memo = fields.Char('Memo')

    business_id = fields.Many2one('business.unit',string='Business Unit')

    def create_cfd_entry(self, urgent_id):
        res = []
        partner_id = urgent_id.business_id.partner_id
        cfd_id = self.env['business.unit'].search([('business_type','=','cfd')])[0]
        amount = self.currency_id._convert(self.amount,
                                            self.env.user.company_id.currency_id,
                                            self.env.user.company_id,
                                            self.date,
                                        )
        move_line = {'name': self.memo,
                     'partner_id': partner_id.id,
                     'account_id': self.journal_id.default_account_id.id,
                     'business_id': cfd_id.id,
                     'date': self.date,
                     'credit': amount,
                     'amount_currency': -self.amount,
                     'currency_id': self.currency_id.id,
                     'urgent_budget_id': urgent_id.id, }
        res.append(move_line)

        move_line = {'name': self.memo,
                     'partner_id': partner_id.id,
                     'account_id': cfd_id.aff_account_receivable_id.id,
                     'business_id': cfd_id.id,
                     'date': self.date,
                     'debit': amount,
                     'amount_currency': self.amount,
                     'currency_id': self.currency_id.id,
                     'urgent_budget_id': urgent_id.id, }
        res.append(move_line)
        line_ids = [(0, 0, l) for l in res]
        move_vals = {
            'partner_id': partner_id.id,
            'journal_id': self.journal_id.id,
            'ref': self.memo,
            'date': self.date,
            'line_ids': line_ids,
            'currency_id': self.currency_id.id,
        }
        move_id = self.env['account.move'].create(move_vals)
        return move_id.action_post()

    def create_bu_br_entry(self, urgent_id):
        res = []
        partner_id = self.env['business.unit'].search([('business_type','=','cfd')])[0].partner_id
        amount = self.currency_id._convert(self.amount,
                                            self.env.user.company_id.currency_id,
                                            self.env.user.company_id,
                                            self.date,
                                        )
        # Bank/Cash Receive
        move_line = {'name': self.memo,
                     'partner_id': partner_id.id,
                     'account_id': self.receive_journal_id.default_account_id.id,
                     'business_id': urgent_id.business_id.id,
                     'date': self.date,
                     'debit': amount,
                     'amount_currency': self.amount,
                     'currency_id': self.currency_id.id,
                     'urgent_budget_id': urgent_id.id, }
        res.append(move_line)

        #Aff:Payble For CFD
        move_line = {'name': self.memo,
                     'partner_id': partner_id.id,
                     'account_id': urgent_id.business_id.aff_account_payable_id.id,
                     'business_id': urgent_id.business_id.id,
                     'date': self.date,
                     'credit': amount,
                     'amount_currency': -self.amount,
                     'currency_id': self.currency_id.id,
                     'urgent_budget_id': urgent_id.id, }
        res.append(move_line)
        line_ids = [(0, 0, l) for l in res]
        move_vals = {
            'journal_id': self.receive_journal_id.id,
            'ref': self.memo,
            'date': self.date,
            'line_ids': line_ids,
            'currency_id': self.currency_id.id,
        }
        move_id = self.env['account.move'].create(move_vals)
        move_id.action_post()

        return True

    def create_entry(self):
        urgent_id = self.env['urgent.budget.request'].browse(self._context.get('active_id'))
        self.create_cfd_entry(urgent_id)
        self.create_bu_br_entry(urgent_id)
        return urgent_id.write({'state': 'paid','received_date':self.date})

    def action_approval(self):
        return self.create_entry()