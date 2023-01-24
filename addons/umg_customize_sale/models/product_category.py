# # -*- coding: utf-8 -*-
# # Part of Odoo. See LICENSE file for full copyright and licensing details.

# import logging
# import re

# from odoo import api, fields, models, tools, _
# from odoo.exceptions import UserError, ValidationError
# from odoo.osv import expression


# from odoo.tools import float_compare, float_round

# _logger = logging.getLogger(__name__)



# class ProductCategory(models.Model):
#     _inherit = "product.category"

#     business_id = fields.Many2one('business.unit', string='Business Unit',domain="[('business_type','=','bu')]")