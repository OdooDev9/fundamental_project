# -*- coding: utf-8 -*-
from lxml import etree

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError




class AccountPayment(models.Model):
    _inherit = "account.payment"

    def action_approve_finance_pic(self):
        self.write({'state':'approved_finance_pic'})
    
    def action_approve_finance_head(self):
        self.write({'state':'approved_finance_head'})



    