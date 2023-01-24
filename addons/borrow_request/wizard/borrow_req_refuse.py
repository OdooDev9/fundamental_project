from odoo import api, fields, models

class BorrowRefuseWizard(models.TransientModel):
    _name = "borrow.refuse.wizard"
    _description = "Borrow Request Refuse Reason Wizard"

    reason = fields.Char(string='Reason', required=True)
    request_ids = fields.Many2many('borrow.request')
    
    @api.model
    def default_get(self, fields):
        res = super(BorrowRefuseWizard, self).default_get(fields)
        active_ids = self.env.context.get('active_ids', [])
       
        res.update({
            'request_ids': active_ids,
        })
        return res

    def borrow_refuse_reason(self):
        self.ensure_one()
        if self.request_ids:
            self.request_ids.refuse_goods(self.reason)
        return {'type': 'ir.actions.act_window_close'}
