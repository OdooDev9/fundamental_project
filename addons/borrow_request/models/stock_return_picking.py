
from odoo.exceptions import UserError
from odoo import _, api, fields, models
from datetime import datetime
class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    return_reason = fields.Text(string="Reason")
    borrow_to_date = fields.Datetime()
    reason_required = fields.Boolean('reason_required')
    
    @api.model
    def default_get(self, fields):
        # res = super(ReturnPicking, self).default_get(fields)
        # if self.env.context.get('active_id') and self.env.context.get('active_model') == 'stock.picking':
        #     if len(self.env.context.get('active_ids', list())) > 1:
        #         raise UserError(_("You may only return one picking at a time."))
        #     picking = self.env['stock.picking'].browse(self.env.context.get('active_id'))
        #     if picking.exists():
        #         res.update({'picking_id': picking.id})
        result = super(ReturnPicking, self).default_get(fields)
        picking = self.env['stock.picking'].browse(self.env.context.get('active_id'))
        if picking.exists() and picking.origin.startswith( 'BR' ):
            borrow = self.env['borrow.request'].search([('name', '=', picking.origin)])
            result.update({'borrow_to_date': borrow.to_date})
            if borrow.to_date < datetime.now():
                result.update({'reason_required': True})
        return result

    def _create_returns(self):
        result = super(ReturnPicking, self)._create_returns()
        picking = self.env['stock.picking'].browse(self.env.context.get('active_id'))
        if picking.exists() and picking.origin.startswith( 'BR' ):
            borrow = self.env['borrow.request'].search([('name', '=', picking.origin)])
            borrow.write({'return_reason': self.return_reason})
        return result
        