# Copyright (C) 2021 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        if self.env.user == self.env.ref("base.user_root"):
            return super(IrUiMenu, self).search(
                args, offset=offset, limit=limit, order=order, count=False
            )
        else:
            menu_ids = super(IrUiMenu, self).search(
                args, offset=offset, limit=limit, order=order, count=False
            )
            if menu_ids:
                
                # Hidding Not Owned Financial Report Menu Items
                context = []
                user_reports = self.env['account.financial.html.report'].search([('bu_br_id', '=', self.env.user.current_bu_br_id.id)])
                for rep in user_reports:
                    context.append("{'model': 'account.financial.html.report', 'id': %s}" % rep.id)
                actions = self.env['ir.actions.client'].sudo().search([('context', 'like', "{'model': 'account.financial.html.report',"), ('context','not in', context)])
                f_reports_menu = menu_ids.filtered(lambda m: m.parent_id and m.parent_id.id == self.env.ref('account.account_reports_legal_statements_menu').id and m.action.id in actions.ids)
                
                
                hide_menu_ids = self.env.user.hide_menu_ids.mapped("menu_id").ids + f_reports_menu.ids
                menu_ids = set(menu_ids.ids).difference(set(hide_menu_ids))
                
                return self.browse(menu_ids)
            return menu_ids
