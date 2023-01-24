from odoo import api, fields, models, _


class NormalIncentiveApprovalWizard(models.TransientModel):
	_name = 'normal.incentive.approval.wizard'
	_description = 'Normal Incentive Approval Wizard'

	approval_person = fields.Many2one('res.users', required=True)

	def request_order(self):
		parent_id = self.env['normal.incentive.main'].browse(self._context.get('active_id'))
		if self.approval_person:
			# order.order_approve_person = self.order_approve_person.id
			parent_id.approval_person = self.approval_person.id
			parent_id.state = 'request_incentive_approved'
			for items in parent_id.line_ids:
				items.approval_person = self.approval_person.id
				items.state = 'request_incentive_approved'


