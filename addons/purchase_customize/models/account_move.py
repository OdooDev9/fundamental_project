from odoo import _, api, fields, models
from odoo.exceptions import ValidationError



class AccountMove(models.Model):
    _inherit = "account.move"

    is_oversea_purchase = fields.Boolean(string="Is Oversea Purchase")
    broker_bill = fields.Boolean(string='Broker Bill',default=False)
