from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError
class add_brand(models.Model):
    _name = 'product.brand'
    _description ="Product Brand"

    name = fields.Char(string='Brand')
    model_line_ids = fields.One2many('brand.model', 'brand_id', string='Models',
                                         copy=True, auto_join=True)

    @api.constrains('name')
    def check(self):
        matching_products = self.env['product.brand'].search([('name', '=', self.name)])
        if len(matching_products) > 1:
            raise UserError(_('Brand name already exit'))

class BrandModel(models.Model):
    _name = "brand.model"

    name = fields.Char("Model Name")
    brand_id = fields.Many2one('product.brand', string='Brand')


class Group(models.Model):
    _name = "group.model"

    name = fields.Char("Group Name")

class product_brand(models.Model):
    _inherit = 'product.template'
    brand = fields.Many2one('product.brand',string="Brand")
    machine_info = fields.Html(string='Machine Information')
    brand_model_id = fields.Many2one('brand.model', domain="[('brand_id', '=', brand)]")
    group_id = fields.Many2one('group.model', string="Group")

    @api.onchange('brand')
    def _brand_model_onchange(self):
        if self.brand:
            self.brand_model_id = False

