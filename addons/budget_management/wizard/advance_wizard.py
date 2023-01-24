from odoo import models, fields, api, _
from datetime import datetime, date
from odoo.exceptions import MissingError,UserError


class Advancewizard(models.TransientModel):
    _name = 'advance.wizard'

    @api.model
    def default_get(self, fields):
        res = super(Advancewizard, self).default_get(fields)
        advance_id = self.env['budget.advance'].browse(self._context.get('active_id'))
        res.update({'amount': advance_id.total,
                    'currency_id': advance_id.currency_id.id,
                    'memo': advance_id.name,
                    'date': datetime.today(),
                    'auto_journal_entry': True if not advance_id.weekly_id and advance_id.business_id.business_type not in ('div','cfd') else False,
                    'business_id': advance_id.business_id.id,
                    'account_id': advance_id.business_id.advance_account_id.id})
        return res

    def _get_cfd_domain(self):
        return [('bu_br_id', '=', self.env['business.unit'].search([('business_type','=','cfd')], limit=1).id),('type','in',('cash','bank'))]

    def _get_account_domain(self):
        if self.business_id.business_type == "br" or self.business_id.business_type == "bu":
            return [('bu_br_id','=',self.business_id.id)]
        else:
            return [('bu_br_id', '=', self.env['business.unit'].search([('business_type','=','cfd')], limit=1).id)]

    def _get_journal_domain(self):
        if self.business_id.business_type == "br" or self.business_id.business_type == "bu":
            return [('bu_br_id','=',self.business_id.id),('type', 'in', ['bank', 'cash'])]
        else:
            return [('bu_br_id', '=', self.env['business.unit'].search([('business_type','=','cfd')], limit=1).id),('type', 'in', ['bank', 'cash'])]

    business_id = fields.Many2one('business.unit','Business Unit')
    business_type = fields.Selection(related='business_id.business_type')
    account_id = fields.Many2one('account.account', 'Advance Account')
    journal_id = fields.Many2one('account.journal', 'Paid By' )
    amount = fields.Float('Amount')
    currency_id = fields.Many2one('res.currency', 'Currency')
    memo = fields.Char('Memo')
    date = fields.Date('Paid Date')
    auto_journal_entry = fields.Boolean()

    weekly_journal_id = fields.Many2one('account.journal', string='Transfer Journal', domain=_get_cfd_domain)
    receive_journal_id = fields.Many2one('account.journal', string='Received Journal',domain=_get_journal_domain)
    div_journal_id = fields.Many2one('account.journal', string="Received Journal")

    @api.onchange('business_id')
    def onchange_business_id(self):
        if self.business_id:
            if self.business_id.business_type == "br" or self.business_id.business_type == "bu":
                return {'domain': {'journal_id': [('bu_br_id','=',self.business_id.id),('type', 'in', ['bank', 'cash'])]}}
            else:
                return {'domain': {'journal_id': [('bu_br_id', '=', self.env['business.unit'].search([('business_type','=','cfd')], limit=1).id),('type', 'in', ['bank', 'cash'])]}}

    @api.onchange('business_id')
    def onchange_business_id_for_advance_account(self):
        if self.business_id:
            if self.business_id.business_type == "br" or self.business_id.business_type == "bu":
                return {'domain': {'account_id': [('bu_br_id','=',self.business_id.id)]}}
            else:
                return {'domain': {'account_id': [('bu_br_id', '=', self.env['business.unit'].search([('business_type','=','cfd')], limit=1).id)]}}

    def create_entry(self):
        advance_id = self.env['budget.advance'].browse(self._context.get('active_id'))
        res = []
        amount = self.currency_id._convert(self.amount,
                                            self.env.user.company_id.currency_id,
                                            self.env.user.company_id,
                                            self.date,
                                        )
        move_line = {'name': advance_id.employee_id.name,
                     'account_id': self.account_id.id,
                     'partner_id': self.business_id.partner_id.id,
                     'analytic_account_id': advance_id.analytic_account_id.id,
                     'date': self.date,
                     'amount_currency': self.amount,
                     'debit': amount,
                     'currency_id': self.currency_id.id,
                     'advance_move_id': advance_id.id, }
        res.append(move_line)

        move_line = {'name': advance_id.employee_id.name,
                     'account_id': self.journal_id.default_account_id.id,
                     'partner_id': self.business_id.partner_id.id,
                     'analytic_account_id': advance_id.analytic_account_id.id,
                     'date': self.date,
                     'amount_currency': -self.amount,
                     'credit': amount,
                     'currency_id': self.currency_id.id,
                     'advance_move_id': advance_id.id, }
        res.append(move_line)
        line_ids = [(0, 0, l) for l in res]
        move_vals = {
            'journal_id': self.journal_id.id,
            'ref': self.memo,
            'date': self.date,
            'line_ids': line_ids,
            'advance_move_id': advance_id.id
        }
        move_id = self.env['account.move'].create(move_vals)
        move_id.action_post()

        #THA for auto journal entry
        if not advance_id.weekly_id:
            self.create_auto_journal_entry_for_weekly_budget()

        return advance_id.write({'move_id': move_id.id, 'account_id': self.account_id.id, 'issue_date':self.date, 'state': 'paid', 'paid': True})

    def action_paid(self):
        if not self.account_id:
            raise UserError('Need a Advance account configuration in your BU/BR/DIV set up.')
        return self.create_entry()

    #THA for auto journal entry
    def create_auto_journal_entry_for_weekly_budget(self):
        if self.business_id.business_type == 'bu' or self.business_id.business_type == 'br':
            self.create_cfd_entry()
            self.create_bu_br_entry()
        # else:
        #     self.create_div_entry()

    # By THA
    def create_cfd_entry(self):
        advance_id = self.env['budget.advance'].browse(self._context.get('active_id'))
        res = []
        cfd_id = self.env['business.unit'].search([('business_type','=','cfd')])[0]
        cfd_cash_and_bank_account_id = self.weekly_journal_id.default_account_id
        # partner_id = weekly_id.business_id.partner_id
        # cfd_id = self.env['business.unit'].search([('business_type','=','cfd')])[0]
        # cfd_journal_ids = self.env['account.journal'].search([('bu_br_id','=',cfd_id.id),('type','=','cash'),('is_transit_jr','=',False)])
        # for journal in cfd_journal_ids:
        #     if journal.default_account_id.currency_id.id == self.currency_id.id:
        #         cfd_cash_and_bank_account_id = journal.default_account_id
        if not cfd_cash_and_bank_account_id:
            raise MissingError(_('Missing cash/bank account for CFD/HO/HQ!!'))      
        amount = self.currency_id._convert(self.amount,
                                    self.env.user.company_id.currency_id,
                                    self.env.user.company_id,
                                    self.date,
                           )
        #Business aff acc received
        move_line = {'name': self.memo,
                     'partner_id': self.business_id.partner_id.id, #Partner Bu/Br
                     'account_id': cfd_id.aff_account_receivable_id.id, # CFD Aff Receive
                     'business_id': cfd_id.id, #Cfd/Ho Side
                     'date': self.date,
                     'debit': amount,
                     'amount_currency': self.amount,
                     'currency_id': self.currency_id.id,
                     'advance_move_id': advance_id.id
                     }
        res.append(move_line)

        #CFD cash out
        move_line = {'name': self.memo,
                     'partner_id': self.business_id.partner_id.id, #Partner Bu/Br
                     'account_id': cfd_cash_and_bank_account_id.id, #Ho Cash
                     'business_id': cfd_id.id, # Cfd/Ho Side
                     'date': self.date,
                     'credit': amount,
                     'amount_currency': -self.amount,
                     'currency_id': self.currency_id.id,
                     'advance_move_id': advance_id.id
                     }
        res.append(move_line)
        line_ids = [(0, 0, l) for l in res]
        move_vals = {
            'partner_id': self.weekly_journal_id.bu_br_id.partner_id.id,
            'journal_id': self.weekly_journal_id.id, #Transfer
            'ref': self.memo,
            'date': self.date,
            'line_ids': line_ids,
            'currency_id': self.currency_id.id,
        }
        move_id = self.env['account.move'].create(move_vals)
        return move_id.action_post()

    def create_bu_br_entry(self):
        advance_id = self.env['budget.advance'].browse(self._context.get('active_id'))
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
                     'partner_id': cfd_id.partner_id.id, #Partner HO
                     'account_id': self.receive_journal_id.default_account_id.id, #Bu/Br receive
                     'business_id': self.business_id.id, #Bu/Br side
                     'date': self.date,
                     'debit': amount,
                     'amount_currency': self.amount,
                     'currency_id': self.currency_id.id,
                     'advance_move_id': advance_id.id
                     }
        res.append(move_line)

        #Aff:Payble For CFD
        move_line = {'name': self.memo,
                     'partner_id': cfd_id.partner_id.id, # Partner HO
                     # 'account_id': weekly_id.business_id.aff_account_payable_id.id,#comment by THA
                     'account_id': self.business_id.aff_account_payable_id.id,#Bu/BR aff Payable
                     'business_id': self.business_id.id,
                     'date': self.date,
                     'credit': amount,
                     'amount_currency': -self.amount,
                     'currency_id': self.currency_id.id,
                     'advance_move_id': advance_id.id
                     }
        res.append(move_line)
        line_ids = [(0, 0, l) for l in res]
        move_vals = {
            'journal_id': self.receive_journal_id.id, # receive Journal
            'partner_id' : self.business_id.partner_id.id, # Bu/Br side
            'ref': self.memo,
            'date': self.date,
            'line_ids': line_ids,
            'currency_id': self.currency_id.id,
        }
        move_id = self.env['account.move'].create(move_vals)
        move_id.action_post()

        return True

    # By THA
    def create_div_entry(self):
        advance_id = self.env['budget.advance'].browse(self._context.get('active_id'))
        res = []
        cfd_cash_and_bank_account_id = False
        partner_id = self.business_id.partner_id
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
                     'business_id': self.business_id.id,
                     'date': self.date,
                     'debit': amount,
                     'amount_currency': self.amount,
                     'currency_id': self.currency_id.id,
                     'advance_move_id': advance_id.id
                     }
        res.append(move_line)

        move_line = {'name': self.memo,
                     'partner_id': partner_id.id,
                     'account_id': cfd_cash_and_bank_account_id.id,
                     'business_id': cfd_id.id,
                     'date': self.date,
                     'credit': amount,
                     'amount_currency': -self.amount,
                     'currency_id': self.currency_id.id,
                     'advance_move_id': advance_id.id
                     }
        res.append(move_line)
        line_ids = [(0, 0, l) for l in res]
        move_vals = {
            'partner_id': partner_id.id,
            'journal_id': self.div_journal_id.id,
            'ref': self.memo,
            'date': self.date,
            'line_ids': line_ids,
            'currency_id': self.currency_id.id,
        }
        move_id = self.env['account.move'].create(move_vals)
        return move_id.action_post()
