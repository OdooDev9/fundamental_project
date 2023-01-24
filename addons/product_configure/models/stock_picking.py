from odoo import api, models, fields


class StockPicking(models.Model):
    """Inherit Stock Picking."""

    _inherit = 'stock.picking'

    hr_bu_id = fields.Many2one('business.unit', string='Business Unit')
    unit_or_part = fields.Selection([('unit', 'Unit'), ('part', 'Spare Part')], string='Unit Or Part')


class stock_move(models.Model):
    _inherit = 'stock.move'

    hr_bu_id = fields.Many2one('business.unit', string='Business Unit', related='picking_id.hr_bu_id')

    @api.onchange('product_id')
    def onchange_bu_product(self):
        for rec in self.picking_id:
            return {'domain': {'product_id': [('business_id', '=', rec.hr_bu_id.id)]}}
