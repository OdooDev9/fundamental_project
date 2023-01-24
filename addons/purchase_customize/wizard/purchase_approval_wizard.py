from odoo import api, fields, models, _


class PurchaseApprovalWizard(models.TransientModel):
    _name = 'purchase.approval.wizard'
    _description = 'Purchase Approval Wizard'

    order_approve_person = fields.Many2one('res.partner', required=True)

    def request_order(self):
        order = self.env['purchase.order'].browse(self._context.get('active_id'))
        if self.order_approve_person:
            # order.order_approve_person = self.order_approve_person.id
            order.update({
                'order_approve_person': self.order_approve_person.id
            })

            if order.state in ['draft', 'sent', 'to_approve']:
                order.update({
                    'state': 'approved_by_gm_agm',
                })

            elif order.state in 'approved_by_gm_agm':
                if order.unit_or_part == 'part':
                    order.update({
                        'state': 'after_sale_approved',
                    })
                else:
                    order.update({
                        'state': 'approved_by_ceo',
                    })

            # elif order.state in 'approved_by_ceo':
            #     order.update({
            #         'state': 'request_dh_approval'
            #     })
            #
            # elif order.state in 'after_sale_approved':
            #     order.update({
            #         'state': 'request_dh_approval'
            #     })
            #
            # elif order.state in 'approved_by_dh':
            #     order.update({
            #         'state': 'request_2nd_approval_gm_agm',
            #     })



class PurchasePortalApproval(models.TransientModel):
	_name = 'purchase.portal.approval'
	_rec_name="approve_person"
	_description = "Purchase Portal Approval"

	approve_person = fields.Many2one('res.partner', required=True)

	def request_purchase(self):
		purchase = self.env['purchase.order'].browse(self._context.get('active_id'))
		if self.approve_person:
			purchase.approve_person = self.approve_person
		purchase.req = True
		return



