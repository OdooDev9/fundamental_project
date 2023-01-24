from odoo import models, fields, api, _
from datetime import datetime
from odoo.tools.float_utils import float_round
from odoo.exceptions import ValidationError, MissingError

class Expensewizard(models.TransientModel):
    _name = 'expense.wizard'

    @api.model
    def default_get(self, fields):
        res = super(Expensewizard, self).default_get(fields)
        expense_id = self.env['budget.expense'].browse(self._context.get('active_id'))
        res.update({'amount': expense_id.total,
                    'currency_id': expense_id.currency_id.id,
                    'memo': expense_id.name,
                    'date': datetime.today(),
                    'business_id': expense_id.business_id.id,
                    'advance_id': expense_id.advance_id and expense_id.advance_id.id or False,
                    'auto_journal_entry': True if not expense_id.weekly_id and expense_id.expense_type == 'claim' and expense_id.business_id.business_type not in ('div','cfd') else False,
                    'advance': expense_id.expense_type == 'clear' and True or False,
                    'expense_type': expense_id.expense_type,
                    })
        return res

    def _get_cfd_domain(self):
        return [('bu_br_id', '=', self.env['business.unit'].search([('business_type','=','cfd')], limit=1).id),('type','in',('cash','bank'))]

    account_id = fields.Many2one('account.account', 'Expense Account')
    journal_id = fields.Many2one('account.journal', 'Paid By')
    amount = fields.Monetary('Amount')
    currency_id = fields.Many2one('res.currency', 'Currency')
    memo = fields.Char('Memo')
    date = fields.Date('Paid Date')
    advance = fields.Boolean('Claim with advance', default=True)
    advance_id = fields.Many2one('budget.advance',domain="[('state','=','confirm')]")
    issue_date = fields.Date(related="advance_id.issue_date", string="Advance Issue Date")
    diff = fields.Monetary('Diff', compute='get_diff')
    diff_in_company_currency = fields.Monetary('Diff in company currency', compute='get_diff_in_company_currency')
    writeoff_account_id = fields.Many2one('account.account', 'Paid Different In')
    writeoff_label = fields.Char('Description')
    handle = fields.Selection([('open', 'Keep'), ('close', 'Mark as full claim')], default='open')

    business_id = fields.Many2one('business.unit','Business Unit')
    business_type = fields.Selection(related='business_id.business_type')

    have_gain_loss = fields.Boolean('Have Exchange Gain/Loss?')
    gain_loss_amount = fields.Monetary('Gain/Loss Amount')
    exchange_line_account = fields.Many2one('account.account','Gain/Loss Account')
    exchange_gain_loss_journal_id = fields.Many2one('account.journal','Gain/Loss Journal')

    auto_journal_entry = fields.Boolean()

    weekly_journal_id = fields.Many2one('account.journal', string='Transfer Journal', domain=_get_cfd_domain)
    receive_journal_id = fields.Many2one('account.journal', string='Received Journal')
    div_journal_id = fields.Many2one('account.journal', string="Received Journal")

    expense_type = fields.Selection([('clear','Clearance'),('claim','Claim')], string='Expense Type')

    @api.onchange('business_id')
    def onchange_business_id(self):
        if self.business_id:
            if self.business_id.business_type == "br" or self.business_id.business_type == "bu":
                return {'domain': {'journal_id': [('bu_br_id','=',self.business_id.id),('type', 'in', ['bank', 'cash'])]}}
            else:
                return {'domain': {'journal_id': [('bu_br_id', '=', self.env['business.unit'].search([('business_type','=','cfd')], limit=1).id),('type', 'in', ['bank', 'cash'])]}}

    @api.onchange('handle')
    def onchange_handle(self):
        self.writeoff_account_id = self.advance_id.move_id.journal_id.default_account_id.id

    @api.depends('advance_id')
    def get_diff(self):
        if self.advance_id:
            self.diff = self.advance_id.diff - self.amount
        else:
            self.diff = 0.0

    @api.onchange('diff')
    def onchange_diff_amount(self):
        if self.diff > 0:
            self.handle = 'open'
        else:
            self.handle = 'close'

    @api.depends('advance_id')
    def get_diff_in_company_currency(self):
        if self.advance_id:
            advance_diff = self.currency_id._convert(self.advance_id.diff,
                                            self.env.user.company_id.currency_id,
                                            self.env.user.company_id,
                                            self.date,
                                        )
            amount = self.currency_id._convert(self.amount,
                                            self.env.user.company_id.currency_id,
                                            self.env.user.company_id,
                                            self.date,
                                        )
            self.diff_in_company_currency = advance_diff - amount
        else:
            self.diff_in_company_currency = 0.0

    @api.onchange('advance')
    def onchange_advance(self):
        if not self.advance:
            self.advance_id = False

    # @api.onchange('advance_id','date')
    # def onchange_for_gain_loss_amount(self):
    #     if self.advance_id and self.date:
    #         amount_at_advance_date = self.currency_id._convert(self.advance_id.total,
    #                                 self.env.user.company_id.currency_id,
    #                                 self.env.user.company_id,
    #                                 self.advance_id.date,                                   
    #                                 # self.advance_id.issue_date,                                   
    #                             )
    #         amount_at_expense_date = self.currency_id._convert(self.advance_id.total,
    #                                 self.env.user.company_id.currency_id,
    #                                 self.env.user.company_id,
    #                                 self.date,                                   
    #                             )
    #         diff = amount_at_advance_date - amount_at_expense_date
    #         if diff > 0:
    #             self.have_gain_loss = True
    #         else:
    #             self.have_gain_loss = False
    #         self.gain_loss_amount = diff

    def get_move_line(self):
        res = []
        expense_id = self.env['budget.expense'].browse(self._context.get('active_id'))
        for line in expense_id.line_ids:
            amount = line.currency_id._convert(line.amount,
                                            self.env.user.company_id.currency_id,
                                            self.env.user.company_id,
                                            self.date,
                                        )
            res.append({'name': line.name,
                        'account_id': line.account_id.id,
                        'analytic_account_id': line.analytic_account_id.id,
                        'date': self.date,
                        'partner_id': expense_id.partner_id.id,
                        'amount_currency': line.amount,
                        'debit': amount,
                        'currency_id': expense_id.currency_id.id,
                        'is_rounding_line': False,
                        'exp_move_id': expense_id.id, })
        return res

    def create_entry(self):
        expense_id = self.env['budget.expense'].browse(self._context.get('active_id'))
        res = self.get_move_line()
        claim_amount = self.amount
        company_id =  self.env.user.company_id

        if self.diff_in_company_currency != 0.0 and self.handle == 'close':
            diff = self.diff_in_company_currency
            # diff = self.currency_id._convert(self.diff,
            #                                 company_id.currency_id,
            #                                 company_id,
            #                                 self.date,  
            #                             )
            res.append({
                        'name': self.writeoff_label,
                        'currency_id': self.currency_id.id,
                        'amount_currency': self.diff,
                        'credit': diff < 0.0 and -diff or 0.0,
                        'debit': diff > 0.0 and diff or 0.0,
                        'date_maturity': self.date,
                        'partner_id': expense_id.partner_id.id,
                        'account_id': self.writeoff_account_id.id,
                        'exp_move_id': expense_id.id,
                        'is_rounding_line': False,
                    })
            claim_amount += self.diff
            self.advance_id.state = 'close'
        if self.diff == 0.0:
            self.advance_id.state='close'
        claim_amount_currency = claim_amount
        claim_amount = self.currency_id._convert(claim_amount,
                                            company_id.currency_id,
                                            company_id,
                                            self.date,     
                                        )
        move_line = {'name': expense_id.employee_id.name,
                     'account_id': self.advance_id.account_id.id or self.journal_id.default_account_id.id,
                     'analytic_account_id': self.advance_id and self.advance_id.analytic_account_id.id or False,
                     'date': self.date,
                     'partner_id': expense_id.partner_id.id,
                     'amount_currency': -claim_amount_currency,
                     'credit': claim_amount,
                     'currency_id': self.currency_id.id,
                     'is_rounding_line': False,
                     'exp_move_id': expense_id.id, }
        res.append(move_line)
        line_ids = [(0, 0, l) for l in res]
        move_vals = {
            'journal_id': self.advance_id.move_id.journal_id.id or self.journal_id.id,
            'ref': self.memo,
            'date': self.date,
            'line_ids': line_ids,
        }
        
        move_id = self.env['account.move'].create(move_vals)
        move_id.post()

        #THA for auto journal entry
        if not expense_id.weekly_id and expense_id.expense_type == 'claim':
        # if not expense_id.weekly_id and expense_id.budget_type == 'include' and expense_id.expense_type == 'claim':
            self.create_auto_journal_entry_for_weekly_budget()

        # For Multi currency
        # if self.expense_id.currency_id != self.currency_id and self.date != self.issue_date:
        # if self.have_gain_loss and self.gain_loss_amount > 0:
        #     self.currency_exchange_gain_loss()

        if self.handle == 'close':
            return expense_id.write({'move_id': move_id.id, 'claim_amount': claim_amount_currency, 'state': 'close'})
        else:
            return expense_id.write({'move_id': move_id.id, 'claim_amount': claim_amount_currency, 'state': 'paid'})

    def action_paid(self):
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
        expense_id = self.env['budget.expense'].browse(self._context.get('active_id'))
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
                     'partner_id': self.business_id.partner_id.id, # Partner Bu/Br
                     'account_id': cfd_id.aff_account_receivable_id.id, #HO aff Receive
                     'business_id': cfd_id.id, # HO side
                     'date': self.date,
                     'debit': amount,
                     'amount_currency': self.amount,
                     'currency_id': self.currency_id.id,
                     'exp_move_id': expense_id.id
                     }
        res.append(move_line)

        #CFD cash out
        move_line = {'name': self.memo,
                     'partner_id': self.business_id.partner_id.id, # Partner Bu/Br
                     'account_id': cfd_cash_and_bank_account_id.id, # HO cash/bank account
                     'business_id': cfd_id.id, #HO side
                     'date': self.date,
                     'credit': amount,
                     'amount_currency': -self.amount,
                     'currency_id': self.currency_id.id,
                     'exp_move_id': expense_id.id
                     }
        res.append(move_line)
        line_ids = [(0, 0, l) for l in res]
        move_vals = {
            'partner_id': self.weekly_journal_id.bu_br_id.partner_id.id, #Transfer Journal
            'journal_id': self.weekly_journal_id.id, #Transfer Journal
            'ref': self.memo,
            'date': self.date,
            'line_ids': line_ids,
            'currency_id': self.currency_id.id,
        }
        move_id = self.env['account.move'].create(move_vals)
        return move_id.action_post()

    def create_bu_br_entry(self):
        expense_id = self.env['budget.expense'].browse(self._context.get('active_id'))
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
                     'account_id': self.receive_journal_id.default_account_id.id, # Bu/Br Receivable(Cash/bank)
                     'business_id': self.business_id.id, # Bu/Br side
                     'date': self.date,
                     'debit': amount,
                     'amount_currency': self.amount,
                     'currency_id': self.currency_id.id,
                     'exp_move_id': expense_id.id
                     }
        res.append(move_line)

        #Aff:Payble For CFD
        move_line = {'name': self.memo,
                     'partner_id': cfd_id.partner_id.id, # Parter HO
                     # 'account_id': weekly_id.business_id.aff_account_payable_id.id,#comment by THA
                     'account_id': self.business_id.aff_account_payable_id.id,# Bu/Br payable
                     'business_id': self.business_id.id, # Bu/Br side
                     'date': self.date,
                     'credit': amount,
                     'amount_currency': -self.amount,
                     'currency_id': self.currency_id.id,
                     'exp_move_id': expense_id.id
                     }
        res.append(move_line)
        line_ids = [(0, 0, l) for l in res]
        move_vals = {
            'journal_id': self.receive_journal_id.id, # Receive Journal
            'partner_id' : self.business_id.partner_id.id,
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
        expense_id = self.env['budget.expense'].browse(self._context.get('active_id'))
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
                     'exp_move_id': expense_id.id
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
                     'exp_move_id': expense_id.id
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

    def currency_exchange_gain_loss(self):
        expense_id = self.env['budget.expense'].browse(self._context.get('active_id'))
        res = []
        exchange_line_account = False
        partner_id = self.business_id.partner_id
        # print("self.advance_id.total............",self.advance_id.total)
        amount_at_advance_date = self.currency_id._convert(self.advance_id.total,
                                    self.env.user.company_id.currency_id,
                                    self.env.user.company_id,
                                    self.advance_id.date,                                   
                                    # self.advance_id.issue_date,                                   
                                )
        amount_at_expense_date = self.currency_id._convert(self.advance_id.total,
                                    self.env.user.company_id.currency_id,
                                    self.env.user.company_id,
                                    self.date,                                   
                                )
        diff = amount_at_advance_date - amount_at_expense_date
        amount_for_diff = self.currency_id._convert(diff,
                                    self.currency_id,
                                    self.env.user.company_id,
                                    self.date,                                   
                                )
        # print("diff................",diff)
        # print("amount_at_advance_date........",amount_at_advance_date)
        # print("amount_at_expense_date........",amount_at_expense_date)
        move_line = {'name': _('Currency exchange rate difference (cash basis)'),
                 'account_id': self.business_id.currency_exchange_loss_account_id if diff < 0.0 else self.business_id.currency_exchange_gain_account_id,
                 'business_id': self.business_id.id,
                 'date': self.date,
                 'debit': diff if diff > 0.0 else 0.0,
                 'credit': diff if diff < 0.0 else 0.0,
                 'amount_currency': - amount_for_diff if diff < 0.0 else amount_for_diff,
                 'currency_id': self.currency_id.id,
                 'exp_move_id': expense_id.id
                 }
        res.append(move_line)
        ar_move_line = {'name': _('Currency exchange rate difference (cash basis)'),
                 'account_id': self.business_id.property_account_receivable_id.id,
                 'business_id': self.business_id.id,
                 'date': self.date,
                 'debit': diff if diff < 0.0 else 0.0,
                 'credit':  diff if diff > 0.0 else 0.0,
                 'amount_currency': - amount_for_diff if diff > 0.0 else amount_for_diff,
                 'currency_id': self.currency_id.id,
                 'exp_move_id': expense_id.id
                 }
        res.append(ar_move_line)
        line_ids = [(0, 0, l) for l in res]
        expense_id = self.env['budget.expense'].browse(self._context.get('active_id'))
        move_vals = {
            'partner_id': partner_id.id,
            'journal_id': self.exchange_gain_loss_journal_id.id,
            'ref': expense_id.name,
            'date': self.date,
            'line_ids': line_ids,
            'currency_id': self.currency_id.id,
        }
        # print("move_vals.............",move_vals)
        move_id = self.env['account.move'].create(move_vals)
        return move_id.action_post()
        # raise UserError("just stop")      
