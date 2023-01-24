from odoo import api, fields, models, _

class HrBuInherited(models.Model):
    _inherit = 'hr.bu'
    _description = 'Accounting BU'

    property_account_receivable_id = fields.Many2one('account.account', 'Account Receivable', domain="[('internal_type', '=', 'receivable')]")
    property_account_payable_id = fields.Many2one('account.account', 'Account Payable', domain="[('internal_type', '=', 'payable')]")
    aff_account_receivable_id = fields.Many2one('account.account', 'Aff: Receivable')
    aff_account_payable_id = fields.Many2one('account.account', 'Aff: Payable')
    cash_in_transit_id =  fields.Many2one('account.account', 'Cash In Transit')
    cash_on_hand_id =  fields.Many2one('account.account', 'Cash On Hand')

class HrBrInherited(models.Model):
    _inherit = 'hr.branch'
    _description = 'Accounting Branch'

    property_account_receivable_id = fields.Many2one('account.account', 'Account Receivable', domain="[('internal_type', '=', 'receivable')]")
    property_account_payable_id = fields.Many2one('account.account', 'Account Payable', domain="[('internal_type', '=', 'payable')]")
    aff_account_receivable_id = fields.Many2one('account.account', 'Aff: Receivable')
    aff_account_payable_id = fields.Many2one('account.account', 'Aff: Payable')
    cash_in_transit_id =  fields.Many2one('account.account', 'Cash In Transit')
    cash_on_hand_id =  fields.Many2one('account.account', 'Cash On Hand')

# class AccountAccount(models.Model):
#     _inherit = 'account.journal'
#     _description = 'Account Journal'

#     transit_account_id = fields.Many2one('account.account', string='Transit Account')