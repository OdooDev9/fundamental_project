from odoo import api, fields, models


class PoRejectWizard(models.TransientModel):
    _name = "po.reject.wizard"
    _description = "Purchase Reject Reason Wizard"

    reason = fields.Char(string='Reason', required=True)
    request_ids = fields.Many2many('purchase.order')

    @api.model
    def default_get(self, fields):
        res = super(PoRejectWizard, self).default_get(fields)
        active_ids = self.env.context.get('active_ids', [])

        res.update({
            'request_ids': active_ids,
        })
        return res

    def reject_reason(self):
        self.ensure_one()
        if self.request_ids:
            self.request_ids.refuse_goods(self.reason)
        return {'type': 'ir.actions.act_window_close'}
