from re import T
from odoo import api, fields, models, _
from datetime import date,datetime
from odoo.exceptions import AccessError, UserError, ValidationError

class AreaTargetSale(models.TransientModel):
    _name = 'area.sale.target.wizard'
    _description = 'Normal Incentive Approval Wizard'

    @api.model
    def default_get(self, fields):
        res = super(AreaTargetSale, self).default_get(fields)
        incentive_id = self.env['area.incentive.definition'].browse(self._context.get('active_id'))
        amount = incentive_id.incentive
        res.update({
                    'amount': amount,
                    'source_amount':amount,
                    'currency_id': incentive_id.incentive_currency_id.id,
                    'memo': incentive_id.name,
                    'date': date.today()})
        return res

    journal_id = fields.Many2one('account.journal', string='Transfer Journal', domain="[('type', 'in', ['bank', 'cash'])]")
    receive_journal_id = fields.Many2one('account.journal', string='Received Journal', domain="[('type', 'in', ['bank', 'cash'])]")
    amount = fields.Monetary(currency_field='currency_id', store=True, readonly=False,string='Incentive Amount')
    source_amount = fields.Monetary(currency_field='currency_id', store=True, readonly=False,string='Source Incentive Amount')
    currency_id = fields.Many2one('res.currency', string='Currency')
    date = fields.Date('Date')
    memo = fields.Char('Memo')


    @api.onchange('currency_id')
    def _onchange_currency(self):
        for rec in self:  
            rec.amount = rec.env.user.company_id.currency_id._convert(rec.source_amount,rec.currency_id,rec.env.user.company_id,self.date)

    def create_cfd_entry(self, incentive_id):
        res = []
        #CFD Cash Out Entry
        cfd_id = self.env['business.unit'].search([('business_type','=','cfd')])[0]
        amount = self.currency_id._convert(self.amount,
                                            self.env.user.company_id.currency_id,
                                            self.env.user.company_id,
                                            self.date,
                                        )
        move_line = {'name': self.memo,
                     'partner_id': incentive_id.business_id.partner_id.id,
                     'account_id': self.journal_id.default_account_id.id,
                     'business_id': cfd_id.id,
                     'date': self.date,
                     'amount_currency': -self.amount,
                     'credit': amount,
                     'currency_id': self.currency_id.id,
                     'asm_id': incentive_id.id, }
        res.append(move_line)

        move_line = {'name': self.memo,
                     'partner_id': incentive_id.business_id.partner_id.id,
                     'account_id': cfd_id.aff_account_receivable_id.id,
                     'business_id': cfd_id.id,
                     'date': self.date,
                     'amount_currency': self.amount,
                     'debit': amount,
                     'currency_id': self.currency_id.id,
                     'asm_id': incentive_id.id, }
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
        return True

    def create_bu_br_entry(self, incentive_id):
        res = []
        partner_id = self.env['business.unit'].search([('business_type','=','cfd')])[0].partner_id
        business_id = incentive_id.business_id
        amount = self.currency_id._convert(self.amount,
                                            self.env.user.company_id.currency_id,
                                            self.env.user.company_id,
                                            self.date,
                                        )
        # Bank/Cash Receive
        move_line = {'name': self.memo,
                     'partner_id': partner_id.id,
                     'account_id': self.receive_journal_id.default_account_id.id,
                     'business_id': incentive_id.business_id.id,
                     'date': self.date,
                     'amount_currency': self.amount,
                     'debit': amount,
                     'currency_id': self.currency_id.id,
                     'asm_id': incentive_id.id, }
        res.append(move_line)

        #Aff:Payble For CFD
        move_line = {'name': self.memo,
                     'partner_id': partner_id.id,
                     'account_id': business_id.aff_account_payable_id.id,
                     'business_id': incentive_id.business_id.id,
                     'date': self.date,
                     'amount_currency': -self.amount,
                     'credit': amount,
                     'currency_id': self.currency_id.id,
                     'asm_id': incentive_id.id, }
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
                     'partner_id': incentive_id.user_id.partner_id.id,
                     'account_id': self.receive_journal_id.default_account_id.id,
                     'business_id': incentive_id.business_id.id,
                     'date': self.date,
                     'amount_currency': -self.amount,
                     'credit': amount,
                     'currency_id': self.currency_id.id,
                     'asm_id': incentive_id.id, }
        res.append(move_line)

        #Close Accured Sale
        move_line = {'name': self.memo,
                     'partner_id': incentive_id.user_id.partner_id.id,
                     'account_id': business_id.asm_account_id.id,
                     'business_id': incentive_id.business_id.id,
                     'date': self.date,
                     'amount_currency': self.amount,
                     'debit': amount,
                     'currency_id': self.currency_id.id,
                     'asm_id': incentive_id.id, }
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
        incentive_id = self.env['area.incentive.definition'].browse(self._context.get('active_id'))
        self.create_cfd_entry(incentive_id)
        self.create_bu_br_entry(incentive_id)
        return incentive_id.write({'state': 'incentive_withdraw'})

    def normal_approval(self):
        return self.create_entry()