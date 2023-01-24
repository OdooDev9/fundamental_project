from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
import logging
_logger = logging.getLogger(__name__)

class CrmLead(models.Model):
	_inherit = 'crm.lead'

	job_request_count = fields.Integer(compute='_compute_job_request_count',string="Number of Job Request")
	job_request_ids = fields.One2many('job.request','opportunity_id',string='Job Request')

	def _compute_job_request_count(self):
		for lead in self:
			count = 0

			for request in lead.job_request_ids:
				if request.state not in ('cancel'):
					count += 1

			lead.job_request_count = count

	
	def action_job_request_new(self):
		_logger.info("work=====================")	
		if not self.partner_id:
			_logger.info("no partner_id =================")
			return self.env.ref("job_request.crm_job_request_partner_action").read()[0]
		else:
			return self.action_new_job_request()

	def action_new_job_request(self):
		_logger.info("action new job request ==============")
		action = self.env.ref("job_request.job_request_action").read()[0]
		action['context'] = {
			'search_default_opportunity_id':self.id,
			'default_opportunity_id':self.id,
			'search_default_partner_id':self.partner_id.id,
			'default_partner_id':self.partner_id.id,
			'default_team_id':self.team_id.id,
			'default_campaign_id':self.campaign_id.id,
			'default_medium_id':self.medium_id.id,
			'default_origin':self.name,
			'default_name':self.name,
			'default_source_id':self.source_id.id,
			'default_is_job_request':True,
		}
		return action


	def action_view_job_request(self):
		_logger.info("action_view_job_request work ====================")

		action = self.env.ref('job_request.job_request_action').read()[0]
		action['context'] = {
			'search_default_draft':1,
			'search_default_partner_id':self.partner_id.id,
			'default_partner_id':self.partner_id.id,
			'default_opportunity_id':self.id
		}

		action['domain'] = [('opportunity_id','=',self.id),('state','not in',['cancel'])]
		request = self.mapped('job_request_ids').filtered(lambda l:l.state not in ('cancel'))
		_logger.info(request)
		_logger.info("request =======================")
		if len(request) == 1 :
			action['views'] = [(self.env.ref('job_request.job_request_form_view').id,'form')]
			action['res_id'] = request.id

		return action