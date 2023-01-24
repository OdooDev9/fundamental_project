# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class PartHistory(models.Model):
    _name = "part.history"
    _description = "Part History"

    production_lot_id_custom = fields.Many2one('stock.production.lot', string="Production Lot Reference")
    start_date = fields.Date(string="Start Date", required=False, )
    end_date = fields.Date(string="End Date", required=False, )
    part_id = fields.Many2one('part.order', string="Part Order")
    invoice_amount = fields.Float('Invoice Amount')
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('confirm', 'Confirm'),
        ('close', 'Close'),
    ], string='Status')


class stock_production_lot(models.Model):
    _inherit = "stock.production.lot"

    def _compute_total_invoice_amount(self):
        for spl in self:
            sum = 0
            for rl in spl.part_history:
                sum += rl.invoice_amount
            spl.total_invoice_amount = sum

    part_history = fields.One2many(comodel_name="part.history", inverse_name="production_lot_id_custom",
                                   string="Part History", required=False, )
    total_invoice_amount = fields.Float('Total Invoice Amount', compute="_compute_total_invoice_amount")


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    replace_product_ids = fields.Many2many('product.product')


class ProductProduct(models.Model):
    _inherit = 'product.product'

    replace_product_ids = fields.Many2many(related="product_tmpl_id.replace_product_ids")
