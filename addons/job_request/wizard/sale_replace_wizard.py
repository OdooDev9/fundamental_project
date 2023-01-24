from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


class SaleReplaceProduct(models.Model):
    _name = "sale.replace.product"
    _description = "Sale Replace Product"

    @api.model
    def default_get(self, fields):
        # by default all the rental order lines will be allocated as existing_product_ids.
        rec = super(SaleReplaceProduct, self).default_get(fields)
        sale_line = self.env['request.quotation.line'].browse(self.env.context.get('sale_order_line_id'))
        rec.update({
            'sale_order_line_id': sale_line.id,
            'old_product_id': sale_line.product_id.id,
            'replace_product_ids': sale_line.product_id.replace_product_ids
        })

        return rec

    sale_order_line_id = fields.Many2one('request.quotation.line', string='Order Line')
    replace_product_ids = fields.Many2many('product.product')
    product_id = fields.Many2one('product.product', 'Replace Product',domain=[('sale_ok', '=', True)], required=True)
    desc = fields.Text('Desc')
    old_product_id = fields.Many2one('product.product')

    @api.onchange('product_id')
    def onchange_field(self):
        available_ids = self.replace_product_ids.ids
        if self.product_id:
            self.desc = self.product_id.name
        return {'domain': {'product_id': [('id', '=', available_ids)]}}

    def action_replace_product(self):
        return True

    def action_replace_product(self):
        res = self.sale_order_line_id.write({'product_id': self.product_id.id, 'name': self.desc,
                                             'price_unit': self.product_id.list_price})
        if self.sale_order_line_id.request_id.part_order_id:
            self.sale_order_line_id.request_id.part_order_id.replace(self.old_product_id, self.product_id, self.desc)
            self.sale_order_line_id.request_id.part_order_id.job_ref_id.replace(self.old_product_id, self.product_id, self.desc, self.sale_order_line_id.product_uom_qty)
        return res