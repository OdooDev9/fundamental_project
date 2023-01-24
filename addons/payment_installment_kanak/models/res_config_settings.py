# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_enable_installments = fields.Boolean("Installment On Sales", implied_group='payment_installment_kanak.group_enable_installments')
