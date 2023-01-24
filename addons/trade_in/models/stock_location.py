from odoo import models, fields, api,_



class StockLocation(models.Model):
    _inherit = 'stock.location'
    is_trade_in = fields.Boolean(string="Is Trade In")
    