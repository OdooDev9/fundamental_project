from odoo import api, fields, models, _


class PersonalSaleTargetApprovalWizard(models.TransientModel):
	_name = 'personal.sale.target.approval.wizard'
	_description = 'Personal Sale Target Approval Wizard'

	approval_person = fields.Many2one('res.partner', required=True)

	def request_order(self):
		target = self.env['personal.sale.target'].browse(self._context.get('active_id'))
		if self.approval_person:
			# order.order_approve_person = self.order_approve_person.id
			target.update({
					'approval_person':self.approval_person.id
				})

			if target.state in ['draft']:
				target.update({
						'state':'request_incentive_approved',
					})


