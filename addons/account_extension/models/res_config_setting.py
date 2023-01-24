from odoo import api, fields, models, _

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    _description = 'Config Settings'

    property_account_receivable_id = fields.Many2one('account.account', 'Account Receivable', domain="[('internal_type', '=', 'receivable')]")
    property_account_payable_id = fields.Many2one('account.account', 'Account Payable', domain="[('internal_type', '=', 'payable')]")
    aff_account_receivable_id = fields.Many2one('account.account', 'Aff: Receivable')
    aff_account_payable_id = fields.Many2one('account.account', 'Aff: Payable')

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        res.update(
            property_account_receivable_id = int(get_param('account_extension.property_account_receivable_id')),
            property_account_payable_id = int(get_param('account_extension.property_account_payable_id')),
            aff_account_receivable_id = int(get_param('account_extension.aff_account_receivable_id')),
            aff_account_payable_id = int(get_param('account_extension.aff_account_payable_id'))
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        set_param = self.env['ir.config_parameter'].sudo().set_param
        set_param('account_extension.property_account_receivable_id', self.property_account_receivable_id.id)
        set_param('account_extension.property_account_payable_id', self.property_account_payable_id.id)
        set_param('account_extension.aff_account_receivable_id', self.aff_account_receivable_id.id)
        set_param('account_extension.aff_account_payable_id', self.aff_account_payable_id.id)
