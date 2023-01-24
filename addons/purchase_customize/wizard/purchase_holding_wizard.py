from odoo import api, fields, models


class PoHoldingWizard(models.TransientModel):
    _name = "po.holding.wizard"
    _description = "Purchase Holding Reason Wizard"

    reason = fields.Char(string='Reason', required=True)
    request_ids = fields.Many2many('purchase.order')

    @api.model
    def default_get(self, fields):
        res = super(PoHoldingWizard, self).default_get(fields)
        active_ids = self.env.context.get('active_ids', [])

        res.update({
            'request_ids': active_ids,
        })
        return res

    def hold_reason(self):
        self.ensure_one()
        if self.request_ids:
            self.request_ids.hold_goods(self.reason)
        return {'type': 'ir.actions.act_window_close'}
