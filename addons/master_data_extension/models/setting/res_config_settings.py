# -*- coding: utf-8 -*-

from attr import field
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    is_inv_auto = fields.Boolean(string='Auto INV Generate')
    account_config = fields.Boolean(string='Account Config')
    is_acc_auto = fields.Boolean(string='Auto ACC Generate')

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        res.update(
            is_inv_auto = get_param('master_data_extension.is_inv_auto'),
            is_acc_auto = get_param('master_data_extension.is_acc_auto'),
            account_config = get_param('master_data_extension.account_config'),
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        set_param = self.env['ir.config_parameter'].sudo().set_param
        set_param('master_data_extension.is_inv_auto', self.is_inv_auto)
        set_param('master_data_extension.is_acc_auto', self.is_acc_auto)
        set_param('master_data_extension.account_config', self.account_config)
        



