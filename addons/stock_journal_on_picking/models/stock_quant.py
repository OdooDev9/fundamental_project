from odoo import _, api, fields, models


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    state = fields.Selection(selection=[
            ('draft', 'Draft'),
            ('approved_inv_head', 'Approved Inventory Head'),
            ('approved_finance_head','Approved F & A Head'),
            ('approved_gm_agm','Approved GM/AGM'),
            ('posted', 'Posted'),
            ('cancel', 'Cancelled'),
        ], string='Status', required=True, readonly=True, copy=False, tracking=True,
        default='draft')
    def action_approve_inv_head(self):
        self.state = 'approved_inv_head'
    def action_approve_finance_head(self):
         self.state = 'approved_finance_head'
    def action_approve_gm_agm(self):
         self.state = 'approved_gm_agm'