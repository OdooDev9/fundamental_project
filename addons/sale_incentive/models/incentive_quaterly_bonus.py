from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError, ValidationError
from dateutil import relativedelta
from datetime import datetime
import logging


class IncentiveQuaterlyBonus(models.Model):
	_name = 'incentive.quaterly.bonus'
	_inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
	_description = 'Incentive Quaterly Bonus'


	name = fields.Char(string="Name",required=True)

	branch_id = fields.Many2one('business.unit',string="Branch Name",required=True,domain="[('business_type','=','br')]")

	sale_person_id = fields.Many2one('res.users',string="Sale Person",required=True)

	state = fields.Selection([
			('draft','Draft'),
			('first_quater','Generated First Quater Bonus'),
			('second_quater','Generated Second Quater Bonus'),
			('done','Done'),
		],string="Status",readonly=True,default="draft",tracking=True)

	definition_id = fields.Many2one('bonus.rule.definition',string="Bonus Rule Definition",required=True)

	# rule_ids = fields.Many2many('incentive.quaterly.bonus.rule',string="Quaterly Bonus Rules",compute="_compute_rule_ids")

	start_date = fields.Date(string="Start Date (Fiscal Year)",required=True)
	end_date = fields.Date(string="End Date (Fiscal Year)",required=True)

	achievement_threadshold = fields.Float(string="Achievement Threadshold (%)",default=90.0)

	first_quater_bonus_ids = fields.One2many('first.quater.bonus','quaterly_bonus_id',string="First Quater Bonus")
	first_quater_bonus = fields.Float(string="First Quater Bonus",compute="_compute_first_quater_bonus")

	second_quater_bonus_ids = fields.One2many('second.quater.bonus','quaterly_bonus_id',string="Second Quater Bonus")
	second_quater_bonus = fields.Float(string="Second Quater Bonus",compute="_compute_second_quater_bonus")

	third_quater_bonus_ids = fields.One2many('third.quater.bonus','quaterly_bonus_id',string="Third Quater Bonus")
	third_quater_bonus = fields.Float(string="Third Quater Bonus")

	invoice_count = fields.Integer(string="Invoice Count",compute="_get_invoice_count",readonly=True)
	invoice_ids = fields.Many2many('account.move',string="Invoices",readonly=True)

	account_id = fields.Many2one('account.account',string="Account For Invoicing",required=True)
	journal_id = fields.Many2one('account.journal',string="Journal For Invoicing",required=True)
	product_id = fields.Many2one('product.product',string="Product for Invoicing",required=True)

	user_id = fields.Many2one('res.users',string="User",required=True,default=lambda self:self.env.user)

	@api.constrains('start_date','end_date')
	def _check_sale_person_contrains(self):
		for line in self:
			if line.start_date > line.end_date:
				raise ValidationError(_('Start date cannot be greater than end date.'))

	@api.model
	def create(self, vals):
		if 'start_date' in vals and 'end_date' in vals and 'sale_person_id' in vals:

			olds = self.env['incentive.quaterly.bonus'].search([('sale_person_id','=',vals['sale_person_id']),('start_date','=',vals['start_date']),('end_date','=',vals['end_date'])])

			if olds:
				raise ValidationError(_('Quaterly Bonus for this salesperson within selected period is already defined!'))

		result = super(IncentiveQuaterlyBonus,self).create(vals)

		return result



	def create_first_quater_bill(self):
		today_date = datetime.today().date() 
		months = []
		last_month = ''

		for line in self.first_quater_bonus_ids:
			months.append(line.quaterly_month)

		if str(today_date.month) in months:
			raise ValidationError(_('First Quater Bonus invoice can be generated after first quater period'))

		if self.first_quater_bonus == 0.0:
			#raise ValidationError(_('First Quater Bonus is zero.'))
			self.update({
					'state':'first_quater',
				})

		account_move = self.env['account.move']

		inv_line = [
			(0,0,{
					'name':self.product_id.name or '',
					'account_id':self.account_id.id,
					'price_unit':self.first_quater_bonus,
					'quantity':1.0,
					'product_uom_id':self.product_id.uom_id.id,
					'product_id':self.product_id.id,
				})
		]

		inv = account_move.create({
				'invoice_origin':self.name + '- First Quater Bonus',
				'type':'in_invoice',
				'ref':False,
				'invoice_line_ids':inv_line,
				'journal_id':self.journal_id.id,
				'partner_id':self.sale_person_id.partner_id.id,
				'user_id':self.user_id.id,
				'incentive_quaterly_bonus_id':self.id,
			})
		self.update({
				'state':'first_quater',
				'invoice_ids':[inv.id],
			})


		return True

	def create_second_quater_bill(self):
		today_date = datetime.today().date() 
		months = []
		last_month = ''

		for line in self.second_quater_bonus_ids:
			months.append(line.quaterly_month)

		if str(today_date.month) in months:
			raise ValidationError(_('Second Quater Bonus invoice can be generated after second quater period'))

		if self.second_quater_bonus == 0.0:
			#raise ValidationError(_('Second Quater Bonus is zero.'))
			self.update({
					'state':'second_quater',
				})

		account_move = self.env['account.move']

		inv_line = [
			(0,0,{
					'name':self.product_id.name or '',
					'account_id':self.account_id.id,
					'price_unit':self.second_quater_bonus,
					'quantity':1.0,
					'product_uom_id':self.product_id.uom_id.id,
					'product_id':self.product_id.id,
				})
		]

		inv = account_move.create({
				'invoice_origin':self.name + '- Second Quater Bonus',
				'type':'in_invoice',
				'ref':False,
				'invoice_line_ids':inv_line,
				'journal_id':self.journal_id.id,
				'partner_id':self.sale_person_id.partner_id.id,
				'user_id':self.user_id.id,
				'incentive_quaterly_bonus_id':self.id,
			})

		invoice_ids = []

		for invoice in self.invoice_ids:
			invoice_ids.append(invoice.id)

		invoice_ids.append(inv.id)

		self.update({
				'state':'second_quater',
				'invoice_ids':invoice_ids,
			})


		return True

	def create_third_quater_bill(self):
		today_date = datetime.today().date() 
		months = []
		last_month = ''

		for line in self.third_quater_bonus_ids:
			months.append(line.quaterly_month)

		if str(today_date.month) in months:
			raise ValidationError(_('Third Quater Bonus invoice can be generated after third quater period'))

		if self.third_quater_bonus == 0.0:
			#raise ValidationError(_('Third Quater Bonus is zero.'))
			self.update({
					'state':'done',
				})

		account_move = self.env['account.move']

		inv_line = [
			(0,0,{
					'name':self.product_id.name or '',
					'account_id':self.account_id.id,
					'price_unit':self.third_quater_bonus,
					'quantity':1.0,
					'product_uom_id':self.product_id.uom_id.id,
					'product_id':self.product_id.id,
				})
		]

		inv = account_move.create({
				'invoice_origin':self.name + '- Third Quater Bonus',
				'type':'in_invoice',
				'ref':False,
				'invoice_line_ids':inv_line,
				'journal_id':self.journal_id.id,
				'partner_id':self.sale_person_id.partner_id.id,
				'user_id':self.user_id.id,
				'incentive_quaterly_bonus_id':self.id,
			})

		invoice_ids = []

		for invoice in self.invoice_ids:
			invoice_ids.append(invoice.id)

		invoice_ids.append(inv.id)

		self.update({
				'state':'done',
				'invoice_ids':invoice_ids,
			})


		return True


	def action_view_invoice(self):

		invoices = self.mapped('invoice_ids')
		action = self.env.ref('account.action_move_out_invoice_type').read()[0]

		if len(invoices) > 1:
			action['domain'] = [('id','in',invoices.ids)]

		elif len(invoices) == 1:
			form_view = [(self.env.ref('account.view_move_form').id, 'form')]
			if 'views' in action:
				action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
			else:
				action['views'] = form_view
			action['res_id'] = invoices.id

		else:
			action = {'type':'ir.actions.act_window_close'}

		context = {
			'default_type':'out_invoice'
		}

		action['context'] = context
		return action



	@api.depends('invoice_ids')
	def _get_invoice_count(self):
		for line in self:
			line.invoice_count = len(line.invoice_ids)

	# @api.depends('definition_id')
	# def _compute_rule_ids(self):
	# 	for line in self:
	# 		_ids = False
	# 		if line.definition_id:
	# 			_ids = line.definition_id.rule_ids.ids
	# 		line.rule_ids = _ids

	@api.depends('first_quater_bonus_ids','definition_id')
	def _compute_first_quater_bonus(self):
		for line in self:
			if line.first_quater_bonus_ids:
				calculate_or_not = True
				total_sale_target = 0.0 
				total_sale = 0.0
				for bonus_line in line.first_quater_bonus_ids:
					if bonus_line.target_achievement_status == 'unachieve':
						calculate_or_not = False
						break
					else:
						total_sale_target += bonus_line.monthly_sale_target
						total_sale += bonus_line.monthly_sale_total

				if not calculate_or_not:
					line.first_quater_bonus = 0.0
				else:
					percent = 0.0 
					if total_sale_target > 0.0:
						percent = total_sale * (100/total_sale_target)
					bonus = 0.0
					if line.definition_id:
						found = False
						for rule in line.definition_id.rule_ids:
							if rule.sale_target_operator == '>=':
								if total_sale >= rule.sale_target_amount:
									
									if rule.performance_operator == '>=':
										if percent >= rule.upper_range:
											bonus = rule.bonus_incentive
											found = True
									elif rule.performance_operator == '>':
										if percent > rule.upper_range:
											bonus = rule.bonus_incentive
											found = True

									elif rule.performance_operator == 'between':
										if percent >= rule.lower_range and percent < rule.upper_range:
											bonus = rule.bonus_incentive
											found = True
										
									elif rule.performance_operator == '<=':
										if percent <= rule.lower_range:
											bonus = rule.bonus_incentive
											found = True

									elif rule.performance_operator == '<':
										if percent < rule.lower_range:
											bonus = rule.bonus_incentive
											found = True

							elif rule.sale_target_operator == '>':
								if total_sale > rule.sale_target_amount:
									
									if rule.performance_operator == '>=':
										if percent >= rule.upper_range:
											bonus = rule.bonus_incentive
											found = True
									elif rule.performance_operator == '>':
										if percent > rule.upper_range:
											bonus = rule.bonus_incentive
											found = True

									elif rule.performance_operator == 'between':
										if percent >= rule.lower_range and percent < rule.upper_range:
											bonus = rule.bonus_incentive
											found = True
										
									elif rule.performance_operator == '<=':
										if percent <= rule.lower_range:
											bonus = rule.bonus_incentive
											found = True

									elif rule.performance_operator == '<':
										if percent < rule.lower_range:
											bonus = rule.bonus_incentive
											found = True
							elif rule.sale_target_operator == '<=':
								if total_sale <= rule.sale_target_amount:
									if rule.is_special_condition:

										if rule.performance_operator == '>=':
											if total_sale >= rule.upper_range:
												bonus = rule.bonus_incentive
												found = True
										elif rule.performance_operator == '>':
											if total_sale > rule.upper_range:
												bonus = rule.bonus_incentive
												found = True

										elif rule.performance_operator == 'between':
											if total_sale >= rule.lower_range and total_sale < rule.upper_range:
												bonus = rule.bonus_incentive
												found = True
										
										elif rule.performance_operator == '<=':
											if total_sale <= rule.lower_range:
												bonus = rule.bonus_incentive
												found = True

										elif rule.performance_operator == '<':
											if total_sale < rule.lower_range:
												bonus = rule.bonus_incentive
												found = True
									else:
										if rule.performance_operator == '>=':
											if percent >= rule.upper_range:
												bonus = rule.bonus_incentive
												found = True
										elif rule.performance_operator == '>':
											if percent > rule.upper_range:
												bonus = rule.bonus_incentive
												found = True

										elif rule.performance_operator == 'between':
											if percent >= rule.lower_range and percent < rule.upper_range:
												bonus = rule.bonus_incentive
												found = True
											
										elif rule.performance_operator == '<=':
											if percent <= rule.lower_range:
												bonus = rule.bonus_incentive
												found = True

										elif rule.performance_operator == '<':
											if percent < rule.lower_range:
												bonus = rule.bonus_incentive
												found = True

							elif rule.sale_target_operator == '<':
								if total_sale <= rule.sale_target_amount:
									if rule.is_special_condition:

										if rule.performance_operator == '>=':
											if total_sale >= rule.upper_range:
												bonus = rule.bonus_incentive
												found = True
										elif rule.performance_operator == '>':
											if total_sale > rule.upper_range:
												bonus = rule.bonus_incentive
												found = True

										elif rule.performance_operator == 'between':
											if total_sale >= rule.lower_range and total_sale < rule.upper_range:
												bonus = rule.bonus_incentive
												found = True
										
										elif rule.performance_operator == '<=':
											if total_sale <= rule.lower_range:
												bonus = rule.bonus_incentive
												found = True

										elif rule.performance_operator == '<':
											if total_sale < rule.lower_range:
												bonus = rule.bonus_incentive
												found = True
									else:
										if rule.performance_operator == '>=':
											if percent >= rule.upper_range:
												bonus = rule.bonus_incentive
												found = True
										elif rule.performance_operator == '>':
											if percent > rule.upper_range:
												bonus = rule.bonus_incentive
												found = True

										elif rule.performance_operator == 'between':
											if percent >= rule.lower_range and percent < rule.upper_range:
												bonus = rule.bonus_incentive
												found = True
											
										elif rule.performance_operator == '<=':
											if percent <= rule.lower_range:
												bonus = rule.bonus_incentive
												found = True

										elif rule.performance_operator == '<':
											if percent < rule.lower_range:
												bonus = rule.bonus_incentive
												found = True

							if found:
								break

					line.first_quater_bonus = bonus

					
			else:
				line.first_quater_bonus = 0.0 


	@api.depends('second_quater_bonus_ids','definition_id')
	def _compute_second_quater_bonus(self):
		for line in self:
			if line.second_quater_bonus_ids:
				calculate_or_not = True
				total_sale_target = 0.0 
				total_sale = 0.0
				for bonus_line in line.second_quater_bonus_ids:
					if bonus_line.target_achievement_status == 'unachieve':
						calculate_or_not = False
						break
					else:
						total_sale_target += bonus_line.monthly_sale_target
						total_sale += bonus_line.monthly_sale_total

				if not calculate_or_not:
					line.second_quater_bonus = 0.0
				else:
					percent = 0.0
					if total_sale_target > 0.0:
						percent = total_sale * (100/total_sale_target)

					bonus = 0.0
					if line.definition_id:
						found = False
						for rule in line.definition_id.rule_ids:
							if rule.sale_target_operator == '>=':
								if total_sale >= rule.sale_target_amount:
									
									if rule.performance_operator == '>=':
										if percent >= rule.upper_range:
											bonus = rule.bonus_incentive
											found = True
									elif rule.performance_operator == '>':
										if percent > rule.upper_range:
											bonus = rule.bonus_incentive
											found = True

									elif rule.performance_operator == 'between':
										if percent >= rule.lower_range and percent < rule.upper_range:
											bonus = rule.bonus_incentive
											found = True
										
									elif rule.performance_operator == '<=':
										if percent <= rule.lower_range:
											bonus = rule.bonus_incentive
											found = True

									elif rule.performance_operator == '<':
										if percent < rule.lower_range:
											bonus = rule.bonus_incentive
											found = True

							elif rule.sale_target_operator == '>':
								if total_sale > rule.sale_target_amount:
									
									if rule.performance_operator == '>=':
										if percent >= rule.upper_range:
											bonus = rule.bonus_incentive
											found = True
									elif rule.performance_operator == '>':
										if percent > rule.upper_range:
											bonus = rule.bonus_incentive
											found = True

									elif rule.performance_operator == 'between':
										if percent >= rule.lower_range and percent < rule.upper_range:
											bonus = rule.bonus_incentive
											found = True
										
									elif rule.performance_operator == '<=':
										if percent <= rule.lower_range:
											bonus = rule.bonus_incentive
											found = True

									elif rule.performance_operator == '<':
										if percent < rule.lower_range:
											bonus = rule.bonus_incentive
											found = True
							elif rule.sale_target_operator == '<=':
								if total_sale <= rule.sale_target_amount:
									if rule.is_special_condition:

										if rule.performance_operator == '>=':
											if total_sale >= rule.upper_range:
												bonus = rule.bonus_incentive
												found = True
										elif rule.performance_operator == '>':
											if total_sale > rule.upper_range:
												bonus = rule.bonus_incentive
												found = True

										elif rule.performance_operator == 'between':
											if total_sale >= rule.lower_range and total_sale < rule.upper_range:
												bonus = rule.bonus_incentive
												found = True
										
										elif rule.performance_operator == '<=':
											if total_sale <= rule.lower_range:
												bonus = rule.bonus_incentive
												found = True

										elif rule.performance_operator == '<':
											if total_sale < rule.lower_range:
												bonus = rule.bonus_incentive
												found = True
									else:
										if rule.performance_operator == '>=':
											if percent >= rule.upper_range:
												bonus = rule.bonus_incentive
												found = True
										elif rule.performance_operator == '>':
											if percent > rule.upper_range:
												bonus = rule.bonus_incentive
												found = True

										elif rule.performance_operator == 'between':
											if percent >= rule.lower_range and percent < rule.upper_range:
												bonus = rule.bonus_incentive
												found = True
											
										elif rule.performance_operator == '<=':
											if percent <= rule.lower_range:
												bonus = rule.bonus_incentive
												found = True

										elif rule.performance_operator == '<':
											if percent < rule.lower_range:
												bonus = rule.bonus_incentive
												found = True

							elif rule.sale_target_operator == '<':
								if total_sale <= rule.sale_target_amount:
									if rule.is_special_condition:

										if rule.performance_operator == '>=':
											if total_sale >= rule.upper_range:
												bonus = rule.bonus_incentive
												found = True
										elif rule.performance_operator == '>':
											if total_sale > rule.upper_range:
												bonus = rule.bonus_incentive
												found = True

										elif rule.performance_operator == 'between':
											if total_sale >= rule.lower_range and total_sale < rule.upper_range:
												bonus = rule.bonus_incentive
												found = True
										
										elif rule.performance_operator == '<=':
											if total_sale <= rule.lower_range:
												bonus = rule.bonus_incentive
												found = True

										elif rule.performance_operator == '<':
											if total_sale < rule.lower_range:
												bonus = rule.bonus_incentive
												found = True
									else:
										if rule.performance_operator == '>=':
											if percent >= rule.upper_range:
												bonus = rule.bonus_incentive
												found = True
										elif rule.performance_operator == '>':
											if percent > rule.upper_range:
												bonus = rule.bonus_incentive
												found = True

										elif rule.performance_operator == 'between':
											if percent >= rule.lower_range and percent < rule.upper_range:
												bonus = rule.bonus_incentive
												found = True
											
										elif rule.performance_operator == '<=':
											if percent <= rule.lower_range:
												bonus = rule.bonus_incentive
												found = True

										elif rule.performance_operator == '<':
											if percent < rule.lower_range:
												bonus = rule.bonus_incentive
												found = True

							if found:
								break
								
					line.second_quater_bonus = bonus

					
			else:
				line.second_quater_bonus = 0.0

	@api.depends('third_quater_bonus_ids','definition_id')
	def _compute_third_quater_bonus(self):
		for line in self:
			if line.third_quater_bonus_ids:
				calculate_or_not = True
				total_sale_target = 0.0 
				total_sale = 0.0
				for bonus_line in line.third_quater_bonus_ids:
					if bonus_line.target_achievement_status == 'unachieve':
						calculate_or_not = False
						break
					else:
						total_sale_target += bonus_line.monthly_sale_target
						total_sale += bonus_line.monthly_sale_total

				if not calculate_or_not:
					line.third_quater_bonus = 0.0
				else:
					percent = 0.0
					if total_sale_target > 0:
						percent = total_sale * (100/total_sale_target)
					bonus = 0.0
					if line.definition_id:
						found = False
						for rule in line.definition_id.rule_ids:
							if rule.sale_target_operator == '>=':
								if total_sale >= rule.sale_target_amount:
									
									if rule.performance_operator == '>=':
										if percent >= rule.upper_range:
											bonus = rule.bonus_incentive
											found = True
									elif rule.performance_operator == '>':
										if percent > rule.upper_range:
											bonus = rule.bonus_incentive
											found = True

									elif rule.performance_operator == 'between':
										if percent >= rule.lower_range and percent < rule.upper_range:
											bonus = rule.bonus_incentive
											found = True
										
									elif rule.performance_operator == '<=':
										if percent <= rule.lower_range:
											bonus = rule.bonus_incentive
											found = True

									elif rule.performance_operator == '<':
										if percent < rule.lower_range:
											bonus = rule.bonus_incentive
											found = True

							elif rule.sale_target_operator == '>':
								if total_sale > rule.sale_target_amount:
									
									if rule.performance_operator == '>=':
										if percent >= rule.upper_range:
											bonus = rule.bonus_incentive
											found = True
									elif rule.performance_operator == '>':
										if percent > rule.upper_range:
											bonus = rule.bonus_incentive
											found = True

									elif rule.performance_operator == 'between':
										if percent >= rule.lower_range and percent < rule.upper_range:
											bonus = rule.bonus_incentive
											found = True
										
									elif rule.performance_operator == '<=':
										if percent <= rule.lower_range:
											bonus = rule.bonus_incentive
											found = True

									elif rule.performance_operator == '<':
										if percent < rule.lower_range:
											bonus = rule.bonus_incentive
											found = True
							elif rule.sale_target_operator == '<=':
								if total_sale <= rule.sale_target_amount:
									if rule.is_special_condition:

										if rule.performance_operator == '>=':
											if total_sale >= rule.upper_range:
												bonus = rule.bonus_incentive
												found = True
										elif rule.performance_operator == '>':
											if total_sale > rule.upper_range:
												bonus = rule.bonus_incentive
												found = True

										elif rule.performance_operator == 'between':
											if total_sale >= rule.lower_range and total_sale < rule.upper_range:
												bonus = rule.bonus_incentive
												found = True
										
										elif rule.performance_operator == '<=':
											if total_sale <= rule.lower_range:
												bonus = rule.bonus_incentive
												found = True

										elif rule.performance_operator == '<':
											if total_sale < rule.lower_range:
												bonus = rule.bonus_incentive
												found = True
									else:
										if rule.performance_operator == '>=':
											if percent >= rule.upper_range:
												bonus = rule.bonus_incentive
												found = True
										elif rule.performance_operator == '>':
											if percent > rule.upper_range:
												bonus = rule.bonus_incentive
												found = True

										elif rule.performance_operator == 'between':
											if percent >= rule.lower_range and percent < rule.upper_range:
												bonus = rule.bonus_incentive
												found = True
											
										elif rule.performance_operator == '<=':
											if percent <= rule.lower_range:
												bonus = rule.bonus_incentive
												found = True

										elif rule.performance_operator == '<':
											if percent < rule.lower_range:
												bonus = rule.bonus_incentive
												found = True

							elif rule.sale_target_operator == '<':
								if total_sale <= rule.sale_target_amount:
									if rule.is_special_condition:

										if rule.performance_operator == '>=':
											if total_sale >= rule.upper_range:
												bonus = rule.bonus_incentive
												found = True
										elif rule.performance_operator == '>':
											if total_sale > rule.upper_range:
												bonus = rule.bonus_incentive
												found = True

										elif rule.performance_operator == 'between':
											if total_sale >= rule.lower_range and total_sale < rule.upper_range:
												bonus = rule.bonus_incentive
												found = True
										
										elif rule.performance_operator == '<=':
											if total_sale <= rule.lower_range:
												bonus = rule.bonus_incentive
												found = True

										elif rule.performance_operator == '<':
											if total_sale < rule.lower_range:
												bonus = rule.bonus_incentive
												found = True
									else:
										if rule.performance_operator == '>=':
											if percent >= rule.upper_range:
												bonus = rule.bonus_incentive
												found = True
										elif rule.performance_operator == '>':
											if percent > rule.upper_range:
												bonus = rule.bonus_incentive
												found = True

										elif rule.performance_operator == 'between':
											if percent >= rule.lower_range and percent < rule.upper_range:
												bonus = rule.bonus_incentive
												found = True
											
										elif rule.performance_operator == '<=':
											if percent <= rule.lower_range:
												bonus = rule.bonus_incentive
												found = True

										elif rule.performance_operator == '<':
											if percent < rule.lower_range:
												bonus = rule.bonus_incentive
												found = True

							if found:
								break
								
					line.third_quater_bonus = bonus

					
			else:
				line.third_quater_bonus = 0.0

	@api.onchange('end_date')
	def _onchange_end_date(self):
		for line in self:
			if line.end_date and not line.start_date:
				raise ValidationError(_('Please Choose start date first!'))

			if line.end_date and line.start_date:
				first_quater = [(6,0,[])]
				second_quater = [(6,0,[])]
				third_quater = [(6,0,[])]

				r = relativedelta.relativedelta(line.end_date,line.start_date)
				
				months_diff = (r.years*12) + r.months
				if months_diff == 11 or months_diff == 12:
					months_diff = 12
				else:
					raise ValidationError(_('Fiscal Year must be 1 year'))

				index = 1
				start_date = line.start_date
				while(True):
					if index > 12:
						break

					month = start_date.month
					logging.info("month --------------")
					logging.info(month)

					if index in [1,2,3,4]:
						first_quater.append((0,0,{
							'quaterly_month':str(month),
							}))

					elif index in [5,6,7,8]:
						second_quater.append((0,0,{
								'quaterly_month':str(month),
							}))
					else:
						third_quater.append((0,0,{
								'quaterly_month':str(month),
							}))

					index += 1
					start_date = start_date + relativedelta.relativedelta(months=1)

				line.first_quater_bonus_ids = first_quater
				line.second_quater_bonus_ids = second_quater
				line.third_quater_bonus_ids = third_quater

class BonusRuleDefinition(models.Model):
	_name = 'bonus.rule.definition'
	_description = 'Bonus Rule Definition'

	name = fields.Char(string="Bonus Rule Name")

	rule_ids = fields.One2many('incentive.quaterly.bonus.rule','definition_id',string="Rules")


class IncentiveQuaterlyBonusRule(models.Model):
	_name = 'incentive.quaterly.bonus.rule'
	_description = 'Incentive Quaterly Bonus Rule'


	definition_id = fields.Many2one('bonus.rule.definition',string="Quaterly Bonus",required=True,ondelete="cascade")

	sale_target_operator = fields.Selection([
			('<','<'),
			('<=','<='),
			('>','>'),
			('>=','>='),
		],string="Operator",default="<")

	sale_target_amount = fields.Float(string="Sale Target Amount")

	is_special_condition = fields.Boolean(string="Is Special")

	lower_range = fields.Float(string="Performance (Lower)")
	upper_range = fields.Float(string="Performance (Upper)")
	performance_operator = fields.Selection([
			('>=','>='),
			('>','>'),
			('<=','<='),
			('<','<'),
			('between','Between')
		],string="Performance Operator",default=">=")

	bonus_incentive = fields.Float(string="Bonus Incentive (Monthly)")

class FirstQuaterBonus(models.Model):
	_name = 'first.quater.bonus'
	_description = 'First Quater Bonus'


	quaterly_bonus_id = fields.Many2one('incentive.quaterly.bonus',string="Quaterly Bonus Id",required=True,ondelete="cascade")

	quaterly_month = fields.Selection([
			('1','Jan'),
			('2','Feb'),
			('3','Mar'),
			('4','Apr'),
			('5','May'),
			('6','Jun'),
			('7','July'),
			('8','Aug'),
			('9','Sep'),
			('10','Oct'),
			('11','Nov'),
			('12','Dec')
		],string="Month")

	monthly_sale_target = fields.Float(string="Monthly Sale Target")

	monthly_sale_total = fields.Float(string="Monthly Sale Total",compute="_compute_monthly_sale_total")

	target_achievement_status = fields.Selection([
			('achieve','Target Achieve'),
			('unachieve','Target Unachieve'),
		],string="Achievement Status",default="achieve",compute="_compute_target_achievement_status")


	@api.depends('quaterly_month','quaterly_bonus_id')
	def _compute_monthly_sale_total(self):
		for line in self:
			total = 0.0 
			if line.quaterly_month and line.quaterly_bonus_id:
				start_date = line.quaterly_bonus_id.start_date
				end_date = line.quaterly_bonus_id.end_date
				sale_person_id = line.quaterly_bonus_id.sale_person_id
				current_start_date = start_date
				current_end_date = end_date

				while(True):
					if not start_date or not end_date:
						break
					if start_date > end_date:
						break
					if str(start_date.month) == line.quaterly_month:
						current_start_date = datetime(start_date.year,start_date.month,1).date()
						temp = datetime(start_date.year,start_date.month,1) + relativedelta.relativedelta(months=1,days=-1)

						current_end_date = temp.date()
						break

					t_date = datetime(start_date.year,start_date.month,start_date.day) + relativedelta.relativedelta(months=1)

					start_date = t_date.date()

				invoices = self.env['account.move'].search([('invoice_user_id','=',sale_person_id.id),('invoice_date','>=',current_start_date),('invoice_date','<=',current_end_date),('state','=','posted')])
				for invoice in invoices:
					total += invoice.amount_total
					


			line.monthly_sale_total = total


	@api.depends('monthly_sale_target','monthly_sale_total','quaterly_bonus_id')
	def _compute_target_achievement_status(self):
		for line in self:
			ach_status = 'unachieve'
			if line.monthly_sale_target and line.monthly_sale_total and line.quaterly_bonus_id.achievement_threadshold:
				if line.monthly_sale_target > 0.0:
					percent = line.monthly_sale_total * (100/line.monthly_sale_target)
				else:
					percent = 0.0

				if percent >= line.quaterly_bonus_id.achievement_threadshold:
					ach_status = 'achieve'
			line.target_achievement_status = ach_status



class SecondQuaterBonus(models.Model):
	_name = 'second.quater.bonus'
	_description = 'Second Quater Bonus'


	quaterly_bonus_id = fields.Many2one('incentive.quaterly.bonus',string="Quaterly Bonus Id",required=True,ondelete="cascade")

	quaterly_month = fields.Selection([
			('1','Jan'),
			('2','Feb'),
			('3','Mar'),
			('4','Apr'),
			('5','May'),
			('6','Jun'),
			('7','July'),
			('8','Aug'),
			('9','Sep'),
			('10','Oct'),
			('11','Nov'),
			('12','Dec')
		],string="Month")

	monthly_sale_target = fields.Float(string="Monthly Sale Target")

	monthly_sale_total = fields.Float(string="Monthly Sale Total",compute="_compute_monthly_sale_total")

	target_achievement_status = fields.Selection([
			('achieve','Target Achieve'),
			('unachieve','Target Unachieve'),
		],string="Achievement Status",default="achieve",compute="_compute_target_achievement_status")

	@api.depends('quaterly_month','quaterly_bonus_id')
	def _compute_monthly_sale_total(self):
		for line in self:
			total = 0.0 
			if line.quaterly_month and line.quaterly_bonus_id:
				start_date = line.quaterly_bonus_id.start_date
				end_date = line.quaterly_bonus_id.end_date
				sale_person_id = line.quaterly_bonus_id.sale_person_id
				current_start_date = start_date
				current_end_date = end_date

				while(True):
					if not start_date or not end_date:
						break
					if start_date > end_date:
						break

					if str(start_date.month) == line.quaterly_month:
						current_start_date = datetime(start_date.year,start_date.month,1).date()
						temp = datetime(start_date.year,start_date.month,1) + relativedelta.relativedelta(months=1,days=-1)

						current_end_date = temp.date()
						break

					t_date = datetime(start_date.year,start_date.month,start_date.day) + relativedelta.relativedelta(months=1)

					start_date = t_date.date()

				invoices = self.env['account.move'].search([('invoice_user_id','=',sale_person_id.id),('invoice_date','>=',current_start_date),('invoice_date','<=',current_end_date),('state','=','posted')])
				for invoice in invoices:
					total += invoice.amount_total

			line.monthly_sale_total = total

	@api.depends('monthly_sale_target','monthly_sale_total','quaterly_bonus_id')
	def _compute_target_achievement_status(self):
		for line in self:
			ach_status = 'unachieve'
			if line.monthly_sale_target and line.monthly_sale_total and line.quaterly_bonus_id.achievement_threadshold:
				if line.monthly_sale_target > 0.0:
					percent = line.monthly_sale_total * (100/line.monthly_sale_target)
				else:
					percent = 0.0

				if percent >= line.quaterly_bonus_id.achievement_threadshold:
					ach_status = 'achieve'
			line.target_achievement_status = ach_status

class ThirdQuaterBonus(models.Model):
	_name = 'third.quater.bonus'
	_description = 'Third Quater Bonus'


	quaterly_bonus_id = fields.Many2one('incentive.quaterly.bonus',string="Quaterly Bonus Id",required=True,ondelete="cascade")

	quaterly_month = fields.Selection([
			('1','Jan'),
			('2','Feb'),
			('3','Mar'),
			('4','Apr'),
			('5','May'),
			('6','Jun'),
			('7','July'),
			('8','Aug'),
			('9','Sep'),
			('10','Oct'),
			('11','Nov'),
			('12','Dec')
		],string="Month")

	monthly_sale_target = fields.Float(string="Monthly Sale Target")

	monthly_sale_total = fields.Float(string="Monthly Sale Total",compute="_compute_monthly_sale_total")

	target_achievement_status = fields.Selection([
			('achieve','Target Achieve'),
			('unachieve','Target Unachieve'),
		],string="Achievement Status",default="achieve",compute="_compute_target_achievement_status")


	@api.depends('quaterly_month','quaterly_bonus_id')
	def _compute_monthly_sale_total(self):
		for line in self:
			total = 0.0 
			if line.quaterly_month and line.quaterly_bonus_id:
				start_date = line.quaterly_bonus_id.start_date
				end_date = line.quaterly_bonus_id.end_date
				sale_person_id = line.quaterly_bonus_id.sale_person_id
				current_start_date = start_date
				current_end_date = end_date

				while(True):
					if not start_date or not end_date:
						break
					if start_date > end_date:
						break

					if str(start_date.month) == line.quaterly_month:
						current_start_date = datetime(start_date.year,start_date.month,1).date()
						temp = datetime(start_date.year,start_date.month,1) + relativedelta.relativedelta(months=1,days=-1)

						current_end_date = temp.date()
						break

					t_date = datetime(start_date.year,start_date.month,start_date.day) + relativedelta.relativedelta(months=1)

					start_date = t_date.date()

				invoices = self.env['account.move'].search([('invoice_user_id','=',sale_person_id.id),('invoice_date','>=',current_start_date),('invoice_date','<=',current_end_date),('state','=','posted')])
				for invoice in invoices:
					total += invoice.amount_total

			line.monthly_sale_total = total

	@api.depends('monthly_sale_target','monthly_sale_total','quaterly_bonus_id')
	def _compute_target_achievement_status(self):
		for line in self:
			ach_status = 'unachieve'
			if line.monthly_sale_target and line.monthly_sale_total and line.quaterly_bonus_id.achievement_threadshold:
				if line.monthly_sale_target > 0.0:
					percent = line.monthly_sale_total * (100/line.monthly_sale_target)
				else:
					percent = 0.0

				if percent >= line.quaterly_bonus_id.achievement_threadshold:
					ach_status = 'achieve'
			line.target_achievement_status = ach_status


