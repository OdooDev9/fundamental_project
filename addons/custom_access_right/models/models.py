# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import models
from odoo.http import request
class ResUsers(models.Model):
    _inherit = 'res.users'

    def context_get(self):
        context = super(ResUsers, self).context_get()
        
        new_context = context.copy()
        user = self.env.user
        # c_b_id is intended as Current Bu/Br ID
        c_b_id = user.current_bu_br_id.id
        # hr_bu_ids intended to Allowed Business Units
        hr_bu_ids = user.hr_bu_ids.ids
        # hr_br_ids intended to Allowed Business Branches
        hr_br_ids = user.hr_br_ids.ids

        business_unit = self.env['business.unit'].search([])
        # IS CFD/HQ?
        c_b_ids = business_unit.ids if user.user_type_id == 'cfd' else user.current_bu_br_id.ids

        is_hq = 1 if user.user_type_id == 'cfd' else 0
        new_context.update({'c_b_ids': c_b_ids, 'c_b_id': c_b_id, 'hr_bu_ids':hr_bu_ids, 'hr_br_ids':hr_br_ids, 'all_bu_ids':hr_bu_ids+hr_br_ids})
        return new_context


    # Need to clear caches after changing some access groups 
    # It'll effective immediately after saving user record
    def write(self, values):
        result = super(ResUsers, self).write(values)
        self.env['ir.rule'].clear_caches()
        return result    














