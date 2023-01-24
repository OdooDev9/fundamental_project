from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import format_datetime
from odoo.tools.misc import formatLang, get_lang


class Pricelist(models.Model):
    _inherit = "product.pricelist"

    @api.model
    def _get_bu(self):
        if self.env.user.user_type_id == 'bu':
            return self.env.user.current_bu_br_id

    @api.model
    def _get_br(self):
        if self.env.user.user_type_id == 'br':
            return self.env.user.current_bu_br_id

    def set_br_domain(self):
        domain = [('id', 'in', [br.id for br in self.env.user.hr_br_ids])]
        return domain

    def set_bu_domain(self):
        domain = [('id', 'in', [g.id for g in self.env.user.hr_bu_ids])]
        return domain

    hr_br_ids = fields.Many2many('business.unit', string='Branch', default=_get_br, domain=set_br_domain)
    hr_bu_id = fields.Many2one('business.unit', string='Business Unit', default=_get_bu, domain=set_bu_domain)
    unit_or_part = fields.Selection([('unit', 'Unit'), ('part', 'Spare Part')], string='Unit Or Part')
    state = fields.Selection([('draft', 'Draft'), ('approved_finance_pic', 'Approved F & A PIC'),
                              ('approved_finance_head', 'Approved F & A Head')], default="draft")

    @api.onchange('unit_or_part')
    def _onchange_unit_part(self):
        self.item_ids = False

    def action_finance_approve(self):
        for rec in self:
            rec.state = 'approved_finance_pic'
            for line in rec.item_ids:
                line.write({'state': 'approved_finance_pic'})

    def action_reset(self):
        for rec in self:
            rec.sudo().write({'state': 'draft'})
            for line in rec.item_ids:
                line.write({'state': 'draft'})

    def action_finance_head_approve(self):
        for rec in self:
            rec.sudo().write({'state': 'approved_finance_head'})
            for line in rec.item_ids:
                line.write({'state': 'approved_finance_head'})


class PricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    state = fields.Selection([('draft', 'Draft'), ('approved_finance_pic', 'Approved F & A PIC'),
                              ('approved_finance_head', 'Approved F & A Head')], default="draft")

    @api.onchange('product_tmpl_id')
    def _onchange_product_tmpl_id(self):
        has_tmpl_id = self.filtered('product_tmpl_id')
        for item in has_tmpl_id:
            if item.product_id and item.product_id.product_tmpl_id != item.product_tmpl_id:
                item.product_id = None
        return {'domain': {'product_tmpl_id': [('business_id', '=', self.env.user.hr_bu_ids.ids),
                                               ('unit_or_part', '=', self.pricelist_id.unit_or_part)]}}
