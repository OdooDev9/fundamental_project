from odoo import api, fields, models, _, SUPERUSER_ID

class ProductCategory(models.Model):
    _inherit = "product.category"


    def _set_bu_domain(self):
        user_type_id = self.env.user.user_type_id
        ids = []
        if user_type_id == 'cfd':
            return ids
        if user_type_id == 'br':
            ids = self.env.user.current_bu_br_id.ids + self.env.user.hr_br_ids.ids
        elif user_type_id == 'bu':
            ids = self.env.user.current_bu_br_id.ids + self.env.user.hr_bu_ids.ids
        domain = [('id', 'in', ids)]
        return domain


    


    business_id = fields.Many2one('business.unit', string="Business Unit", default = lambda self:self.env.user.current_bu_br_id,domain=_set_bu_domain)
    unit_or_part = fields.Selection([('unit', 'Unit'), ('part', 'Spare Part')], string='Unit Or Part')