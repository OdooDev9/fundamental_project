from odoo import _, api, fields, models
from odoo.exceptions import UserError,AccessError

class LotSerialNoTransfer(models.TransientModel):
    _name = 'lot.serial.transfer.wizard'

    picking_id = fields.Many2one('stock.picking', 'Transfer')
    message =fields.Text()
    
    def confirm(self):
        return self.picking_id.button_validate()



