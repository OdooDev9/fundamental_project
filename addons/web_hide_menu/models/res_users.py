# Copyright (C) 2021 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    hide_menu_ids = fields.One2many("hide.menu", "user_id", string="Hide Menu")

    def hide_report_menu(self):
        print("HELLO========++>")
        for user in self:
            f_reports_menu = self.env['ir.ui.menu'].search([('parent_id', '=', self.env.ref('account.account_reports_legal_statements_menu').id)])
            user_reports = self.env['account.financial.html.report'].search([('bu_br_id', '=', user.current_bu_br_id.id)])
            context = []
            for rep in user_reports:
                context.append("{'model': 'account.financial.html.report', 'id': %s}" % rep.id)
            
            print("==========>context", context)
        return True