from odoo import api, models, fields, _
from ast import literal_eval
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    goods_request_count = fields.Integer(string='Goods Request Count', compute='_compute_goods_request_count')
    request_ids = fields.One2many('sale.order.request', 'quote_name', string='Sale Order Request Ref')
    is_good_request =fields.Boolean()
    def _compute_goods_request_count(self):
        requests = []
        for order in self:
            request_ids = self.env['sale.order.request'].search([('quote_name', '=', order.id)])
            order.goods_request_count = len(request_ids)

    def action_view_delivery_rental(self):
        action = self.env.ref('goods_request.action_sale_order_request').read()[0]

        pickings = self.mapped('request_ids')
        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif pickings:
            action['views'] = [(self.env.ref('goods_request.view_sale_order_request_form').id, 'form')]
            action['res_id'] = pickings.id
        # Prepare the context.

        return action

