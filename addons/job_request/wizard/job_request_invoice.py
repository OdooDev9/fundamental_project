
from odoo import fields, models, api
import logging
_logger = logging.getLogger(__name__)


class JobRequestInvoice(models.TransientModel):
    _name = 'job.request.invoice'
    _description = 'Job Request Invoice'

    service = fields.Float('Service Charge')
    name = fields.Char('Description')
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.company.currency_id.id)

    def create_invoice(self):
        order = self.env['job.request'].browse(self.env.context.get('active_id'))
        invoice_vals = self._prepare_invoice_values(order, self.name, self.service)

        invoice = self.env['account.move'].with_company(self.env.user.company_id) \
            .sudo().create(invoice_vals).with_user(self.env.uid)
        order.service_charge = self.service
        return invoice

    def _prepare_invoice_values(self, order, name, amount):
        invoice_vals = {
            'ref': order.name,
            'move_type': 'out_invoice',
            'invoice_origin': order.name,
            'invoice_user_id': self.env.uid,
            'partner_id': order.partner_id.id,
            'currency_id': self.currency_id.id,
            'hr_bu_id': order.business_id.id,
            'job_re_id': order.id,
            'invoice_line_ids': [(0, 0, {
                'name': name,
                'price_unit': amount,
                'quantity': 1.0,
            })],
        }

        return invoice_vals