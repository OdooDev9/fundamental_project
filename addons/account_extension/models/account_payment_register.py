from readline import read_init_file
from odoo import _, api, fields, models
from odoo.exceptions import UserError

class AccountPaymentRegisterInherit(models.TransientModel):
    _inherit = 'account.payment.register'
    
    hr_br_id = fields.Many2one('business.unit', string='Branch',domain="[('business_type','=','br')]")
    hr_bu_id =fields.Many2one('business.unit',string='Business Unit',domain="[('business_type','=','bu')]")
    cfd_id = fields.Many2one('business.unit',string='CFD', default=lambda self: self.env.ref('master_data_extension.cfd_business_unit').id)
    unit_or_part = fields.Selection([('unit', 'Unit'), ('part', 'Spare Part')], string='Units or Parts',default='part')
    service_type = fields.Boolean('Service INV')
    cfd_journal_id = fields.Many2one('account.journal',string='CFD Journal', \
        domain=lambda self: [('bu_br_id', '=', self.env['business.unit'].search([('business_type', '=', 'cfd')]).ids)])
    
    is_oversea_purchase =fields.Boolean(string='Is Oversea Purchase')
    broker_button = fields.Boolean(string='Is Broker Fees')
    
    @api.model
    def set_jr_bu_domain(self):
        domain = [('type', 'in', ('bank', 'cash'))]
        active_ids = self._context.get('active_ids',[])
        if active_ids:
            move = self.env['account.move'].browse(self._context.get('active_ids', []))
            for move in move:
                domain += [('company_id', '=', move.company_id.id)]
                if move.broker_bill==True:
                    domain += [('bu_br_id', '=', self.env['business.unit'].search([('business_type', '=', 'cfd')]).ids),('is_transit_jr','=',False)]
                else:
                    if move.is_oversea_purchase:
                        return [('bu_br_id','=',move.hr_bu_id.id),('type','in', ('bank', 'cash'))]
                    if not move.hr_br_id and move.hr_bu_id:
                        domain += [('bu_br_id', '=', move.hr_bu_id.id), ('is_transit_jr', '=', False)]
                    else:
                        domain += [('bu_br_id', '=', move.hr_bu_id.id), ('is_transit_jr', '=', True)]
                

            
        return domain

    @api.model
    def set_jr_br_domain(self):
        domain = [('type', 'in', ('bank', 'cash'))]
        active_ids = self._context.get('active_ids',[])
        if active_ids:
            move = self.env['account.move'].browse(self._context.get('active_ids', []))
            domain += [('company_id', '=', move.company_id.id)]
            if move.hr_br_id:
                domain += [('bu_br_id', '=', move.hr_br_id.id)]
        return domain

    journal_id = fields.Many2one('account.journal', store=True, readonly=False,
        string='BU Journal',
        compute='_compute_journal_id',
        domain=set_jr_bu_domain)

    br_journal_id = fields.Many2one('account.journal', store=True, readonly=False,
        string='BR Journal',
        domain=set_jr_br_domain)

    @api.model
    def default_get(self, fields_list):
        # OVERRIDE
        res = super().default_get(fields_list)
        active_ids = self._context.get('active_ids',[])
        account_move_obj = self.env['account.move'].browse(self.env.context.get('active_id'))
        bu_journal = self.env['account.journal'].search(self.set_jr_bu_domain(),limit=1)
        br_journal = self.env['account.journal'].search(self.set_jr_br_domain(),limit=1)
        if bu_journal:
            res['journal_id'] = bu_journal.id
        if br_journal:
            res['br_journal_id'] = br_journal.id
            
        else:
            res['br_journal_id'] = False
        for id in active_ids:
            move = self.env['account.move'].search([('id', '=', int(id))],limit=1)
            res.update({'hr_bu_id':move.hr_bu_id.id, 'hr_br_id':move.hr_br_id.id, 'unit_or_part':account_move_obj.unit_or_part, 'service_type':move.service_type})
            if move.service_type and not move.hr_bu_id:
                res['journal_id'] = br_journal.id
            if move.is_oversea_purchase:
                if move.hr_bu_id.oversea_po_journal_id:
                    res['journal_id'] = move.hr_bu_id.oversea_po_journal_id.id
                cfd = self.env['business.unit'].search([('business_type', '=', 'cfd')],limit=1)
                if cfd and cfd.oversea_po_journal_id:
                    res['cfd_journal_id'] = cfd.oversea_po_journal_id.id
        return res
    
    @api.onchange('br_journal_id')
    def _onchange_br_journal(self):
        if self.service_type == True:
            self.journal_id = self.br_journal_id.id

    def _create_payments(self):
        self.ensure_one()
        batches = self._get_batches()
        edit_mode = self.can_edit_wizard and (len(batches[0]['lines']) == 1 or self.group_payment)
        to_process = []

        if edit_mode:
            payment_vals = self._create_payment_vals_from_wizard()
            payment_vals.update({'hr_bu_id': self.hr_bu_id.id, 'hr_br_id': self.hr_br_id.id, 
                'br_journal_id': self.br_journal_id.id if self.hr_br_id else False,
                'unit_or_part':self.unit_or_part,
            })
            to_process.append({
                'create_vals': payment_vals,
                'to_reconcile': batches[0]['lines'],
                'batch': batches[0],
            })
        else:
            # Don't group payments: Create one batch per move.
            if not self.group_payment:
                new_batches = []
                for batch_result in batches:
                    for line in batch_result['lines']:
                        new_batches.append({
                            **batch_result,
                            'lines': line,
                        })
                batches = new_batches

            for batch_result in batches:
                batch_result.update({'hr_bu_id': self.hr_bu_id.id,'hr_br_id': self.hr_br_id.id,
                    'br_journal_id': self.br_journal_id.id if self.hr_br_id else False
                })
                to_process.append({
                    'create_vals': self._create_payment_vals_from_batch(batch_result),
                    'to_reconcile': batch_result['lines'],
                    'batch': batch_result,
                })

        payments = self._init_payments(to_process, edit_mode=edit_mode)
        self._post_payments(to_process, edit_mode=edit_mode)
        self._reconcile_payments(to_process, edit_mode=edit_mode)
        return payments

    def _init_payments(self, to_process, edit_mode=False):
        """ Create the payments.

        :param to_process:  A list of python dictionary, one for each payment to create, containing:
                            * create_vals:  The values used for the 'create' method.
                            * to_reconcile: The journal items to perform the reconciliation.
                            * batch:        A python dict containing everything you want about the source journal items
                                            to which a payment will be created (see '_get_batches').
        :param edit_mode:   Is the wizard in edition mode.
        """
        payments = self.env['account.payment'].create([x['create_vals'] for x in to_process])

        for payment, vals in zip(payments, to_process):
            vals['payment'] = payment

            # If payments are made using a currency different than the source one, ensure the balance match exactly in
            # order to fully paid the source journal items.
            # For example, suppose a new currency B having a rate 100:1 regarding the company currency A.
            # If you try to pay 12.15A using 0.12B, the computed balance will be 12.00A for the payment instead of 12.15A.
            if edit_mode:
                lines = vals['to_reconcile']

                # Batches are made using the same currency so making 'lines.currency_id' is ok.
                if payment.currency_id != lines.currency_id:
                    liquidity_lines, counterpart_lines, writeoff_lines = payment._seek_for_lines()
                    source_balance = abs(sum(lines.mapped('amount_residual')))
                    payment_rate = liquidity_lines[0].amount_currency / liquidity_lines[0].balance
                    source_balance_converted = abs(source_balance) * payment_rate

                    # Translate the balance into the payment currency is order to be able to compare them.
                    # In case in both have the same value (12.15 * 0.01 ~= 0.12 in our example), it means the user
                    # attempt to fully paid the source lines and then, we need to manually fix them to get a perfect
                    # match.
                    payment_balance = abs(sum(counterpart_lines.mapped('balance')))
                    payment_amount_currency = abs(sum(counterpart_lines.mapped('amount_currency')))
                    if not payment.currency_id.is_zero(source_balance_converted - payment_amount_currency):
                        continue

                    delta_balance = source_balance - payment_balance

                    # Balance are already the same.
                    if self.company_currency_id.is_zero(delta_balance):
                        continue

                    # Fix the balance but make sure to peek the liquidity and counterpart lines first.
                    debit_lines = (liquidity_lines + counterpart_lines).filtered('debit')
                    credit_lines = (liquidity_lines + counterpart_lines).filtered('credit')

                    payment.move_id.write({'line_ids': [
                        (1, debit_lines[0].id, {'debit': debit_lines[0].debit + delta_balance}),
                        (1, credit_lines[0].id, {'credit': credit_lines[0].credit + delta_balance}),
                    ]})
        return payments

    def action_create_oversea_payments(self):
        # payments = False
        active_ids = self._context.get('active_ids',[])
        active_move_id = self.env['account.move'].search([('id','in', active_ids)])
        # if self._context.get('dont_redirect_to_payments'):
        #     return True
        payment_vals = self._create_payment_vals_from_wizard()
        payment_vals.update({'hr_bu_id': self.hr_bu_id.id, 'unit_or_part':self.unit_or_part, 'is_oversea_purchase': True})
        payments = self.env['account.payment'].create(payment_vals)
        payments.action_post()
        
        # Reconcillation
        balance_pay = payments.move_id.line_ids.filtered(lambda l: l.account_id.internal_type == 'payable')
        invoice = self.env['account.move'].browse(self.env.context['active_id'])
        invoice.js_assign_outstanding_line(balance_pay.id)

        # Extra Transaction
        move = self.env['account.move']
        move_value = {
                'partner_id': payments.partner_id.id,
                'journal_id': self.cfd_journal_id.id,
                'hr_bu_id': self.hr_bu_id.id,
                'ref': active_move_id.name,
                # 'payment_id':payments.id,
                'oversea_payment_id':payments.id,
                'is_extra_move': True,
                'line_ids': []
            }
        # CFD Default account ID : come from CFD journal
        cfd_default_acc = self.cfd_journal_id.default_account_id
        if not cfd_default_acc:
            raise UserError(_('Missing Default Account on your Journal of CFD'))

        # CFD Aff Receivable Account ID : come from CFD business unit model "business.unit"
        aff_account_receivable = self.cfd_id.aff_account_receivable_id 
        if not aff_account_receivable:
            raise UserError(_('Missing Aff: Receivable Account of your Business Unit(%s) ' % (self.hr_bu_id.name)))

        move_value['line_ids'] = [
                # Aff Receivable Account CFD
                (0, 0, {
                    'color':'info', 'account_id':aff_account_receivable.id, 
                    'partner_id':self.hr_bu_id.partner_id.id, 
                    'name':'OverSea PO', 'debit': payments.amount
                }),
                # HO Oversea Bank Account
                (0, 0, {
                    'color':'info', 'account_id':cfd_default_acc.id, 
                    'partner_id':self.hr_bu_id.partner_id.id,
                    'name':'OverSea PO','credit': payments.amount
                }),
            ]
        move.create(move_value).action_post()

        # Return Action
        action = {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'create': False},
        }
        if len(payments) == 1:
            action.update({'view_mode': 'form','res_id': payments.id,})
        else:
            action.update({'view_mode': 'tree,form','domain': [('id', 'in', payments.ids)]})
        return action

class AccountPaymentTransfer(models.TransientModel):
    _name = 'account.payment.transfer'
    _description = 'Account Payment Transfer'
    
    name  = fields.Char('Label')
    payment_id = fields.Many2one('account.payment',string='Payment')

    # BU/BR
    bu_id = fields.Many2one('business.unit',string='BU')
    br_id = fields.Many2one('business.unit',string='BR')
    cfd_id = fields.Many2one('business.unit',string='CFD', default=lambda self: self.env.ref('master_data_extension.cfd_business_unit').id)

    bu_journal_id = fields.Many2one('account.journal',string='BU Journal', \
        domain="[('bu_br_id','=', bu_id)]")
    br_journal_id = fields.Many2one('account.journal',string='BR Journal', \
        domain="[('bu_br_id', '=', br_id)]")
    cfd_journal_id = fields.Many2one('account.journal',string='CFD Journal', \
        domain="[('bu_br_id.business_type', '=', 'cfd')]")

    is_br_bank_payment = fields.Boolean('Bank Payment by BR')

    is_oversea_purchase = fields.Boolean(string="Is Oversea Purchase", related='payment_id.is_oversea_purchase')

    def create_transfer_transactions(self):
        # active_ids = self._context.get('active_ids',[])
        move = self.env['account.move']
        # print("cfd_journal_id=%s, br_journal_id=%s, bu_journal_id=%s" % (self.cfd_journal_id.name, self.br_journal_id.name, self.bu_journal_id.name))
        pid = self.payment_id
        try:
            if self.bu_id:
                cfd_bu = self.cfd_journal_id.bu_br_id
                move_value = {
                    'partner_id': pid.partner_id.id,
                    'hr_bu_id': self.bu_id.id,
                    'hr_br_id': self.br_id.id,
                    'ref': pid.ref if self.name else pid.ref,
                    'extra_source_id':pid.id,
                    'is_extra_move': True,
                    'line_ids': [],
                    'payment_id': False,
                }
                
                if self.br_id and self.is_br_bank_payment == False:
                    """BR Transfer entry"""
                    br_move_value = move_value.copy()
                    br_move_value.update({'journal_id':self.br_journal_id.id})
                    exchange_amount = self.br_journal_id.currency_id._convert(pid.amount,self.env.user.company_id.currency_id,self.env.user.company_id,fields.Date.today())
                    br_move_value['line_ids'] = [
                            # Cash In Transit - BR
                            (0, 0, {'color':'info', 'account_id':self.br_journal_id.cash_in_transit_id.id, 
                            'currency_id': self.br_journal_id.currency_id.id or self.br_journal_id.company_id.currency_id.id, 'amount_currency':pid.amount,
                            'partner_id':self.bu_id.partner_id.id, 'name':'BR SALE','debit': exchange_amount}),
                            # Cash on Hand - BR
                            (0, 0, {'color':'info', 'account_id':self.br_journal_id.default_account_id.id, 
                            'currency_id': self.br_journal_id.currency_id.id or self.br_journal_id.company_id.currency_id.id, 'amount_currency':-pid.amount,
                            'partner_id':self.bu_id.partner_id.id, 'name':'BR SALE', 'credit': exchange_amount}),
                        ]
                    br_move = move.create(br_move_value)
                    br_move._post(soft=False)

                """BU Transfer entry"""
                bu_move_value = move_value.copy()
                bu_move_value.update({'journal_id':self.bu_journal_id.id})
                exchange_amount = self.bu_journal_id.currency_id._convert(pid.amount,self.env.user.company_id.currency_id,self.env.user.company_id,fields.Date.today())
                bu_move_value['line_ids'] = [
                        # Cash on Hand - BU
                        (0, 0, {'color':'success', 'account_id':self.bu_journal_id.default_account_id.id, 
                        'currency_id': self.br_journal_id.currency_id.id or self.br_journal_id.company_id.currency_id.id, 'amount_currency':pid.amount,
                        'partner_id':self.br_id.partner_id.id if self.br_id else self.bu_id.partner_id.id, 'name':'BR SALE' if self.br_id.id else 'BU SALE', 'debit': exchange_amount}),
                        # Cash In Transit - BU
                        (0, 0, {'color':'success', 'account_id':self.bu_journal_id.cash_in_transit_id.id, 
                        'currency_id': self.br_journal_id.currency_id.id or self.br_journal_id.company_id.currency_id.id, 'amount_currency':-pid.amount,
                        'partner_id':self.br_id.partner_id.id if self.br_id else self.bu_id.partner_id.id, 'name':'BR SALE' if self.br_id.id else 'BU SALE','credit': exchange_amount}),
                    ]
                move.create(bu_move_value)
                
                """BU ==> CFD Transfer entry"""
                bu_cfd_move_value = move_value.copy()
                bu_cfd_move_value.update({'journal_id':self.cfd_journal_id.id})
                bu_cfd_move_value['line_ids'] = [
                        # Cash on Hand - BU
                        (0, 0, {'color':'warning', 'account_id':self.bu_journal_id.default_account_id.id, 
                        'currency_id': self.br_journal_id.currency_id.id or self.br_journal_id.company_id.currency_id.id, 'amount_currency':-pid.amount,
                        'partner_id':cfd_bu.partner_id.id, 'name':'BR SALE' if self.br_id.id else 'BU SALE', 'credit': exchange_amount}),
                        # AFF Receivable - BU
                        (0, 0, {'color':'warning', 'account_id':pid.hr_bu_id.aff_account_receivable_id.id, 
                        'currency_id': self.br_journal_id.currency_id.id or self.br_journal_id.company_id.currency_id.id, 'amount_currency':pid.amount,
                        'partner_id':cfd_bu.partner_id.id, 'name':'BR SALE' if self.br_id.id else 'BU SALE','debit': exchange_amount}),
                    ]
                move.create(bu_cfd_move_value)
                

                """CFD Transfer entry"""
                cfd_move_value = move_value.copy()
                cfd_move_value.update({'journal_id':self.cfd_journal_id.id})
                exchange_amount = self.cfd_journal_id.currency_id._convert(pid.amount,self.env.user.company_id.currency_id,self.env.user.company_id,fields.Date.today())
                description = 'BR SALE ==> BU ==> CFD' if self.br_id.id else 'BU SALE ==> CFD'
                if pid.is_pre_payment:
                    description = "PRE PAYMENT"
                cfd_move_value['line_ids'] = [
                        # Cash on Hand - CFD
                        (0, 0, {'color':'primary', 'account_id':self.cfd_journal_id.default_account_id.id, 
                        'currency_id': self.br_journal_id.currency_id.id or self.br_journal_id.company_id.currency_id.id, 'amount_currency':pid.amount,
                        'partner_id':self.bu_id.partner_id.id, 'name':description, 'debit': exchange_amount}),
                        # AFF Payable - CFD
                        (0, 0, {'color':'primary', 'account_id':cfd_bu.aff_account_payable_id.id, 
                        'currency_id': self.br_journal_id.currency_id.id or self.br_journal_id.company_id.currency_id.id, 'amount_currency':-pid.amount,
                        'partner_id':self.bu_id.partner_id.id, 'name':description,'credit': exchange_amount}),
                    ]
                move.create(cfd_move_value)

                print("<===========================================>")
                # print("BR Transit", br_move_value)
                # print("BU Transit", bu_move_value)
                # print("BU HO Transit", bu_cfd_move_value)
                # print("HO Transit", cfd_move_value)
                print("<=====================++++==================>")
                self.payment_id.write({'is_transfered': True})
        except Exception as e:       
            raise UserError(_(str(e)))

    def create_transfer_transactions_for_oversea_po(self):
        move = self.env['account.move']
        pid = self.payment_id
        # if pid.payment_type == 'outbound':
        #     print("move_id===>",pid.reconciled_bills_count)

        try:
            move_value = {
                'partner_id': pid.partner_id.id,
                'hr_bu_id': self.bu_id.id,
                'ref': pid.ref if self.name else pid.ref,
                'extra_source_id':pid.id,
                'is_extra_move': True,
                'line_ids': []
            }
            
            """ ========================= BU ENTRY ==================================== """
            bu_move_value = move_value.copy()
            bu_move_value.update({'journal_id':self.bu_journal_id.id})

            """ CHECK REQUIRED ACCOUNT """
            # BU Account Payable ID : come from BU business unit model "business.unit"
            bu_payable_acc = self.bu_id.property_account_payable_id
            if not bu_payable_acc:
                raise UserError(_('Missing Payable Account of your Business Unit(%s) ' % (self.bu_id.name)))

            # Aff Payable Account ID : come from BU business unit model "business.unit"
            aff_bu_payable_acc = self.bu_id.aff_account_payable_id
            if not aff_bu_payable_acc:
                raise UserError(_('Missing Aff: Payable Account of your Business Unit(%s) ' % (self.bu_id.name)))

            bu_move_value['line_ids'] = [
                    # Account Payable - Trade - Oversea - BU
                    (0, 0, {
                        'color':'success', 'account_id':bu_payable_acc.id, 
                        'partner_id':self.cfd_id.partner_id.id, 
                        'name':'OverSea PO', 'debit': pid.amount
                    }),
                    # Aff Payable Account (HO) - BU
                    (0, 0, {
                        'color':'success', 'account_id':aff_bu_payable_acc.id, 
                        'partner_id':self.cfd_id.partner_id.id,
                        'name':'OverSea PO','credit': pid.amount
                    }),
                ]
            move.create(bu_move_value)

            """ ========================= CFD ENTRY ==================================== """
            cfd_move_value = move_value.copy()
            cfd_move_value.update({'journal_id':self.cfd_journal_id.id})

            """ CHECK REQUIRED ACCOUNT """
            # CFD Default account ID : come from CFD journal
            cfd_default_acc = self.cfd_journal_id.default_account_id
            if not cfd_default_acc:
                raise UserError(_('Missing Default Account on your Journal of CFD'))

            # CFD Oversea Bank Account ID : come from CFD business unit model "business.unit"
            aff_account_receivable = self.bu_id.aff_account_receivable_id 
            if not aff_account_receivable:
                raise UserError(_('Missing Aff: Receivable Account of your Business Unit(%s) ' % (self.bu_id.name)))

            cfd_move_value['line_ids'] = [
                    # Aff Receivable Account (Related BU) - CFD
                    (0, 0, {
                        'color':'info', 'account_id':self.bu_id.aff_account_receivable_id.id, 
                        'partner_id':self.bu_id.partner_id.id, 
                        'name':'OverSea PO', 'debit': pid.amount
                    }),
                    # HO Oversea Bank Account
                    (0, 0, {
                        'color':'info', 'account_id':cfd_default_acc.id, 
                        'partner_id':self.bu_id.partner_id.id,
                        'name':'OverSea PO','credit': pid.amount
                    }),
                ]
            move.create(cfd_move_value)

            self.payment_id.write({'is_transfered': True})
        except Exception as e:       
            raise UserError(_(str(e)))

class AccountPaymentInherit(models.Model):
    _inherit = "account.payment"
    hr_br_id = fields.Many2one('business.unit', string='Branch',domain="[('business_type','=','br')]")
    hr_bu_id = fields.Many2one('business.unit',string='Business Unit',domain="[('business_type','=','bu')]")
    unit_or_part = fields.Selection([('unit', 'Unit'), ('part', 'Spare Part')], string='Units or Parts',default='part')
    count_extra_entry = fields.Integer(
        string='Extra Entries',
        compute='count_extra'
    )
    count_extra_entry_line = fields.Integer(
        string='Extra Lines',
        compute='count_extra'
    )
    is_pre_payment = fields.Boolean("Pre Payment/Down Payment")
    is_transfered = fields.Boolean("Is Transfered")
    service_type = fields.Boolean('Service', compute='get_service_type_or_not')

    is_oversea_purchase = fields.Boolean(string="Is Oversea Purchase")
    count_oversea_entry_line = fields.Integer(
        string='Extra Lines',
        compute='count_extra'
    )
    @api.model
    def default_get(self, fields):
        """Method to set default warehouse of user branch."""
        result = super(AccountPaymentInherit, self).default_get(fields)
        business = self.env.user.current_bu_br_id
        if business.business_type == 'br':
            result.update({'hr_br_id': business.id})
        if business.business_type == 'bu':
            result.update({'hr_bu_id': business.id})      
        return result

    def count_extra(self):
        for rec in self:
            move = rec.env['account.move'].search([('extra_source_id','=',rec.id)])
            line = rec.env['account.move.line'].search([('move_id', 'in', move.ids)])
            rec.count_extra_entry = len(move.ids)
            rec.count_extra_entry_line = len(line.ids)

            # For Oversea Purchase
            oversea_move = rec.env['account.move'].search(['|', ('payment_id','=',rec.id), ('oversea_payment_id','=',rec.id)])
            oversea_move_line = rec.env['account.move.line'].search([('move_id', 'in', oversea_move.ids)])
            rec.count_oversea_entry_line = len(oversea_move_line.ids)

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('move_id.line_ids.amount_residual', 'move_id.line_ids.amount_residual_currency', 'move_id.line_ids.account_id')
    def _compute_reconciliation_status(self):
        ''' Compute the field indicating if the payments are already reconciled with something.
        This field is used for display purpose (e.g. display the 'reconcile' button redirecting to the reconciliation
        widget).
        '''
        for pay in self:
            liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()

            if not pay.currency_id or not pay.id:
                pay.is_reconciled = False
                pay.is_matched = False
            elif pay.currency_id.is_zero(pay.amount):
                pay.is_reconciled = True
                pay.is_matched = True
            else:
                residual_field = 'amount_residual' if pay.currency_id == pay.company_id.currency_id else 'amount_residual_currency'
                if (
                    # Allow user managing payments without any statement lines by using the bank account directly. 
                    # In that case, the user manages transactions only using the register payment wizard.
                    # And payment transaction with default account of related journal
                    pay.journal_id.default_account_id and pay.journal_id.default_account_id in liquidity_lines.account_id
                ) or (
                    # In that case, the user manages transactions only using the register payment wizard.
                    # And payment transaction with transit account of related journal
                    pay.journal_id.cash_in_transit_id and pay.journal_id.cash_in_transit_id in liquidity_lines.account_id
                ):
                    pay.is_matched = True
                else:
                    pay.is_matched = pay.currency_id.is_zero(sum(liquidity_lines.mapped(residual_field)))

                reconcile_lines = (counterpart_lines + writeoff_lines).filtered(lambda line: line.account_id.reconcile)
                pay.is_reconciled = pay.currency_id.is_zero(sum(reconcile_lines.mapped(residual_field)))
        
    @api.model
    def set_jr_br_domain(self):
        domain = [('type', 'in', ('bank', 'cash'))]
        if self.hr_br_id:
            domain += [('bu_br_id', '=', self.hr_br_id.id)]
        return domain
        
    br_journal_id = fields.Many2one('account.journal', store=True, readonly=False,
        string='BR Journal',
        domain=set_jr_br_domain)

    @api.onchange('hr_br_id')
    def onchange_hr_br_id(self):
        if not self.hr_br_id:
            return {'domain': {'br_journal_id': [('bu_br_id', '=', -1)]}}
        return {'domain': {'br_journal_id': [('bu_br_id', '=', self.hr_br_id.id if self.hr_br_id else False),('type', 'in', ('bank', 'cash'))]}}

    @api.onchange('hr_bu_id')
    def onchange_hr_bu_id(self):
        if not self.hr_bu_id:
            return {'domain': {'journal_id': [('bu_br_id', '=', -1)]}}
        return {'domain': {'journal_id': [('bu_br_id', '=', self.hr_bu_id.id),('type', 'in', ('bank', 'cash'))]}}
    

    def _get_valid_liquidity_accounts(self):
        data = (
            self.journal_id.default_account_id,
            self.payment_method_line_id.payment_account_id,
            self.journal_id.company_id.account_journal_payment_debit_account_id,
            self.journal_id.company_id.account_journal_payment_credit_account_id,
            self.journal_id.inbound_payment_method_line_ids.payment_account_id,
            self.journal_id.outbound_payment_method_line_ids.payment_account_id,
        )
        if self.is_oversea_purchase and self.hr_bu_id.aff_account_payable_id:
            data = data + (self.hr_bu_id.aff_account_payable_id,)
        return data

    @api.depends('journal_id', 'payment_type', 'payment_method_line_id')
    def _compute_outstanding_account_id(self):
        for pay in self:
            if pay.payment_type == 'inbound':
                pay.outstanding_account_id = (pay.payment_method_line_id.payment_account_id
                                              or pay.journal_id.company_id.account_journal_payment_debit_account_id)
            elif pay.payment_type == 'outbound':
                pay.outstanding_account_id = (pay.payment_method_line_id.payment_account_id
                                              or pay.journal_id.company_id.account_journal_payment_credit_account_id)
            else:
                pay.outstanding_account_id = False

    @api.depends('journal_id', 'partner_id', 'partner_type', 'is_internal_transfer')
    def _compute_destination_account_id(self):
        self.destination_account_id = False
        for pay in self:
            if pay.is_internal_transfer:
                pay.destination_account_id = pay.journal_id.company_id.transfer_account_id
            elif pay.partner_type == 'customer':
                if pay.is_pre_payment:
                    if not pay.hr_bu_id.property_account_receivable_id:
                        raise UserError(_('Missing Account Receivable for related BU(%s)' % pay.hr_bu_id.name))
                    pay.destination_account_id = pay.hr_bu_id.property_account_receivable_id
                else:
                    # Receive money from invoice or send money to refund it.
                    if pay.partner_id:
                        pay.destination_account_id = pay.partner_id.with_company(pay.company_id).property_account_receivable_id
                    else:
                        pay.destination_account_id = self.env['account.account'].search([
                            ('company_id', '=', pay.company_id.id),
                            ('internal_type', '=', 'receivable'),
                            ('deprecated', '=', False),
                        ], limit=1)
            elif pay.partner_type == 'supplier':
                if pay.is_pre_payment:
                    if not pay.hr_bu_id.property_account_payable_id:
                        raise UserError(_('Missing Account Payable for related BU(%s)' % pay.hr_bu_id.name))
                    pay.destination_account_id = pay.hr_bu_id.property_account_payable_id
                else:                
                    # Send money to pay a bill or receive money to refund it.
                    if pay.partner_id:
                        pay.destination_account_id = pay.partner_id.with_company(pay.company_id).property_account_payable_id
                    else:
                        pay.destination_account_id = self.env['account.account'].search([
                            ('company_id', '=', pay.company_id.id),
                            ('internal_type', '=', 'payable'),
                            ('deprecated', '=', False),
                        ], limit=1)

    @api.depends('reconciled_invoice_ids')
    def get_service_type_or_not(self):
        if len(self.reconciled_invoice_ids):
            result = self.reconciled_invoice_ids.service_type
            self.service_type = result
        else:
            self.service_type = False

    @api.model_create_multi
    def create(self, values):
        """
            Create a new record for a model ModelName
            @param values: provides a data for new record
    
            @return: returns a id of new record
        """
        br_journal_id =  values[0].get('br_journal_id')
        bu_journal_id =  values[0].get('journal_id')
        result = super(AccountPaymentInherit,self).create(values)
        # Custom account.move
        move = self.env['account.move']
        for value in values:
            journal = self.env['account.journal'].search([('id', '=', br_journal_id)]) # this is BR journal 
            bu_journal = self.env['account.journal'].search([('id', '=', bu_journal_id)]) # this is BU journal 
            bu = self.env['business.unit'].search([('id', '=', value.get('hr_bu_id'))])
            if value.get('hr_br_id') and bu_journal.type != 'bank':
                move_value = {
                    'partner_id': value.get('partner_id'),
                    'hr_bu_id': value.get('hr_bu_id'),
                    'hr_br_id': value.get('hr_br_id'),
                    'ref': value.get('ref'),
                    'journal_id': journal.id,
                    'extra_source_id':result.id,
                    'is_extra_move': True,
                    'line_ids': []
                }
                """
                                                      DR  CR
                    Cash on Hand - BR	    BR	 Bu	  ***		Cash and Bank
                    Cash In Transit - BR	BR	 BU		  ***	Cash and Bank
                """
                pid_amount = journal.currency_id._convert(value.get('amount'),self.env.user.company_id.currency_id,self.env.user.company_id,fields.Date.today())
                move_value['line_ids'] = [
                        # Cash on Hand - BR
                        (0, 0, {'color':'danger', 'account_id':journal.default_account_id.id, 'currency_id': journal.currency_id.id or journal.company_id.currency_id.id, 'amount_currency':value.get('amount'),
                        'partner_id':value.get('partner_id'), 'name':'BR SALE', 'debit': pid_amount}),
                        # Cash In Transit - BR
                        (0, 0, {'color':'danger', 'account_id':journal.cash_in_transit_id.id, 'currency_id': journal.currency_id.id or journal.company_id.currency_id.id, 'amount_currency': -value.get('amount'),
                        'partner_id':bu.partner_id.id, 'name':'BR SALE','credit': pid_amount}),
                    ]
                res = move.create(move_value)
                if res and not result.is_pre_payment:
                    res._post(soft=False)

        # raise UserError(_("STOP"))
        return result
     
    def action_payment_transfer(self):
        view = self.env.ref('account_extension.view_account_payment_transfer_form')
        is_br_bank_payment = True if self.journal_id.type == 'bank' else False
        return {
            'name': _('Payment Transfer'),
            'res_model': 'account.payment.transfer',
            'view_mode': 'form',
            'context': {
                'active_model': 'account.move',
                'active_ids': self.ids,
                'default_payment_id':self.id,
                'default_bu_id':self.hr_bu_id.id,
                'default_br_id':self.hr_br_id.id,
                'default_is_br_bank_payment': is_br_bank_payment,
            },
            'target': 'new',
            'view_id': view.id,
            'type': 'ir.actions.act_window',
        }

    def button_extra_entries(self):
        move = self.env['account.move'].search(
            [
                ('extra_source_id','=',self.id), ('line_ids.account_id.bu_br_id','=',self.env.user.current_bu_br_id.id)
            ]
        )
        return {
            'name': _('Extra Journal Entries'),
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'views': [[self.env.ref('account.view_move_tree').id, 'list'],[False, 'form']],
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', move.ids)],
            'context': {
                'create': False,
                'edit': False,
                'delete': False,
                # 'journal_id': self.journal_id.id,
                # 'group_by': 'move_id',
                'expand': True
            }
        }
    def button_extra_entrie_lines(self):
        # print("self.env.user NAME ===> ", self.env.user.current_bu_br_id.name)
        move = self.env['account.move'].search([('extra_source_id','=',self.id),('line_ids.account_id.bu_br_id','=',self.env.user.current_bu_br_id.id)])
        return {
            'name': _('Extra Journal Entries'),
            'view_mode': 'tree,form',
            'res_model': 'account.move.line',
            'views': [[self.env.ref('account_extension.view_extra_transaction_move_line_tree').id, 'list'],[False, 'form']],
            'type': 'ir.actions.act_window',
            'domain': [('move_id', 'in', move.ids)],
            'context': {
                'create': False,
                'edit': False,
                'delete': False,
                # 'journal_id': self.journal_id.id,
                'group_by': ['move_id'],
                'expand': True
            }
        }

    def button_oversea_entrie_lines(self):
        move = self.env['account.move'].search(['|', ('payment_id','=',self.id), ('oversea_payment_id','=',self.id)])
        return {
            'name': _('Oversea Journal Entries'),
            'view_mode': 'tree,form',
            'res_model': 'account.move.line',
            'views': [[self.env.ref('account_extension.view_extra_transaction_move_line_tree').id, 'list'],[False, 'form']],
            'type': 'ir.actions.act_window',
            'domain': [('move_id', 'in', move.ids)],
            'context': {
                'create': False,
                'edit': False,
                'delete': False,
                # 'journal_id': self.journal_id.id,
                'group_by': ['move_id'],
                'expand': True
            }
        }

    def action_post(self):
        result = super(AccountPaymentInherit,self).action_post()
        for rec in self:
            if rec.is_pre_payment:
                move = rec.env['account.move'].search([('extra_source_id','=',rec.id)])
                move._post(soft=False)

    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        line_vals_list = super(AccountPaymentInherit,self)._prepare_move_line_default_vals(write_off_line_vals)
        if self.is_oversea_purchase:
            if not self.hr_bu_id.aff_account_payable_id:
                raise UserError(_("Account Missing Error!. Your haven't set Aff: Payable Account for current business unit called %s." % self.hr_bu_id.name))
            else:
                line_vals_list[0]['account_id'] = self.hr_bu_id.aff_account_payable_id.id
        return line_vals_list

    ###########################
    # Remove Extra Entries
    ##########################
    def remove_extra_entries(self):
        try:
            self.env['account.move'].search([('extra_source_id','=',self.id)]).button_draft()
            self.env['account.move'].search([('extra_source_id','=',self.id)]).unlink()
        except Exception as error:
            raise UserError(_(str(error)))
    
    def unlink(self):
        """
            Delete all record(s) from recordset
            return True on success, False otherwise
    
            @return: True on success, False otherwise
    
            #TODO: process before delete resource
        """
        self.remove_extra_entries()
        result = super(AccountPaymentInherit, self).unlink()
    
        return result

class AccountPaymentMethodLineInherit(models.Model):
    _inherit = "account.payment.method.line"
    
    payment_account_id = fields.Many2one(
        comodel_name='account.account',
        check_company=True,
        copy=False,
        ondelete='restrict',
        domain=lambda self: "[('deprecated', '=', False),"
                            "('bu_br_id', '=', parent.bu_br_id), "
                            "('company_id', '=', company_id), "
                            "('user_type_id.type', 'not in', ('receivable', 'payable')), "
                            "'|', ('user_type_id', 'in', (%s,%s)), ('id', 'in', (parent.default_account_id,parent.cash_in_transit_id))]"

                            % (self.env.ref('account.data_account_type_current_assets').id, self.env.ref('account.data_account_type_current_liabilities').id)
    )
