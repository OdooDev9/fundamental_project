from odoo import api, fields, models, _


class SaleTargetApprovalWizard(models.TransientModel):
	_name = 'sale.target.approval.wizard'
	_description = 'Sale Target Approval Wizard'

	approval_person = fields.Many2one('res.partner', required=True)

	def request_order(self):
		target = self.env['sale.target'].browse(self._context.get('active_id'))
		if self.approval_person:
			# order.order_approve_person = self.order_approve_person.id
			target.update({
					'approval_person':self.approval_person.id
				})

			if target.state in ['draft']:
				target.update({
						'state':'request_related_dh_approve',
					})
			elif target.state in 'related_dh_approved':
				target.update({
						'state':'request_gm_approve'
					})
			elif target.state in 'gm_approved':
				target.update({
						'state':'request_coo_approve',
					})
			elif target.state in 'coo_approved':
				target.update({
						'state':'request_ceo_approve',
					})


