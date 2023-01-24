from odoo import api, fields, models, Command, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from odoo.tools import float_compare, date_utils, email_split, email_re, html_escape, is_html_empty
from odoo.tools.misc import formatLang, format_date, get_lang
from dateutil.relativedelta import relativedelta
from datetime import date, timedelta
from collections import defaultdict
from contextlib import contextmanager
from itertools import zip_longest
from hashlib import sha256
from json import dumps

import ast
import json
import re
import warnings


class account_payment(models.Model):
    _inherit = "account.payment"

    # def _default_fine_journal_id(self):

    #     if self.env.user.current_bu_br_id:
    #         jous = self.env['account.journal'].search([('hr_br_id','=',self.env.user.current_bu_br_id.id)])
    #         for jou in jous:
    #             if  'Fine' in jou.name:
    #                 return jou.id
    #     return False

    is_installment = fields.Boolean(string="Is Installment", default=False)
    # invoice_installment_id =fields.Manay2one('invoice.installment.line')

    fine_journal_id = fields.Many2one('account.journal', string="Fine Journal")

    installment_origin_amount = fields.Float(
        string="Installment Origin Amount")
    # amount = fields.Monetary(currency_field='currency_id', store=True, readonly=False,
    #     compute='_compute_amount')

    @api.model_create_multi
    def create(self, vals_list):
        fine_vals_list = []
        write_off_line_vals_list = []
        for vals in vals_list:
            fine_vals_list.append(vals.pop('fine_line_vals', None))

            write_off_line_vals_list.append(
                vals.get('write_off_line_vals', None))

        payments = super(account_payment, self).create(vals_list)

        if fine_vals_list:

            self.write_fine_val_to_move_line(
                write_off_line_vals_list, fine_vals_list, payments)

        return payments

    def write_fine_val_to_move_line(self, write_off_lines, fine_vals, payments):
        for i, pay in enumerate(payments):

            fine_line_vals = fine_vals[i]
            counter_part_line = None
            for move_line in pay._prepare_move_line_default_vals(write_off_line_vals=write_off_lines[i]):
                if move_line['account_id'] == pay.destination_account_id.id:
                    # print(move_line['account_id'])
                    # print(pay.destination_account_id.id)
                    counter_part_line = move_line
                    # print(counter_part_line, 'part')
            if not counter_part_line:
                UserError('Counter Part Not Found')

            counter_part_move_line = None
            for move_line in pay.move_id.line_ids:
                if move_line.account_id.id == pay.destination_account_id.id:
                    counter_part_move_line = move_line
            if not counter_part_move_line:
                UserError('Move Line Not Found')
            amount = 0
            if fine_line_vals:
                # currency = self.env['res.currency'].browse(['currency_id'])
                amount = fine_line_vals['amount']

                fine_balance = pay.currency_id._convert(
                    amount, pay.company_id.currency_id, pay.company_id, pay.date)

                counterpart_amount_currency = counter_part_line['amount_currency'] + amount
                counterpart_amount_balance = pay.currency_id._convert(
                    counterpart_amount_currency, pay.company_id.currency_id, pay.company_id, pay.date)
                fine_ammount_currency = -amount

                # print([
                #             (1, counter_part_move_line.id, {
                #                 'amount_currency': counterpart_amount_currency,
                #                 'debit': counter_part_line['debit'] + fine_balance if
                #                 counter_part_line['debit'] > 0.0 else 0.0,
                #                 'credit': -counter_part_line['credit'] - fine_balance if
                #                 counter_part_line['credit'] < 0.0 else 0.0,
                #             }),
                #             (0, 0, {
                #                 'name': 'Fine amount',
                #                 'date_maturity': counter_part_line['date_maturity'],
                #                 'amount_currency': fine_ammount_currency,
                #                 'currency_id': self.currency_id.id,
                #                 'debit': 0.0,
                #                 'credit': -fine_balance,
                #                 'partner_id': counter_part_line['partner_id'],
                #                 'account_id': counter_part_line['account_id'],
                #             })
                #         ])

                pay.move_id.write(
                    {
                        'line_ids': [
                            (1, counter_part_move_line.id, {
                                'amount_currency': counterpart_amount_currency,
                                'debit': 0.0,
                                'credit': -counterpart_amount_balance,
                            }),
                            (0, 0, {
                                'name': fine_line_vals['name'] or None,
                                'date_maturity': counter_part_line['date_maturity'],
                                'amount_currency': fine_ammount_currency,
                                'currency_id': counter_part_line['currency_id'],
                                'debit': 0.0,
                                'credit': fine_balance,
                                'partner_id': counter_part_line['partner_id'],
                                'account_id': fine_line_vals['account_id'] or None,
                                'is_fine_line': True,
                            })
                        ]
                    }
                )

    def _synchronize_from_moves(self, changed_fields):
        ''' Update the account.payment regarding its related account.move.
        Also, check both models are still consistent.
        :param changed_fields: A set containing all modified fields on account.move.
        '''
        if self._context.get('skip_account_move_synchronization'):
            return

        for pay in self.with_context(skip_account_move_synchronization=True):

            # After the migration to 14.0, the journal entry could be shared between the account.payment and the
            # account.bank.statement.line. In that case, the synchronization will only be made with the statement line.
            if pay.move_id.statement_line_id:
                continue

            move = pay.move_id
            move_vals_to_write = {}
            payment_vals_to_write = {}

            if 'journal_id' in changed_fields:
                if pay.journal_id.type not in ('bank', 'cash'):
                    raise UserError(
                        _("A payment must always belongs to a bank or cash journal."))

            if 'line_ids' in changed_fields:
                all_lines = move.line_ids
                liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()
                removed_fine_line_counter_line = self.env['account.move.line']
                for counter_line in counterpart_lines:
                    if not counter_line.is_fine_line:
                        removed_fine_line_counter_line |= counter_line
                counterpart_lines = removed_fine_line_counter_line
                # print(counterpart_lines)
                if len(liquidity_lines) != 1:
                    raise UserError(_(
                        "Journal Entry %s is not valid. In order to proceed, the journal items must "
                        "include one and only one outstanding payments/receipts account.",
                        move.display_name,
                    ))

                if len(counterpart_lines) != 1:
                    raise UserError(_(
                        "Journal Entry %s is not valid. In order to proceed, the journal items must "
                        "include one and only one receivable/payable account (with an exception of "
                        "internal transfers).",
                        move.display_name,
                    ))

                if writeoff_lines and len(writeoff_lines.account_id) != 1:
                    raise UserError(_(
                        "Journal Entry %s is not valid. In order to proceed, "
                        "all optional journal items must share the same account.",
                        move.display_name,
                    ))

                if any(line.currency_id != all_lines[0].currency_id for line in all_lines):
                    raise UserError(_(
                        "Journal Entry %s is not valid. In order to proceed, the journal items must "
                        "share the same currency.",
                        move.display_name,
                    ))

                if any(line.partner_id != all_lines[0].partner_id for line in all_lines):
                    raise UserError(_(
                        "Journal Entry %s is not valid. In order to proceed, the journal items must "
                        "share the same partner.",
                        move.display_name,
                    ))

                if counterpart_lines.account_id.user_type_id.type == 'receivable':
                    partner_type = 'customer'
                else:
                    partner_type = 'supplier'

                liquidity_amount = liquidity_lines.amount_currency

                move_vals_to_write.update({
                    'currency_id': liquidity_lines.currency_id.id,
                    'partner_id': liquidity_lines.partner_id.id,
                })
                payment_vals_to_write.update({
                    'amount': abs(liquidity_amount),
                    'partner_type': partner_type,
                    'currency_id': liquidity_lines.currency_id.id,
                    'destination_account_id': counterpart_lines.account_id.id,
                    'partner_id': liquidity_lines.partner_id.id,
                })
                if liquidity_amount > 0.0:
                    payment_vals_to_write.update({'payment_type': 'inbound'})
                elif liquidity_amount < 0.0:
                    payment_vals_to_write.update({'payment_type': 'outbound'})

            move.write(move._cleanup_write_orm_values(
                move, move_vals_to_write))
            pay.write(move._cleanup_write_orm_values(
                pay, payment_vals_to_write))

    @api.model
    def default_get(self, fields):
        rec = super(account_payment, self).default_get(fields)
        ctx = self.env.context
        if ctx.get('default_amount'):
            rec.update({'amount': ctx['default_amount']})
        return rec

    @api.model
    def _compute_payment_amount(self, invoices, currency, journal, date):
        total = super(account_payment, self)._compute_payment_amount(
            invoices, currency, journal, date)
        ctx = self.env.context
        if ctx.get('default_amount'):
            return ctx['default_amount']
        return total

    @api.depends('invoice_ids', 'amount', 'payment_date', 'currency_id', 'payment_type')
    def _compute_payment_difference(self):
        draft_payments = self.filtered(
            lambda p: p.invoice_ids and p.state == 'draft')
        for pay in draft_payments:
            payment_amount = -pay.amount if pay.payment_type == 'outbound' else pay.amount

            if pay.is_installment:
                currency_id = pay.currency_id
                for i in pay.invoice_ids:
                    currency_id = i.currency_id
                    break
                origin_amount = currency_id._convert(pay.installment_origin_amount, pay.currency_id, self.env.company,
                                                     self.payment_date)
                pay.payment_difference = origin_amount - payment_amount
            else:
                pay.payment_difference = pay._compute_payment_amount(pay.invoice_ids, pay.currency_id, pay.journal_id,
                                                                     pay.payment_date) - payment_amount
        (self - draft_payments).payment_difference = 0

    

class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'
    _description = 'Register Payment'

    fine_amount = fields.Monetary(currency_field='currency_id', readonly=False)

    fine_account_id = fields.Many2one('account.account', string="Fine Account", copy=False,
                                      domain="[('deprecated', '=', False), ('company_id', '=', company_id)]")
    fine_writeoff_label = fields.Char(string='Fine Journal Item Label', default='Fine For  Write-Off',
                                      help='Change label of the counterpart that will hold the payment difference')
    installment_origin_amount = fields.Monetary(currency_field='currency_id', readonly=False,string="Installment Origin Amount")
    interest_discount_amount = fields.Monetary(currency_field='currency_id', readonly=True,string="Interest Discount Amount", digits=(12, 2))
    interest_disc_account_id = fields.Many2one('account.account', string="Interest Discount Account", copy=False,
                                               domain="[('deprecated', '=', False), ('company_id', '=', company_id)]")

    def create_entry(self):
        interest_discount_currency = self.interest_discount_amount
        interest_discount_balance = self.currency_id._convert(
            interest_discount_currency,
            self.company_id.currency_id,
            self.company_id,
            self.payment_date,
        )
        res = self.env['account.move'].create({
            'move_type': 'entry',
            'date': self.payment_date,
            'partner_id': self.partner_id.id,
            'ref': '',
            'line_ids': [
                (0, 0, {
                    'name': 'Interest Discount',
                    'amount_currency': interest_discount_currency,
                    'currency_id': self.currency_id.id,
                    'account_id': self.interest_disc_account_id.id,
                    'debit': interest_discount_balance,
                    'credit': 0.0,
                    'partner_id': self.partner_id.id,
                }),
                (0, 0, {
                    'name': 'Interest Discount',
                    'amount_currency': -interest_discount_currency,
                    'currency_id': self.currency_id.id,
                    'account_id': self.hr_bu_id.property_account_receivable_id.id,
                    'debit': 0.0,
                    'credit': interest_discount_balance,
                    'partner_id': self.partner_id.id,
                }),
            ],
        })

        res.action_post()
        balance_receiv = res.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')
        invoice = self.env['account.move'].browse(self.env.context['active_id'])
        invoice.js_assign_outstanding_line(balance_receiv.id)

    def _create_payment_vals_from_wizard(self):
        payment_vals = {
            'date': self.payment_date,
            'amount': self.amount,
            'payment_type': self.payment_type,
            'partner_type': self.partner_type,
            'ref': self.communication,
            'journal_id': self.journal_id.id,
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_id.id,
            'partner_bank_id': self.partner_bank_id.id,
            'payment_method_line_id': self.payment_method_line_id.id,
            'destination_account_id': self.line_ids[0].account_id.id
        }

        if not self.currency_id.is_zero(self.payment_difference) and self.payment_difference_handling == 'reconcile':
            payment_vals['write_off_line_vals'] = {
                'name': self.writeoff_label,
                'amount': self.payment_difference,
                'account_id': self.writeoff_account_id.id,
            }
        if self.fine_amount:
            payment_vals['fine_line_vals'] = {
                'name': self.fine_writeoff_label,
                'amount': self.fine_amount,
                'account_id': self.fine_account_id.id,
            }

        return payment_vals
    
    def _compute_amount(self):
        for wizard in self:
           
            if wizard.source_currency_id == wizard.currency_id and not wizard.env.context.get('default_is_installment'):
               
                # Same currency.
                wizard.amount = wizard.source_amount_currency
              
            elif wizard.currency_id == wizard.company_id.currency_id and  not wizard.env.context.get('default_is_installment'):
                # Payment expressed on the company's currency.
                wizard.amount = wizard.source_amount
              

            #Installment Line Payment 
            elif wizard.env.context.get('default_is_installment'):
                
                amount = 0.0
                partial_amount = 0.0
                ctx = self.env.context
                installment_obj = self.env['invoice.installment.line'].browse(ctx['installment_id'])
                # installment_origin_amount = wizard.installment_origin_amount
                
                # amount = wizard.installment_origin_amount - installment_obj.partial_paid_amount
                amount = wizard.installment_origin_amount
                fine_amount = self.env.context.get('default_fine_amount')
                interest_discount_amount = self.env.context.get('default_interest_discount_amount')

                if wizard.currency_id == wizard.company_id.currency_id:
                
                    wizard.amount =  installment_obj.invoice_currency_id._convert(amount, wizard.currency_id, wizard.company_id, wizard.payment_date)
                    wizard.fine_amount = installment_obj.invoice_currency_id._convert(fine_amount,wizard.currency_id, wizard.company_id, wizard.payment_date)
                    wizard.interest_discount_amount =  installment_obj.invoice_currency_id._convert(interest_discount_amount,wizard.currency_id, wizard.company_id, wizard.payment_date)

                elif wizard.source_currency_id != wizard.currency_id:
                    wizard.amount =  wizard.company_id.currency_id._convert(amount, wizard.currency_id, wizard.company_id, wizard.payment_date)
                    wizard.fine_amount = wizard.company_id.currency_id._convert(fine_amount,wizard.currency_id, wizard.company_id, wizard.payment_date)
                    wizard.interest_discount_amount =  wizard.company_id.currency_id._convert(interest_discount_amount,wizard.currency_id, wizard.company_id, wizard.payment_date)

                elif wizard.source_currency_id == wizard.currency_id:
                    wizard.amount =amount
                    wizard.fine_amount =fine_amount
                    wizard.interest_discount_amount =interest_discount_amount
            else:             
                # Foreign currency on payment different than the one set on the journal entries.
                amount_payment_currency = wizard.company_id.currency_id._convert(wizard.source_amount, wizard.currency_id, wizard.company_id, wizard.payment_date)
                wizard.amount = amount_payment_currency

    def _create_payments(self):
        res = super(AccountPaymentRegister, self)._create_payments()
        for payment_line in res:
            ctx = self.env.context
            current = False
            paid_fine = 0.0
            currency_amount = 0.0
            installment_id = self._context.get('installment_id')
            if installment_id:
                installment_obj = self.env['invoice.installment.line'].browse(installment_id)
                for line in installment_obj:
                    currency_amount = self.currency_id._convert(self.amount,line.invoice_id.currency_id,self.env.company,self.payment_date)
                    # currency_amount = self.currency_id._convert(self.amount, installment_obj.invoice_currency_id, self.env.company, self.payment_date)
                    # print()
                    if (line.paid_amount+currency_amount) == line.amount:
                        line.state = 'paid'
                        line.sinst_line_id.state = 'paid'
                        line.paid = True
                    # print(line.paid_amount+currency_amount,line.amount,"=====================++>")
                    line.update({
                        'paid_amount': line.paid_amount+currency_amount,
                        'paid_currency_id': self.currency_id.id,
                        # 'fine_paid': currency_fine_amount,
                        # 'principal_paid': currency_amount - currency_fine_amount,
                        'rv_no':payment_line.name if not line.rv_no else line.rv_no+","+payment_line.name
                    })

                    current = line
                    line_installment = self.env['account.move'].browse(self.env.context['active_id']).installment_ids.filtered(
                        lambda x: x.index != 0)
                    for line in line_installment:
                        line.update({'index': line.index})

                    paid_fine = 0.0
                    current_fine_amount = current.fine_amount - current.fine_discount
                    print('current fine',current_fine_amount)


                    if current_fine_amount > 0.0:

                        if currency_amount > current_fine_amount:
                            fine_temp = self.currency_id._convert(self.fine_amount, installment_obj.invoice_currency_id, self.env.company, self.payment_date)
                            
                            # fine_temp = self.currency_id._convert(current_fine_amount, line.invoice_id.currency_id,
                            #                                                 self.env.company, self.payment_date)
                            print(fine_temp,'>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>')
                            paid_temp = self.amount - self.fine_amount
                            paid_temp = self.currency_id._convert(paid_temp, line.invoice_id.currency_id, self.env.company,
                                                                            self.payment_date)
                            
                            current.update({
                                'fine_paid': current.fine_paid+fine_temp ,#if not current.fine_paid else fine_temp,
                                'principal_paid': paid_temp+current.principal_paid,
                            })
                            paid_fine = current_fine_amount
                        else:
                            fine_temp = self.currency_id._convert(self.fine_amount, line.invoice_id.currency_id,
                                                                            self.env.company, self.payment_date)
                           
                            # fine_temp = line.invoice_id.currency_id._convert(currency_amount, self.currency_id,
                            #                                                 self.env.company, self.payment_date)
                            current.update({
                                'fine_paid': fine_temp+current.fine_paid,# if not current.fine_paid else fine_temp+current.fine_paid,
                                'principal_paid': 0.0,
                            })
                            paid_fine = currency_amount
                    else:
                        paid_temp = self.currency_id._convert(self.amount, line.invoice_id.currency_id, self.env.company,
                                                                        self.payment_date)
                       
                        # paid_temp = line.invoice_id.currency_id._convert(currency_amount, self.currency_id, self.env.company,
                        #                                                 self.payment_date)
                        current.update({
                            'principal_paid': paid_temp+current.principal_paid
                        })

                    today = fields.Datetime.today()
                    dd = today.strftime("%d-%b-%y").split('-')

                    if len(dd) == 3:
                        current.update({
                            'rv_date': dd[1]
                        })

                    current.update({
                        'is_active': False,
                    })

                    for nex in line_installment:
                        if nex.index > current.index:
                            # nex.update({
                            #         'total_remaining_amount':current.total_remaining_amount - line.amount
                            #     })
                            if nex.index > 1:

                                if nex.index == current.index + 1:
                                    due_amount = 0.0
                                    fine_amount = 0.0

                                    if currency_amount != current.amount:
                                        # print(currency_amount)
                                        # print('current amount///////',current.amount)

                                        if current.invoice_currency_id.id == self.currency_id.id:

                                            current_temp = current.invoice_currency_id._convert(current.amount,
                                                                                                self.currency_id,
                                                                                                self.env.company,
                                                                                                self.payment_date)
                                            # print(current_temp,'>>>>>>>>>>>>>>>>>>>>>>>>>>>')
                                        else:
                                            current_temp = current.amount
                                        # print(current_temp,current.principal_paid,current_temp-current.principal_paid,"====>")
                                        due_amount = current_temp - current.fine_paid - current.principal_paid
                                        if due_amount < 0:
                                            due_amount = 0

                                    fine_rate = nex.fine_rate
                                    fine_amount = due_amount * (fine_rate / 100)
                                    _amount = nex.without_interest_amount + \
                                        nex.interest_amount + due_amount + fine_amount
                                    print("**"*100,line.paid_amount,_amount)
                                    if line.paid_amount == _amount:
                                    # TODO : for no need to udpate next line hzn
                                        nex.update({
                                            'fine_previous_period': current.fine_amount - paid_fine - current.fine_discount,
                                            'due_amount': due_amount,
                                            'amount': _amount,
                                            'is_active': True,
                                            'ar_balance_previous': current.ar_balance,
                                        })


                                        nex.sinst_line_id.update({
                                            'due_amount': due_amount,
                                            'fine_amount': fine_amount,
                                            'amount': _amount,
                                        })
                                    nex.update({
                                        'ar_balance_previous': current.ar_balance,
                                    })
                            if nex.index == 1:
                                nex.update({
                                    'is_active': True
                                })
                            # nex.update({'state':'current_due'})
                    current.sinst_line_id.update({
                        'due_amount': current.due_amount,
                        'fine_amount': current.fine_amount,
                        'fine_previous_period': current.fine_previous_period,
                        'fine_current_period': current.fine_current_period,
                        'paid_amount': current.paid_amount,
                        'fine_paid': current.fine_paid,
                        'principal_paid': current.principal_paid,
                        'ar_balance': current.ar_balance,
                        'rv_date': current.rv_date,
                        'rv_no':current.rv_no,

                    })
            if self.interest_discount_amount != 0:
                self.create_entry()

    
        
        return res




    

    

    # @api.onchange('currency_id')
    # def _onchange_currency(self):

    #     if self.env.context.get('default_is_installment'):
    #         amount = 0.0
    #         partial_amount = 0.0
    #         ctx = self.env.context
    #         installment_obj = self.env['invoice.installment.line'].browse(
    #             ctx['installment_id'])
    #         active_ids = self._context.get('active_ids')
    #         invoices = self.env['account.move'].browse(active_ids)

    #         installment_origin_amount = self.env.context.get(
    #             'default_installment_origin_amount')
    #         amount = installment_origin_amount - installment_obj.partial_paid_amount
    #         print(amount,'register amount>>>>>>>>>>>>>>>>>>>>>>>>>')

    #         fine_amount = self.env.context.get('default_fine_amount')
    #         interest_discount_amount = self.env.context.get(
    #             'default_interest_discount_amount')
    #         currency_id = self.currency_id

    #         # for i in invoices:
    #         #     currency_id = i.currency_id

    #         self.amount = installment_obj.invoice_currency_id._convert(
    #             amount, self.currency_id, self.env.company, self.payment_date)
    #         print('register currency amount>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>',self.amount)
    #         self.fine_amount = installment_obj.invoice_currency_id._convert(
    #             fine_amount, self.currency_id, self.env.company, self.payment_date)
    #         self.interest_discount_amount = installment_obj.invoice_currency_id._convert(
    #             interest_discount_amount, self.currency_id, self.env.company, self.payment_date)
        #     # else:
    #     #     self.amount = abs(self._compute_payment_amount(self.invoice_ids, self.currency_id, self.journal_id, self.payment_date))

    #     if self.journal_id:  # TODO: only return if currency differ?
    #         return

        # Set by default the first liquidity journal having this currency if exists.
        # domain = [('type', 'in', ('bank', 'cash')), ('currency_id', '=', self.currency_id.id)]
        # if self.invoice_ids:
        #     domain.append(('company_id', '=', self.invoice_ids[0].company_id.id))
        # journal = self.env['account.journal'].search(domain, limit=1)
        # if journal:
        #     return {'value': {'journal_id': journal.id}}

    # def _create_payments(self):
    #     res = super(AccountPaymentRegister, self)._create_payments()
        
    #     for line in res:
    #         current = False
    #         paid_fine = 0.0
    #         currency_amount = 0.0
    #         ctx = self.env.context
    #         installment_id = self._context.get('installment_id')

    #         # installment_id = self.env['invoice.installment.line'].browse(ctx['installment_id'])

    #         # line.sinst_line_id.state = 'paid'
    #         if installment_id:
    #             installment_obj = self.env['invoice.installment.line'].browse(
    #                 installment_id)
    #             currency_amount = self.currency_id._convert(
    #                 self.amount, installment_obj.invoice_currency_id, self.env.company, self.payment_date)
    #             currency_fine_amount = self.currency_id._convert(
    #                 self.fine_amount, installment_obj.invoice_currency_id, self.env.company, self.payment_date)
    #             # currency_amount = self.company_id.currency_id._convert(self.amount, self.env.company.currency_id, self.env.company,self.payment_date)
               
    #             installment_obj.write({
    #                 'rv_no': line.name,
    #                 'paid_amount': currency_amount,
    #                 # 'paid_currency_id': line.currency_id.id,

    #             })
    #             today = fields.Datetime.today()
    #             dd = today.strftime("%d-%b-%y").split('-')

    #             if len(dd) == 3:
    #                 installment_obj.update({
    #                     'rv_date': dd[1]
    #                 })
    #             for current in installment_obj:
    #                 paid_fine += paid_fine + currency_fine_amount
                 

    #                 installment_obj.update({
    #                     'is_active': False,
    #                     'partial_paid_amount': current.partial_paid_amount + current.paid_amount,
    #                     'fine_paid': current.fine_amount - current.fine_discount,
    #                     'principal_paid': current.partial_paid_amount + current.paid_amount  - paid_fine,
    #                     'ar_balance_previous': current.ar_balance,
    #                 })
                   

    #             line_installment = installment_obj.filtered(lambda x: x.index != 0)
    #             print(line_installment,' installment >>>>>>>>>>>>>>>>>>>>')
    #             for line in line_installment:
    #                 line.update({'index': line.index})


    #                 for nex in line_installment:
    #                     print(nex,'nex d>>>>>>>>>>>>>>>>>>>>>>>>>>>>')
    #                     if nex.index > current.index:
    #                         print('..........................')
    #                         # nex.update({
    #                         #         'total_remaining_amount':current.total_remaining_amount - line.amount
    #                         #     })
    #                         if nex.index > 1:

    #                             if nex.index == current.index + 1:
    #                                 due_amount = 0.0
    #                                 fine_amount = 0.0
                                
    #                                 if currency_amount != current.amount:
    #                                     if current.invoice_currency_id.id == self.currency_id.id:

    #                                         current_temp = current.invoice_currency_id._convert(current.amount,self.currency_id,self.env.company,self.payment_date)
    #                                     else:
    #                                         current_temp = current.amount
    #                                     due_amount = current_temp - current.fine_amount - current.principal_paid
    #                                     if due_amount < 0:
    #                                         due_amount = 0

    #                                 fine_rate = nex.fine_rate
    #                                 fine_amount = due_amount * (fine_rate/100)
    #                                 _amount = nex.without_interest_amount + nex.interest_amount + due_amount + fine_amount

    #                                 nex.update({
    #                                         'fine_previous_period':current.fine_amount - paid_fine - current.fine_discount,
    #                                         'due_amount':due_amount,
    #                                         'amount':_amount,
    #                                         'is_active':True,
    #                                         'ar_balance_previous':current.ar_balance,
    #                                 })


    #                 installment_obj.sinst_line_id.write({
    #                 'due_amount': current.due_amount,
    #                 'fine_amount': current.fine_amount,
    #                 'fine_previous_period': current.fine_previous_period,
    #                 'fine_current_period': current.fine_current_period,
    #                 'paid_amount': current.paid_amount,
    #                 'fine_paid': current.fine_paid,
    #                 'principal_paid': current.principal_paid,
    #                 'ar_balance': current.ar_balance,
    #                 'rv_date': current.rv_date,
    #                 'rv_no': current.rv_no,

    #             })
                    
                   

    #             if self.interest_discount_amount != 0:
    #                 self.create_entry()

    #     return res

        # for nex in line_installment:
        #     if nex.index > current.index:
        #         # nex.update({
        #         #         'total_remaining_amount':current.total_remaining_amount - line.amount
        #         #     })
        #         if nex.index > 1:

        #             if nex.index == current.index + 1:
        #                 due_amount = 0.0
        #                 fine_amount = 0.0

        #                 if currency_amount != current.amount:
        #                     if current.invoice_currency_id.id == self.currency_id.id:

        #                         current_temp = current.invoice_currency_id._convert(current.amount,
        #                                                                             self.currency_id,
        #                                                                             self.env.company,
        #                                                                             self.payment_date)
        #                     else:
        #                         current_temp = current.amount
        #                     due_amount = current_temp - current.fine_amount - current.principal_paid
        #                     if due_amount < 0:
        #                         due_amount = 0

        #                 fine_rate = nex.fine_rate
        #                 fine_amount = due_amount * (fine_rate / 100)
        #                 _amount = nex.without_interest_amount + nex.interest_amount + due_amount + fine_amount

        #                 nex.update({
        #                     'fine_previous_period': current.fine_amount - paid_fine - current.fine_discount,
        #                     'due_amount': due_amount,
        #                     'amount': _amount,
        #                     'is_active': True,
        #                     'ar_balance_previous': current.ar_balance,
        #                 })

        #                 nex.sinst_line_id.update({
        #                     'due_amount': due_amount,
        #                     'fine_amount': fine_amount,
        #                     'amount': _amount,
        #                 })
        #         if nex.index == 1:
        #             nex.update({
        #                 'is_active': True
        #             })

        # installment_obj.sinst_line_id.write({
        #     'due_amount': current.due_amount,
        #     'fine_amount': current.fine_amount,
        #     'fine_previous_period': current.fine_previous_period,
        #     'fine_current_period': current.fine_current_period,
        #     'paid_amount': current.paid_amount,
        #     'fine_paid': current.fine_paid,
        #     'principal_paid': current.principal_paid,
        #     'ar_balance': current.ar_balance,
        #     'rv_date': current.rv_date,
        #     'rv_no': 'Test'

        # })
        # self.create_entry()

        # return res

    # def _create_payment_vals_from_wizard(self):
    #     res = super(AccountPaymentRegister, self)._create_payment_vals_from_wizard()
    #     #print(self._context,'////////////////////////////')
    #
    #     return res
