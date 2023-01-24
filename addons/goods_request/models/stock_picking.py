from odoo import api, models, fields, _
from ast import literal_eval
from odoo.exceptions import UserError, ValidationError
import logging

class stock_picking(models.Model):
	_inherit = 'stock.picking'

	request_ref_id = fields.Many2one('sale.order.request', string='Goods Request Ref')
	for_request_goods = fields.Boolean("stock move for request")