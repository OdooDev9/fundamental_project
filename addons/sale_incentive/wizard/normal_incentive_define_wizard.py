from odoo import api, fields, models, _


class NormalIncentiveDefWiz(models.TransientModel):
	_name = 'normal.incentive.def.wizard'
	_description = 'Area Incentive Rules Wizard'
   
	incentive_fixed_rate = fields.Float(string="Incentive Fixed Rate")
	incentive_percentage = fields.Float(string="Incentive (%)")
	salesperson_incentive_rate = fields.Float(string="Salesperson Rate")
	bu_br_rate = fields.Float(string="Pooling BU/BR Rate")
	retain_rate = fields.Float(string="Retain for Salesperson Rate")
	sales_manager_rate = fields.Float(string="Areas Sales Manager")
	gov_salesperson_percentage = fields.Float('GOV Salesperson (%)')
	gov_pooling_percentage = fields.Float('GOV Pooling (%)')
	lower_range = fields.Float(string="By Section Amount(lower)")
	upper_range = fields.Float(string="By Section Amount(upper)")
	calculation_type = fields.Selection([
			('fixed_amount','Fixed Amount'),
			('fixed_percent','Fixed Percentage'),
			('fixed_percent_multi_agent','Fixed Percentage Division to Multi Agent'),
			('fixed_amount_multi_agent','Fixed Amount Division to Multi Agent'),
			('by_section_fixed_amount','By Sections Fixed Amount Division to Multi Agent'),
		],string="Calculation Type",required=True)
	rates_definition = fields.Selection([
			('category','By Product Category'),
			('product','By Product'),
			('sale_order_type','By Units or Parts'),
		],string="Rates Definition",required=True)
	salesperson_used = fields.Boolean(string="Used",default=False)
	bu_br_used = fields.Boolean(string="Used",default=False)
	government_salesperson_used = fields.Boolean('Used')
	government_pooling_used = fields.Boolean('Used')
	retain_for_salesperson_used = fields.Boolean(string="Used",default=False)
	area_sale_manager_used = fields.Boolean(string="Used",default=False)


	@api.model
	def default_get(self, fields):
		res = super(NormalIncentiveDefWiz, self).default_get(fields)
		active_id = self.env['normal.incentive.definition'].browse(self.env.context.get('active_id'))
		res.update({
						'calculation_type':active_id.calculation_type,
						'rates_definition':active_id.rates_definition,
						'salesperson_used':active_id.salesperson_used,
						'bu_br_used':active_id.bu_br_used,
						'government_salesperson_used':active_id.government_salesperson_used,
						'government_pooling_used':active_id.government_pooling_used,
						'retain_for_salesperson_used':active_id.retain_for_salesperson_used,
						'area_sale_manager_used':active_id.area_sale_manager_used})
		for line in active_id.incentive_rule_ids:

			res.update({
						'incentive_fixed_rate': line.incentive_fixed_rate,
						'incentive_percentage':line.incentive_percentage,
						'salesperson_incentive_rate':line.salesperson_incentive_rate,
						'bu_br_rate':line.bu_br_rate,
						'retain_rate':line.retain_rate,
						'sales_manager_rate':line.sales_manager_rate,
						'gov_salesperson_percentage':line.gov_salesperson_percentage,
						'gov_pooling_percentage':line.gov_pooling_percentage,
						'upper_range':line.upper_range,
						'lower_range':line.lower_range})
		return res
	
	def apply_rules(self):
		active_id = self.env['normal.incentive.definition'].browse(self.env.context.get('active_id'))
		vals ={
			'incentive_fixed_rate':self.incentive_fixed_rate,
			'incentive_percentage':self.incentive_percentage,
			'salesperson_incentive_rate':self.salesperson_incentive_rate,
			'bu_br_rate':self.bu_br_rate,
			'retain_rate':self.retain_rate,
			'sales_manager_rate':self.sales_manager_rate,
			'gov_salesperson_percentage':self.gov_salesperson_percentage,
			'gov_pooling_percentage':self.gov_pooling_percentage,
			'upper_range':self.upper_range,
			'lower_range':self.lower_range,
		}
		return active_id.incentive_rule_ids.write(vals)



	
	

