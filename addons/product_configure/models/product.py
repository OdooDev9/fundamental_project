from odoo import api, fields, models, _, SUPERUSER_ID

class ProductTemplateInherited(models.Model):
    _inherit = 'product.template'
    _description = 'Define Business Unit In Product'

    # business_id = fields.Many2one('business.unit', string='Business Unit',default=lambda self: self.env.user.current_bu_br_id)
    # unit_or_part = fields.Selection([('unit', 'Unit'), ('part', 'Spare Part')], string='Unit Or Part')
    stock = fields.Selection([
        ('healthy', 'Healthy Stock'),
        ('dead', 'Dead Stock'),
        ('over', 'Over Stock'),
    ], string="Stock Status")

    @api.onchange('categ_id')
    def onchange_product_categ_id(self):
        self.unit_or_part = self.categ_id.unit_or_part
    

    @api.model
    def _get_bu(self):
        if self.env.user.user_type_id =='bu':
            return self.env.user.current_bu_br_id
    
    @api.model
    def _get_br(self):
        if self.env.user.user_type_id =='br':
            return self.env.user.current_bu_br_id

    def _set_bu_domain(self):
        domain = [('id', 'in', [bu.id for bu in self.env.user.hr_bu_ids])]
        return domain
    def _set_br_domain(self):
        domain = [('id', 'in', [br.id for br in self.env.user.hr_br_ids])]
        return domain



    branch_id = fields.Many2one('business.unit', string='Branches',default=_get_br,domain=_set_br_domain)
    business_id = fields.Many2one('business.unit', string='Business Unit',default=_get_bu,domain=_set_bu_domain)
    unit_or_part = fields.Selection([('unit', 'Unit'), ('part', 'Spare Part')], string='Unit Or Part')

    @api.onchange('detailed_type')
    def _onchange_detailed_type(self):
        self.unit_or_part = False
            