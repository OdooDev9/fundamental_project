from odoo import api, fields, models,_
import logging

_logger = logging.getLogger(__name__)

# MPT
class PartReplaceProduct(models.Model):
    _name = "part.replace.product"
    _description = "Part Replace Product"

    @api.model
    def default_get(self, fields):
        # by default all the part order lines will be allocated as existing_product_ids.
        rec = super(PartReplaceProduct, self).default_get(fields)
        part_replace_line = self.env['part.order.line'].browse(self.env.context.get('part_line_id'))
        rec.update({
            'part_line_id': part_replace_line.id,
            'old_product_id': part_replace_line.product_id.id,
            'replace_product_ids': part_replace_line.product_id.replace_product_ids
        })

        return rec

    part_line_id = fields.Many2one('part.order.line', string='Order Line')
    replace_product_ids = fields.Many2many('product.product')
    product_id = fields.Many2one('product.product', 'Replace Product', domain=[('sale_ok', '=', True)], required=True)
    desc = fields.Text('Desc')
    old_product_id = fields.Many2one('product.product')

    @api.onchange('product_id')
    def onchange_field(self):
        available_ids = self.replace_product_ids.ids
        if self.product_id:
            self.desc = self.product_id.name
        return {'domain': {'product_id': [('id', '=', available_ids)]}}

    def action_part_replace_product(self):
        return True

    def action_part_replace_product(self):
        res = self.part_line_id.write({'product_id': self.product_id.id, 'name': self.desc,
                                       'price_unit': self.product_id.list_price})
        if self.part_line_id.part_id:
            self.part_line_id.part_id.replace(self.old_product_id, self.product_id, self.desc)
            self.part_line_id.part_id.job_ref_id.replace(self.old_product_id, self.product_id,
                                                                          self.desc,
                                                                          self.part_line_id.product_uom_qty)
        return res
