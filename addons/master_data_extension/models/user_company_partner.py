from odoo import models, fields, api, _
import json


class ResUsers(models.Model):
    _inherit = 'res.users'

    current_bu_br_id = fields.Many2one('business.unit', string='Current Business Unit/Branch')
    # hr_bu_id = fields.Many2one('business.unit',string='Current Business Unit',domain="[('business_type','=','bu')]")
    hr_bu_ids = fields.Many2many('business.unit', 'user_business_ref', 'bu_id', 'user_id',
                                 string='Allowed Business Unit', domain="[('business_type','=','bu')]")
    hr_br_ids = fields.Many2many('business.unit', 'user_branch_ref', 'br_id', 'user_id', string='Allowed Branches',
                                 domain="[('business_type','=','br')]")
    # edit_hr_bu_ids = fields.Many2many('business.unit', 'user_edit_business_ref', 'bu_id', 'user_id',
    #                              string='Edited Business Unit', domain="[('business_type','=','bu')]")
    # edit_hr_br_ids = fields.Many2many('business.unit', 'user_edit_branch_ref', 'br_id', 'user_id', string='Edited Branches',
    #                              domain="[('business_type','=','br')]")
    user_type_id = fields.Selection([('br', 'Branch'), ('bu', 'Business Unit'), ('div', 'DIV'), ('cfd', 'CFD')],
                                    string='User Type')

    current_bu_br_id_domain = fields.Char(compute="_compute_current_bu_br_id_domain", readonly=True, store=False)

    
    
        

    
    @api.depends('user_type_id')
    def _compute_current_bu_br_id_domain(self):
        for rec in self:
            rec.current_bu_br_id_domain = rec.user_type_id
            


    @api.onchange('user_type_id')
    def onchange_user_type(self):
        for rec in self:
            rec.current_bu_br_id = False
            rec.hr_bu_ids = False
            rec.hr_br_ids = False
            if rec.user_type_id == 'cfd':
                rec.current_bu_br_id = self.env['business.unit'].search([('business_type','=','cfd')]).id
                rec.hr_bu_ids = self.env['business.unit'].search([('business_type','=','bu')]).ids
                rec.hr_br_ids = self.env['business.unit'].search([('business_type','=','br')]).ids

    @api.onchange('current_bu_br_id')
    def onchange_current_bu_br(self):
        if self.current_bu_br_id:
            self.hr_bu_ids = self.current_bu_br_id.ids if self.user_type_id == 'bu' else False
            self.hr_br_ids = self.current_bu_br_id.ids if self.user_type_id == 'br' else False

                    

    # @api.model_create_multi
    # def create(self, vals_list):
    #     users = super(ResUsers, self).create(vals_list)
    #     for user in users:
    #         if user.user_type_id == 'br':
    #             user.write({'groups_id': [(4, self.env.ref('master_data_extension.group_br_user').id)]})
    #         elif user.user_type_id == 'bu':
    #             user.write({'groups_id': [(4, self.env.ref('master_data_extension.group_bu_user').id)]})
    #         elif user.user_type_id == 'cfd':
    #             user.write({'groups_id': [(4, self.env.ref('master_data_extension.group_cfd_user').id)]})

    #     return users
    
    # def write(self, values):
    #     if values.get('user_type_id', None):
    #         if values.get('user_type_id') == 'br':
    #             self.write({'groups_id': [(4, self.env.ref('master_data_extension.group_br_user').id)]})
    #             self.write({'groups_id': [(3, self.env.ref('master_data_extension.group_bu_user').id),(3, self.env.ref('master_data_extension.group_cfd_user').id)]})

    #         elif values.get('user_type_id') == 'bu':
    #             self.write({'groups_id': [(4, self.env.ref('master_data_extension.group_bu_user').id)]})
    #             self.write({'groups_id': [(3, self.env.ref('master_data_extension.group_br_user').id),
    #                                       (3, self.env.ref('master_data_extension.group_cfd_user').id)]})
    #         elif values.get('user_type_id') == 'cfd':
    #             self.write({'groups_id': [(4, self.env.ref('master_data_extension.group_cfd_user').id)]})
    #             self.write({'groups_id': [(3, self.env.ref('master_data_extension.group_bu_user').id),
    #                                       (3, self.env.ref('master_data_extension.group_br_user').id)]})


    #     if 'hr_bu_ids' in values:
    #         self.env['ir.rule'].clear_caches()
    #     if 'hr_br_ids' in values:
    #         self.env['ir.rule'].clear_caches()
    #     return super(ResUsers, self).write(values)



class ResCompany(models.Model):
    _inherit = 'res.company'
    bu_id = fields.Many2one('business.unit', string='Business Unit')
