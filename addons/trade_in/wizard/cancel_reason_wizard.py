from odoo import api, fields, models, _

class RentalRenew(models.TransientModel):
	_name = 'trade.reason'
	_rec_name="reason"
	_description = "Reason"

	reason = fields.Text(string="Reason", required=False)

	def cancel_reason(self):
		cancel = self.env['trade_in.trade_in'].browse(self._context.get('active_id'))
		cancel.state = 'cancel'
		msg = 'Cancel Reason:'+ str(self.reason)
		cancel.message_post(body=msg)
		return