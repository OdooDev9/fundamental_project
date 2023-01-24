from urllib import request
from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError, ValidationError
from datetime import date,datetime
from dateutil.relativedelta import relativedelta
import logging


class IncentiveRequest(models.Model):
      _name = 'incentive.request'
      _description = 'Incentive Request'
      _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
      _order = 'name desc'

      name = fields.Char(string="Name", required=True, default=lambda self: _('New'), readonly=True, copy=False)
      request_date = fields.Date(string="Request Date")
      incentive_request_line = fields.One2many('incentive.request.line','incentive_request_id')
      state = fields.Selection([
            ('draft', 'Draft'),
            ('request_incentive_approved', 'Request Incentive Approved'),
            # ('incentive_approved', 'Incentive Approved'),
            ('boh_approved', 'BOH Approved'),
            ('saleadmin_approved','Sale Admin Approved'),
            ('salehead_approved','Sale Head Approved'),
            ('finance_account_approved', 'F & A Approved'),
            ('cca_dh_approved','CCA Dept. Approved'),
            ('cca_gm_approved','CCA GM Approved'),
            ('incentive_withdraw', 'Incentive Withdraw'),
            ('pooling_withdraw', 'Pooling Withdraw'),
            ('retain_withdraw', 'Retain Withdraw'),
            ('incentive_partially_withdraw','Incentive Partially Withdraw'),
            ('close', 'Close'),
            ('reject', 'Rejected'),
      ], string="Status", readonly=True, default="draft", tracking=True, required=True)
      branch_id = fields.Many2one('business.unit', string="Branch Name", required=False,
                                                domain="[('business_type','=','br')]")
      business_id = fields.Many2one('business.unit', string="Business Unit", required=False,
                                                domain="[('business_type','=','bu')]")
      incentive_definition_id = fields.Many2one('normal.incentive.definition', string="Incentive Definition",
                                                                    required=False, ondelete="cascade")
      currency_id = fields.Many2one('res.currency', string='Currency')
      exchange_rate = fields.Float()
      pooling_amount = fields.Float(compute='compute_exchange_rate')
      retain_amount = fields.Float(compute='compute_exchange_rate')
      saleman_amount = fields.Float(compute='compute_exchange_rate')
      due_amount = fields.Float('Due Amount', compute='get_due_total')
      paid_amount = fields.Float('Paid Amount')
      # pooling_status = fields.Boolean(store=True)
      # retain_status = fields.Boolean(string="Retain Status",store=True,compute='action_compute_retain_status')
      saleperson_paid = fields.Boolean()
      pooling_paid = fields.Boolean()
      retain_paid = fields.Boolean()
      manager = fields.Boolean()
      manager_amount = fields.Float(compute='compute_exchange_rate')
      pooling_date = fields.Date()
      retain_date =  fields.Date()
      bu_user = fields.Boolean(compute='compute_bu_user')
      br_user = fields.Boolean(compute='compute_br_user')
      cfd_user = fields.Boolean(compute='compute_cfd_user')
      mmk_currency_id = fields.Many2one('res.currency',string="Currency")
      total = fields.Float(compute="compute_total",string="Amount Total")
      journal_id = fields.Many2one('account.journal', string='Transfer Journal', domain="[('type', 'in', ['bank', 'cash'])]")
      receive_journal_id = fields.Many2one('account.journal', string='Received Journal', domain="[('type', 'in', ['bank', 'cash'])]")

      @api.depends('saleman_amount','pooling_amount','retain_amount')
      def compute_total(self):
            for rec in self:
                  rec.total = rec.saleman_amount + rec.pooling_amount + rec.retain_amount

      @api.model
      def default_get(self, fields):
            result = super(IncentiveRequest, self).default_get(fields)
            currency = self.env['res.currency'].search([('name','=','MMK')])
            result['mmk_currency_id'] = currency.id
            return result
 

      @api.model 
      def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
            res = super(IncentiveRequest, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
            if 'due_amount' in fields:
                  for line in res:
                        if '__domain' in line:
                              lines = self.search(line['__domain'])
                              total_due_amount = 0.0
                              for record in lines:
                                    total_due_amount += record.due_amount
                              line['due_amount'] = total_due_amount

            return res

      def compute_bu_user(self):
        for rec in self:
            # if self.env.user.current_bu_br_id and self.env.user.user_type_id == 'br':
            #     rec.bu_br_user_approve = True
                
            if self.env.user.user_type_id == 'bu':
                rec.bu_user = True      
            else:
                rec.bu_user = False
      def compute_br_user(self):
        for rec in self:
            # if self.env.user.current_bu_br_id and self.env.user.user_type_id == 'br':
            #     rec.bu_br_user_approve = True
                
            if self.env.user.user_type_id == 'br':
                rec.br_user = True      
            else:
                rec.br_user = False
      
      def compute_cfd_user(self):
        for rec in self:
            # if self.env.user.current_bu_br_id and self.env.user.user_type_id == 'br':
            #     rec.bu_br_user_approve = True
                
            if self.env.user.user_type_id == 'cfd':
                rec.cfd_user = True      
            else:
                rec.cfd_user = False






      def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('You cannot Delete this record'))
        return super(IncentiveRequest, self).unlink()

      # @api.depends('state','request_date','incentive_definition_id')
      # def action_compute_retain_status(self):
      #       for rec in self:
      #             definition = rec.incentive_definition_id
      #             today = datetime.today().date()
      #             if definition.retain_settlement_period == 'annually':
      #                   end_date = definition.retain_annually_date
      #                   if today < end_date:
      #                         rec.retain_status = False
      #                   else:
      #                         rec.retain_status = True
                              # raise UserError(_('You cannot create payment yet for this. Settlement Period is annually. Today date must be greater than annaully date for this incentive.'))

      # @api.depends('state','request_date','incentive_definition_id')
      # def action_compute_pooling_payment(self):
      #       for rec in self:
      #             print('...........')
                  # for line in rec.incentive_request_line:
                  #       for incen in line.normal_incentive_id:
                  #             definition = rec.incentive_definition_id
                  #             today = datetime.today().date()
                  #             if definition.bu_br_settlement_period == 'quaterly':
                  #                   start_date = definition.bu_br_quaterly_start_date
                  #                   end_date = definition.bu_br_quaterly_end_date
                  #                   withdraw_date = datetime(start_date.year,start_date.month,start_date.day)
                  #
                  #                   time = 1
                  #
                  #                   if definition.bu_br_quaterly_time == '3':
                  #                         time = 3
                  #                   else:
                  #                         time = 4
                  #
                  #                   starting_date = rec.date
                  #
                  #
                  #                   while(True):
                  #                         if start_date > end_date:
                  #                               break
                  #
                  #                         temp_end = datetime(start_date.year,start_date.month,start_date.day) + relativedelta(months=time)
                  #                         temp_end = temp_end.date()
                  #                         print('Temp End',temp_end)
                  #
                  #                         if starting_date.month >= start_date.month and starting_date.month <= temp_end.month:
                  #                               print(starting_date,'request date.........')
                  #                               print(start_date,'////////////')
                  #                               print(temp_end,'>>>>>>>>>>>>>>>>')
                  #                               withdraw_date = datetime(temp_end.year,temp_end.month,1) + relativedelta(months=1,days=-1)
                  #                               print(withdraw_date,'>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>')
                  #                               break
                  #                         start_date = temp_end
                  #
                  #
                  #                   print(today)
                  #                   print(withdraw_date,'>>>>>>>>>>>>>>withdraw')
                  #                   if today > withdraw_date.date():
                  #                         print('True**************')
                  #                         rec.pooling_status = True
                  #                   else:
                  #                         print('fasle.................')
                  #                         rec.pooling_status = False
                              
                  # if rec.incentive_definition_id:
                  #       definition = rec.incentive_definition_id
                  #       today = datetime.today().date()
                  
                  #       if definition.bu_br_settlement_period == 'quaterly':
                  #             start_date = definition.bu_br_quaterly_start_date
                  #             end_date = definition.bu_br_quaterly_end_date
                  #             withdraw_date = datetime(start_date.year,start_date.month,start_date.day)

                  #             time = 1

                  #             if definition.bu_br_quaterly_time == '3':
                  #                   time = 3
                  #             else:
                  #                   time = 4

                  #             starting_date = rec.request_date


                  #             while(True):
                  #                   if start_date > end_date:
                  #                         break

                  #                   temp_end = datetime(start_date.year,start_date.month,start_date.day) + relativedelta(months=time)
                  #                   temp_end = temp_end.date()
                  #                   print('Temp End',temp_end)

                  #                   if starting_date.month >= start_date.month and starting_date.month <= temp_end.month:
                  #                         print(starting_date,'request date.........')
                  #                         print(start_date,'////////////')
                  #                         print(temp_end,'>>>>>>>>>>>>>>>>')
                  #                         withdraw_date = datetime(temp_end.year,temp_end.month,1) + relativedelta(months=1,days=-1)
                  #                         print(withdraw_date,'>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>')
                  #                         break
                  #                   start_date = temp_end
                              

                  #             print(today)
                  #             print(withdraw_date,'>>>>>>>>>>>>>>withdraw')
                  #             if today > withdraw_date.date():
                  #                   print('True**************')
                  #                   rec.pooling_status = True
                  #             else:
                  #                   print('fasle.................')
                  #                   rec.pooling_status = False
                                    # print('second condition.............................')
                                    # raise UserError(_('You cannot create payment yet for this. Settlement Period is quaterly.'))
                        
                              

                

# ////////////////////////////////////////////////////////////////

      # Compute Due Amount
      def get_due_total(self):
            for rec in self:
                  rec.due_amount = rec.total - rec.paid_amount
                  # total = rec.saleman_amount + rec.pooling_amount + rec.retain_amount
                 
                 


      # Compute Exchange Rate USD To MMK
      @api.depends('incentive_request_line')
      def compute_exchange_rate(self):
            currency = self.env['res.currency']

            for rec in self:
                  # rec.saleman_amount = 0.0
                  # rec.pooling_amount =0.0
                  # rec.retain_amount =.0
                  pooling_amount = retain_amount = 0.0
                  mmk_sale_man_amount = 0.0
                  mmk_pooling_amount = 0.0
                  mmk_retain_amount = 0.0
                  mmk_manager_amount =0.0
                  saleman_amount = 0.0
                  area_sale_manager_amount = 0.0
                  # if rec.exchange_rate:
                  for line in rec.incentive_request_line:
                        for incentive_line in line.normal_incentive_id:

                              for item_line in incentive_line.line_ids:

                                    if item_line.currency_id.name == 'MMK' and item_line.sale_person_type in ['sale_person','gov_salesperson']:
                                          mmk_sale_man_amount += item_line.incentive_amount
                                    if item_line.currency_id.name == 'MMK' and item_line.sale_person_type in ['bu_br','gov_pooling']:
                                          mmk_pooling_amount +=item_line.incentive_amount
                                    if item_line.currency_id.name == 'MMK' and item_line.sale_person_type == 'retain':
                                          mmk_retain_amount +=item_line.incentive_amount
                                    if item_line.currency_id.name == 'MMK' and item_line.sale_person_type == 'sale_manager':
                                          mmk_manager_amount +=item_line.incentive_amount
                                    if item_line.currency_id.name == 'USD' and item_line.sale_person_type in ['sale_person','gov_salesperson']:
                                          saleman_amount += item_line.incentive_amount * rec.exchange_rate
                                    if item_line.currency_id.name == 'USD' and item_line.sale_person_type in ['bu_br','gov_pooling']:
                                          pooling_amount += item_line.incentive_amount * rec.exchange_rate
                                    if item_line.currency_id.name == 'USD' and item_line.sale_person_type == 'retain':
                                          retain_amount += item_line.incentive_amount * rec.exchange_rate
                                    if item_line.currency_id.name == 'USD' and item_line.sale_person_type == 'sale_manager':
                                          area_sale_manager_amount += item_line.incentive_amount * rec.exchange_rate
                  rec.saleman_amount += mmk_sale_man_amount + saleman_amount
                  rec.pooling_amount += mmk_pooling_amount + pooling_amount
                  rec.retain_amount += mmk_retain_amount + retain_amount
                  rec.manager_amount += mmk_manager_amount + area_sale_manager_amount


      # @api.model
      def create(self, vals):
            if vals.get('name', _('New')) == _('New'):
                  vals['name'] = self.env['ir.sequence'].next_by_code('incentive.request', sequence_date=None) or _('New')
            result = super(IncentiveRequest, self).create(vals)
            return result

      def action_move_items(self):
            self.ensure_one()
            action = self.env["ir.actions.actions"]._for_xml_id("account.action_account_moves_all_a")
            action['domain'] = [('request_incentive_id', '=', self.id)] if self.env.user.user_type_id == 'cfd' else [('request_incentive_id', '=', self.id),('account_id.bu_br_id', '=', self.env.user.current_bu_br_id.id)]
            # action['domain'] = [('request_incentive_id', '=', self.id)]
            return action

      def approve_sale_admin(self):
            for request in self:
                  for request_line in request.incentive_request_line:
                        for ni in request_line.normal_incentive_id:
                              ni.state ='saleadmin_approved'
                  request.state = 'saleadmin_approved'
      
      def approve_sale_head(self):
            for request in self:
                  for request_line in request.incentive_request_line:
                        for ni in request_line.normal_incentive_id:
                              ni.state ='salehead_approved'
                  request.state = 'salehead_approved'
      def approve_boh(self):
            for request in self:
                  for request_line in request.incentive_request_line:
                        for ni in request_line.normal_incentive_id:
                              ni.state ='boh_approved'
                  request.state = 'boh_approved'
      
      def approve_finance_account(self):

            for line in self.incentive_request_line:
                  if line.deduct_amount:
                        line.normal_incentive_id.reverse_deduct_incentive()
                  for ni in line.normal_incentive_id:
                        ni.state ='finance_account_approved'
            self.state = 'finance_account_approved'
      def approve_cca_dh(self):
            if self.exchange_rate == 0.0:
                  raise UserError(_('Please Define MMK Currency Exchange Rate'))
            for request_line in self.incentive_request_line:
                  for ni in request_line.normal_incentive_id:
                        ni.state ='cca_dh_approved'
            self.state = 'cca_dh_approved'
      def approve_cca_gm(self):
            for request_line in self.incentive_request_line:
                  for ni in request_line.normal_incentive_id:
                        ni.state ='cca_gm_approved'
            self.state = 'cca_gm_approved'

      # def create_br_entry(self, incentive_id, accured_account_id,incentive_amount, br):
      #     amount = self.currency_id._convert(incentive_amount,
      #                                        self.env.user.company_id.currency_id,
      #                                        self.env.user.company_id,
      #                                        datetime.today(),
      #                                        )
      #     move_line = {'name': self.name,
      #                  'partner_id': self.business_id.partner_id.id,
      #                  'account_id': accured_account_id.id,
      #                  'business_id': self.branch_id.id,
      #                  'date': datetime.today(),
      #                  'amount_currency': -incentive_amount,
      #                  'credit': amount,
      #                  'currency_id': self.currency_id.id,
      #                  'incentive_id': self.id, }
      #     br.append(move_line)
      #     return br

      # def create_bu_entry(self, incentive_id,account_id,incentive_amount,bu):
      #     saleman_amt =0.0
      #     pooling_amt = 0.0
      #     retain_amt = 0.0
      #     if incentive_id.sale_person_type == 'sale_person':
      #         incentive_amount += incentive_id.incentive_amount
      #         account_id = incentive_id.account_id[0]
      #         print(incentive_amount,'sale man.........')
      #     if incentive_id.sale_person_type == 'bu_br':
      #         incentive_amount += incentive_id.incentive_amount
      #         account_id = incentive_id.account_id[0]
      #         print(incentive_amount,'pooling .........')
      #     if incentive_id.sale_person_type == 'retain':
      #         incentive_amount += incentive_id.account_id[0].incentive_amount
      #         account_id =incentive_id.account_id[0]

      #         amount = self.currency_id._convert(incentive_amount,
      #                                         self.env.user.company_id.currency_id,
      #                                         self.env.user.company_id,
      #                                         datetime.today(),
      #                                         )
      #         move_line = {'name': self.name,
      #                     'partner_id': self.branch_id.partner_id.id,
      #                     'account_id': account_id.id,
      #                     'business_id': self.business_id.id,
      #                     'date': datetime.today(),
      #                     'amount_currency': incentive_amount,
      #                     'debit': amount,
      #                     'currency_id': self.currency_id.id,
      #                     'incentive_id': self.id, }
      #         bu.append(move_line)
      #         return bu
      # def create_entry(self, incentive_id,br, bu):
      #     # incentive_amount = 0.0
         
      #     # for l in incentive_id.incentive_request_line:
              
      #     #     for line in l.normal_incentive_id:
      #     #         for incentive_line in line.line_ids:
      #     #             print(incentive_line,'//////')
      #     #             if incentive_line.sale_person_type == 'sale_person':
      #     #                 incentive_amount += incentive_line.incentive_amount
      #     #                 account_id = incentive_line.account_id
      #     #                 print(incentive_amount,'sale man.........')
      #     #             if incentive_line.sale_person_type == 'bu_br':
      #     #                 incentive_amount += incentive_line.incentive_amount
      #     #                 account_id = incentive_line.account_id
      #     #                 print(incentive_amount,'pooling .........')
      #     #             if incentive_line.sale_person_type == 'retain':
      #     #                 incentive_amount += incentive_line.incentive_amount
      #     #                 account_id = incentive_line.account_id
      #     if incentive_id.sale_person_type in ['sale_person', 'gov_salesperson', 'retain']:
      #         accured_account_id = self.branch_id.incentive_account_id
      #     if incentive_id.sale_person_type in ['bu_br', 'gov_pooling']:
      #         accured_account_id = self.branch_id.pooling_account_id
            
      #     br = self.create_br_entry(incentive_id, accured_account_id, br)
      #     bu = self.create_bu_entry(incentive_id,accured_account_id, bu)
      #     return bu, br



      # def approve_finance_account(self):
      #     bu = []
      #     br = []
      #     amount = 0.0
                  
      #     for rec in self:
      #         if rec.branch_id:

      #             saleman_amt =0.0
      #             pooling_amt = 0.0
      #             retain_amt = 0.0
                     
                     
      #             for req_line in rec.incentive_request_line:
      #                 amount += req_line.total
                           
                              
      #                 for incentive_line in req_line.normal_incentive_id.line_ids:
      #                     incentive_amount =0.0
                                    
      #                     if incentive_line.sale_person_type == 'sale_person':
      #                         incentive_amount += incentive_line.incentive_amount
      #                         account_id = incentive_line.account_id[0]
      #                         print(incentive_amount,'sale man.........')
      #                     if incentive_line.sale_person_type == 'bu_br':
      #                         incentive_amount += incentive_line.incentive_amount
      #                         account_id = incentive_line.account_id[0]
      #                         print(incentive_amount,'pooling .........')
      #                     if incentive_line.sale_person_type == 'retain':
      #                         incentive_amount += incentive_line.incentive_amount
      #                         account_id = incentive_line.account_id
      #                     if incentive_line.sale_person_type in ['sale_person', 'gov_salesperson', 'retain']:
      #                         accured_account_id = self.branch_id.incentive_account_id
      #                     if incentive_line.sale_person_type in ['bu_br', 'gov_pooling']:
      #                         accured_account_id = self.branch_id.pooling_account_id
      #                 # bu, br = self.create_entry(incentive_line, br, bu)
      #                 # print(amount,'Incentive Amount////////////////////')
      #                 amount_currency = amount
      #                 amount = self.currency_id._convert(amount,
      #                                                 self.env.user.company_id.currency_id,
      #                                                 self.env.user.company_id,
      #                                                 datetime.today(),
      #                                                 )

      #             # Br
      #             move_line = {'name': self.name,
      #                         'partner_id': self.business_id.partner_id.id,
      #                         'account_id': self.branch_id.aff_account_receivable_id.id,
      #                         'business_id': self.branch_id.id,
      #                         'date': datetime.today(),
      #                         'amount_currency': amount_currency,
      #                         'debit': amount,
      #                         'currency_id': self.currency_id.id,
      #                         'incentive_id': self.id, }
      #             br.append(move_line)
      #             line_ids = [(0, 0, l) for l in br]
      #             br_move_vals = {
      #                 'journal_id': self.incentive_definition_id.journal_id.id,
      #                 'ref': self.name,
      #                 'date': datetime.today(),
      #                 'line_ids': line_ids,
      #             }
      #             print(br_move_vals,'xxxxxxxxxxxxxxxxxxxxxxxxxxx')
      #             self.env['account.move'].create(br_move_vals).action_post()

      #             # BU
      #             move_line = {'name': self.name,
      #                         'partner_id': self.branch_id.partner_id.id,
      #                         'account_id': self.business_id.aff_account_payable_id.id,
      #                         'business_id': self.business_id.id,
      #                         'date': datetime.today(),
      #                         'amount_currency': -amount_currency,
      #                         'credit': amount,
      #                         'currency_id': self.currency_id.id,
      #                         'incentive_id': self.id, }
      #             #print('bu move line************',move_line)
      #             bu.append(move_line)
      #             line_ids = [(0, 0, l) for l in bu]
      #             bu_move_vals = {
      #                 'journal_id': self.incentive_definition_id.journal_id.id,
      #                 'ref': self.name,
      #                 'date': datetime.today(),
      #                 'line_ids': line_ids,
      #             }
      #             #print(bu_move_vals,'>>>>>>>>>>>>>>>>>>>>.')
      #             self.env['account.move'].create(bu_move_vals).action_post()
      #             #print('bu moveeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee')
                              

      #         return rec.write({'state': 'incentive_approved'})

      # def prepare_bu_own_sale(self, incentive_id, accured_account_id, res):
      #     amount = self.currency_id._convert(incentive_id.incentive_amount,
      #                                        self.env.user.company_id.currency_id,
      #                                        self.env.user.company_id,
      #                                        datetime.today(),
      #                                        )

      #     move_line = {'name': incentive_id.name,
      #                  'partner_id': incentive_id.partner_id.id,
      #                  'account_id': incentive_id.account_id.id,
      #                  'business_id': incentive_id.business_id.id,
      #                  'date': datetime.today(),
      #                  'amount_currency': incentive_id.incentive_amount,
      #                  'debit': amount,
      #                  'currency_id': self.currency_id.id,
      #                  'incentive_id': self.id, }
      #     res.append(move_line)
      #     move_line = {'name': incentive_id.name,
      #                  'partner_id': incentive_id.partner_id.id,
      #                  'account_id': accured_account_id.id,
      #                  'business_id': incentive_id.business_id.id,
      #                  'date': datetime.today(),
      #                  'amount_currency': -incentive_id.incentive_amount,
      #                  'credit': amount,
      #                  'currency_id': self.currency_id.id,
      #                  'incentive_id': self.id, }
      #     res.append(move_line)
      #     return res

      def multi_pooling_paid(self, obj=None):
        active_ids = self._context.get('active_ids') if not obj else obj.ids
        request_ids = self.env['incentive.request'].browse(active_ids)
        for record in request_ids:
            record.pooling_paid()
        return True

      def multi_retain_paid(self, obj=None):
        active_ids = self._context.get('active_ids') if not obj else obj.ids
        request_ids = self.env['incentive.request'].browse(active_ids)
        for record in request_ids:
            record.retain_paid()
        return True

      def create_pooling_cfd_entry(self):
            mmk_currency_id = self.env.ref('base.MMK')
            res = []
            cfd_id = self.env['business.unit'].search([('business_type','=','cfd')])[0]
            partner_id = self.branch_id.partner_id if self.branch_id else self.business_id.partner_id
            # amount = self.amount/self.exchange_rate
            mmk_pooling_amount = self.pooling_amount
            amount = self.pooling_amount / self.exchange_rate
            move_line = {'name': self.name,
                        'partner_id': partner_id.id,
                        'account_id': self.journal_id.bank_pooling_account.id,
                        #  'account_id': self.journal_id.default_account_id.id,
                        'business_id': cfd_id.id,
                        'date': date.today(),
                        'amount_currency': -mmk_pooling_amount,
                        'credit': amount,
                        'currency_id': mmk_currency_id.id,
                        'request_incentive_id': self.id, }
            res.append(move_line)

            move_line = {'name': self.name,
                        'partner_id': partner_id.id,
                        'account_id': cfd_id.aff_account_receivable_id.id,
                        'business_id': cfd_id.id,
                        'date': date.today(),
                        'amount_currency': mmk_pooling_amount,
                        'debit': amount,
                        'currency_id': mmk_currency_id.id,
                        'request_incentive_id': self.id, }
            res.append(move_line)
            line_ids = [(0, 0, l) for l in res]
            move_vals = {
                  'partner_id': partner_id.id,
                  'journal_id': self.journal_id.id,
                  'ref': self.name,
                  'date': date.today(),
                  'line_ids': line_ids,
            }
            move_id = self.env['account.move'].create(move_vals)
            move_id.post()

      def create_pooling_bu_br_entry(self, partner_id):
            mmk_currency_id = self.env.ref('base.MMK')
      
            res = []
            branch_id = self.branch_id
            business_id = self.business_id
            mmk_pooling_amount = self.pooling_amount
            amount = self.pooling_amount/self.exchange_rate
            # amount = self.amount/request_incentive_id.exchange_rate
            # Bank/Cash Receive
            move_line = {'name': self.name,
                        'partner_id': partner_id.id,
                        'account_id': self.receive_journal_id.default_account_id.id,
                        'business_id': branch_id and branch_id.id or business_id.id or False,
                        'date': date.today(),
                        'amount_currency': mmk_pooling_amount,
                        'debit': amount,
                        'currency_id': mmk_currency_id.id,
                        'request_incentive_id': self.id, }
            res.append(move_line)

            #Aff:Payble For CFD
            move_line = {'name': self.name,
                        'partner_id': partner_id.id,
                        'account_id': branch_id and branch_id.aff_account_payable_id.id or business_id.aff_account_payable_id.id,
                        'business_id': branch_id and branch_id.id or business_id.id or False,
                        'date':date.today(),
                        'amount_currency': - mmk_pooling_amount,
                        'credit': amount,
                        'currency_id': mmk_currency_id.id,
                        'request_incentive_id': self.id, }
            res.append(move_line)
            line_ids = [(0, 0, l) for l in res]
            move_vals = {
                  'journal_id': self.receive_journal_id.id,
                  'ref': self.name,
                  'date': date.today(),
                  'line_ids': line_ids,
                  'hr_br_id':branch_id.id,
                  'hr_bu_id':business_id.id,
            }
            move_id = self.env['account.move'].create(move_vals)
            move_id.action_post()

            # Cash Move To Saleperson
            # Bank/Cash to Saleperson
            res = []
            move_line = {'name': self.name,
                        'partner_id': partner_id.id,
                        'account_id': self.receive_journal_id.default_account_id.id,
                        'business_id': branch_id and branch_id.id or business_id.id or False,
                        'date':date.today(),
                        'amount_currency': - mmk_pooling_amount,
                        'credit': amount,
                        'currency_id': mmk_currency_id.id,
                        'request_incentive_id': self.id, }
            res.append(move_line)
            #Close Accured Sale
            move_line = {'name': self.name,
                        'partner_id': partner_id.id,
                        'account_id': branch_id and branch_id.pooling_account_id.id or business_id.pooling_account_id.id,
                        'business_id': branch_id and branch_id.id or business_id.id or False,
                        'date':date.today(),
                        'amount_currency': mmk_pooling_amount,
                        'debit': amount,
                        'currency_id': mmk_currency_id.id,
                        'request_incentive_id': self.id, }
            res.append(move_line)
            line_ids = [(0, 0, l) for l in res]
            move_vals = {
                  'journal_id': self.receive_journal_id.id,
                  'ref': self.name,
                  'date': date.today(),
                  'line_ids': line_ids,
                  'hr_br_id':branch_id.id,
                  'hr_bu_id':business_id.id,
            }
            move_id = self.env['account.move'].create(move_vals)
            move_id.action_post()

        # return True

      def create_entry(self):
            # for request_id in self.env.context.get('active_ids'):

            #       request_incentive_id = self.env['incentive.request'].browse(request_id)

            # request_incentive_id = self.env['incentive.request'].browse(self._context.get('active_id'))
            partner_id = self.env['business.unit'].search([('business_type','=','cfd')])[0].partner_id
            self.create_pooling_cfd_entry()
            self.create_pooling_bu_br_entry(partner_id)
            self.paid_amount+=self.pooling_amount
            for req_line in self.incentive_request_line:
                  for line in req_line.normal_incentive_id:
                        line.write({'state': 'pooling_withdraw'})
            self.write({'state': 'pooling_withdraw'})

    
      def pooling_paid(self):
        return self.create_entry()



      
      def create_retain_cfd_entry(self):
            res = []
            mmk_currency_id = self.env.ref('base.MMK')
            cfd_id = self.env['business.unit'].search([('business_type','=','cfd')])[0]
            partner_id = self.branch_id.partner_id if self.branch_id else self.business_id.partner_id
            amount = self.retain_amount/self.exchange_rate
            # amount = self.amount/request_incentive_id.exchange_rate
            move_line = {'name': self.name,
                        'partner_id': partner_id.id,
                        'account_id': self.journal_id.default_account_id.id,
                        'business_id': cfd_id.id,
                        'date': date.today(),
                        'amount_currency': -self.retain_amount,
                        'credit': amount,
                        'currency_id': mmk_currency_id.id,
                        'request_incentive_id': self.id, }
            res.append(move_line)

            move_line = {'name': self.name,
                        'partner_id': partner_id.id,
                        'account_id': cfd_id.aff_account_receivable_id.id,
                        'business_id': cfd_id.id,
                        'date': date.today(),
                        'amount_currency': self.retain_amount,
                        'debit': amount,
                        'currency_id': mmk_currency_id.id,
                        'request_incentive_id': self.id, }
            res.append(move_line)
            line_ids = [(0, 0, l) for l in res]
            move_vals = {
                  'partner_id': partner_id.id,
                  'journal_id': self.journal_id.id,
                  'ref': self.name,
                  'date': date.today(),
                  'line_ids': line_ids,
            }
            move_id = self.env['account.move'].create(move_vals)
            move_id.action_post()
            # return move_id.action_post()

      def create_retain_bu_br_entry(self, partner_id):
            res = []
            branch_id = self.branch_id
            business_id = self.business_id
            mmk_currency_id = self.env.ref('base.MMK')
            # amount = self.currency_id._convert(self.amount,
            #                                             self.env.user.company_id.currency_id,
            #                                             self.env.user.company_id,
            #                                             datetime.today(),
            #                                         )
            # amount = self.amount/self.exchange_rate
            amount = self.retain_amount / self.exchange_rate
            # Bank/Cash Receive
            move_line = {'name': self.name,
                        'partner_id': partner_id.id,
                        'account_id': self.receive_journal_id.default_account_id.id,
                        'business_id': branch_id and branch_id.id or business_id.id or False,
                        'date': date.today(),
                        'amount_currency': self.retain_amount,
                        'debit': amount,
                        'currency_id': mmk_currency_id.id,
                        'request_incentive_id': self.id, }
            res.append(move_line)

            #Aff:Payble For CFD
            move_line = {'name': self.name,
                        'partner_id': partner_id.id,
                        'account_id': branch_id and branch_id.aff_account_payable_id.id or business_id.aff_account_payable_id.id,
                        'business_id': branch_id and branch_id.id or business_id.id or False,
                        'date': date.today(),
                        'amount_currency': -self.retain_amount,
                        'credit': amount,
                        'currency_id': mmk_currency_id.id,
                        'request_incentive_id': self.id, }
            res.append(move_line)
            line_ids = [(0, 0, l) for l in res]
            move_vals = {
                  'journal_id': self.receive_journal_id.id,
                  'ref': self.name,
                  'date': date.today(),
                  'line_ids': line_ids,
                  'hr_br_id':branch_id.id,
                  'hr_bu_id':business_id.id,
            }
            move_id = self.env['account.move'].create(move_vals)
            move_id.action_post()

            # Cash Move To Saleperson
            # Bank/Cash to Saleperson
            res = []
            move_line = {'name': self.name,
                        'partner_id': partner_id.id,
                        'account_id': self.receive_journal_id.default_account_id.id,
                        'business_id': branch_id and branch_id.id or business_id.id or False,
                        'date': date.today(),
                        'amount_currency': -self.retain_amount,
                        'credit': amount,
                        'currency_id': mmk_currency_id.id,
                        'request_incentive_id': self.id, }
            res.append(move_line)

            #Close Accured Sale
            move_line = {'name': self.name,
                        'partner_id': partner_id.id,
                        'account_id': branch_id and branch_id.incentive_account_id.id or business_id.incentive_account_id.id,
                        'business_id': branch_id and branch_id.id or business_id.id or False,
                        'date': date.today(),
                        'amount_currency': self.retain_amount,
                        'debit': amount,
                        'currency_id': mmk_currency_id.id,
                        'request_incentive_id': self.id, }
            res.append(move_line)
            line_ids = [(0, 0, l) for l in res]
            move_vals = {
                  'journal_id': self.receive_journal_id.id,
                  'ref': self.name,
                  'date': date.today(),
                  'line_ids': line_ids,
                  'hr_br_id':branch_id.id,
                  'hr_bu_id':business_id.id,
            }
            move_id = self.env['account.move'].create(move_vals)
            move_id.action_post()

            return True

      def retain_create_entry(self):
            
   
            partner_id = self.env['business.unit'].search([('business_type','=','cfd')])[0].partner_id
            self.create_retain_cfd_entry()
            self.create_retain_bu_br_entry(partner_id)
            self.paid_amount+=self.retain_amount
            for req_line in self.incentive_request_line:
                for line in req_line.normal_incentive_id:
                    line.state = 'retain_withdraw'
            self.write({'state': 'retain_withdraw'})

    

      def retain_paid(self):
        return self.retain_create_entry()


class IncentiveRequestLine(models.Model):
      _name = 'incentive.request.line'
      _description = 'Incentive Request.line'

      normal_incentive_id = fields.Many2one('normal.incentive.main')
      invoice_id = fields.Many2one('account.move')
      branch_id  = fields.Many2one('business.unit',domain=[('business_type','=','br')])
      business_id  = fields.Many2one('business.unit',domain=[('business_type','=','bu')])
      total = fields.Float(compute='compute_normal_incentive')
      amount_due = fields.Float()
      paid_amount = fields.Float()
      state = fields.Selection([
            ('draft', 'Draft'),
            ('request_incentive_approved', 'Request Incentive Approved'),
            ('incentive_approved', 'Incentive Approved'),
            ('incentive_withdraw', 'Incentive Withdraw'),
            ('pooling_withdraw', 'Pooling Withdraw'),
            ('retain_withdraw', 'Retain Withdraw'),
            ('incentive_partially_withdraw','Incentive Partially Withdraw'),
            ('close', 'Close'),
            ('reject', 'Rejected'),
      ], string="Status", readonly=True, default="draft", tracking=True, required=True)
      incentive_request_id = fields.Many2one('incentive.request')
      deduct_amount = fields.Float()
      currency_id = fields.Many2one('res.currency', string='Currency', required=True,
                                                  related="normal_incentive_id.currency_id")
      invoice_amount  = fields.Float()
      pooling_amount = fields.Float(compute='_compute_amount')
      retain_amount = fields.Float(compute='_compute_amount')
      saleman_amount = fields.Float(compute='_compute_amount')
      unit_or_part = fields.Selection([('unit', 'Unit'), ('part', 'Spare Part')], string='Units or Parts',related="normal_incentive_id.unit_or_part")
      remark = fields.Text()


      @api.depends('normal_incentive_id')
      def _compute_amount(self):
        for rec in self:
            rec.saleman_amount =0.0
            rec.pooling_amount =0.0
            rec.retain_amount = 0.0
            for line in rec.normal_incentive_id.line_ids:
                if line.sale_person_type in ['sale_person','gov_saleperson']:
                    rec.saleman_amount +=line.incentive_amount
                elif line.sale_person_type in ['bu_br','gov_pooling']:
                    rec.pooling_amount +=line.incentive_amount
                elif line.sale_person_type == 'retain':
                    rec.retain_amount +=line.incentive_amount
               
                else:
                    rec.saleman_amount =0.0
                    rec.pooling_amount =0.0
                    rec.retain_amount = 0.0



      @api.depends('normal_incentive_id')
      def compute_normal_incentive(self):
            for rec in self:
                  rec.total = rec.normal_incentive_id.total

      def action_run(self):
        
            for rec in self:

                  # rec.normal_incentive_id.line_ids.unlink()
                  rec.invoice_id.compute_incentive(rec.normal_incentive_id,rec.deduct_amount)
                  print('Incentive ID',rec.normal_incentive_id)
                  # rec.amount_due = rec.normal_incentive_id.due_amount
