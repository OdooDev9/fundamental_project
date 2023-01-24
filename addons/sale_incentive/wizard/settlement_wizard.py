from odoo import models, fields, api, _ 
from odoo.exceptions import AccessError, UserError, ValidationError
import logging

class BranchSettlementWizard(models.TransientModel):
	_name = 'branch.settlement.wizard'
	_description = 'Branch Settlement Wizard'

	date_from = fields.Date('From',required=True,default=fields.Date.today())
	date_to = fields.Date('Up To',required=True,default=fields.Date.today())
	branch_id = fields.Many2one('business.unit',string="Branch Name",required=True,domain="[('business_type','=','br')]")

	incentive_ids = fields.Many2many('branch.incentive.settlement',string="Branch Incentive Settlement",compute="_compute_incentive_ids")

	@api.depends('date_from','date_to','branch_id')
	def _compute_incentive_ids(self):
		if self.date_from and self.date_to and self.branch_id:
			if self.date_from > self.date_to:
				raise ValidationError(_('Date from cannot greater than date to.'))

			# incentive_ids = self.env['branch.incentive.settlement'].sudo().search([('branch_id','=',self.branch_id.id),('start_date','>=',self.date_from),('end_date','<=',self.date_to),('state','=','draft')])

			# if incentive_ids:
			# 	self.incentive_ids = incentive_ids.ids
			# else:
			# 	self.incentive_ids = []

		else:
			self.incentive_ids = []



	def action_settle(self):

		if not self.incentive_ids:
			raise ValidationError(_('There is no incentive settlement for this branch.'))


		for incentive in self.incentive_ids:
			incentive.create_bill()


class NormalIncentiveSettlementWizard(models.TransientModel):
	_name = 'normal.incentive.settlement.wizard'
	_description = 'Normal Incentive Settlement Wizard'

	date_from = fields.Date('From',required=True,default=fields.Date.today())
	date_to = fields.Date('Up To',required=True,default=fields.Date.today())
	partner_id = fields.Many2one('res.partner',string="Partner Name",required=True)

	incentive_ids = fields.Many2many('normal.incentive',string="Incentives",compute="_compute_incentive_ids")

	@api.depends('date_from','date_to','partner_id')
	def _compute_incentive_ids(self):
		if self.date_from and self.date_to and self.partner_id:
			if self.date_from > self.date_to:
				raise ValidationError(_('Date from cannot greater than date to.'))

			incentive_ids = self.env['normal.incentive'].sudo().search([('partner_id','=',self.partner_id.id),('date','>=',self.date_from),('date','<=',self.date_to),('state','=','incentive_approved')])

			if incentive_ids:
				self.incentive_ids = incentive_ids.ids
			else:
				self.incentive_ids = []

		else:
			self.incentive_ids = []



	def action_settle(self):

		if not self.incentive_ids:
			raise ValidationError(_('There is no incentive settlement for this person.'))


		for incentive in self.incentive_ids:
			incentive.withdraw_incentive()