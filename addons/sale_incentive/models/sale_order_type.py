from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError, ValidationError
import logging


class SaleOrderType(models.Model):
	_inherit = 'sale.order.type'

	#use_sale_team_target = fields.Boolean(string="Use Sale Team Target",default=False)

	# sale_team_target_id = fields.Many2one('sale.team.target',string="Sale Team Target",domain="[('state','=','ceo_approved')]")

	use_normal_incentive = fields.Boolean(string="Use Normal Incentive",default=False)

	normal_incentive_definition_id = fields.Many2one('normal.incentive.definition',string="Normal Incentive Definition",domain="[('rates_definition','=','sale_order_type')]")

	# @api.onchange('use_sale_team_target')
	# def onchange_use_sale_team_target(self):
	# 	for line in self:
	# 		if line.use_sale_team_target:
	# 			if line.use_normal_incentive:
	# 				raise ValidationError(_("You can only use one incentive rule. Choose either sale team target or normal incentive."))
	# 		if not line.use_sale_team_target:
	# 			line.sale_team_target_id = False


	@api.onchange('use_normal_incentive')
	def onchange_use_normal_incentive(self):
		for line in self:

			if not line.use_normal_incentive:
				line.normal_incentive_definition_id = False