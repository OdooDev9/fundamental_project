from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import get_lang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare, float_round


class SaleOrder(models.Model):
    _inherit = "sale.order"

    req_quot_id = fields.Many2one('request.quotation', string='Request Quotation')


