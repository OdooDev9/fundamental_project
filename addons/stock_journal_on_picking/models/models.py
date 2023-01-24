# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare

import logging


class StockPicking(models.Model):
    _inherit = 'stock.picking'

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
        domain = [('id', 'in', [bu.id for bu in self.env.user.hr_bu_ids])]
        return domain

    # @api.model
    # def set_location_domain(self):
    #     if self.env.user.user_type_id =='bu':
    #         domain = [('hr_bu_id', '=', self.env.user.current_bu_br_id.id),('usage','=','internal')]
    #     if self.env.user.user_type_id =='br':
    #         domain = [('hr_bu_id', '=', self.env.user.current_bu_br_id.id),('usage','=','internal')]

    #     return domain

    hr_br_id = fields.Many2one('business.unit', string='Branch', default=_get_br, domain=set_br_domain)
    hr_bu_id = fields.Many2one('business.unit', string='Business Unit', default=_get_bu, domain=set_bu_domain)
    unit_or_part = fields.Selection([('unit', 'Unit'), ('part', 'Spare Part')], string='Unit Or Part', default='part')
    # location_id = fields.Many2one('stock.location', "Source Location", domain=default_location_domain,check_company=True, readonly=False, required=True,states={'done': [('readonly', True)]})
    is_bu = fields.Boolean(string='Is BU')
    is_br = fields.Boolean(string='Is BR')
    is_validate = fields.Boolean(string='Is Validate', compute='compute_validate')

    location_id = fields.Many2one('stock.location', "Source Location",
                                  check_company=True, readonly=False, required=True,
                                  states={'done': [('readonly', True)]})
    # location_dest_id = fields.Many2one(
    #     'stock.location', "Destination Location",
    #     default=lambda self: self.env['stock.picking.type'].browse(self._context.get('default_picking_type_id')).default_location_dest_id,
    #     check_company=True, readonly=True, required=True,
    #     states={'draft': [('readonly', False)]})
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting Another Operation'),
        ('confirmed', 'Waiting'),
        ('assigned', 'Ready'),
        ('approve_inv_head', 'Approved Inventory Head'),
        ('approve_finance_head', 'Approved F & A Head'),
        ('approve_gm_agm', 'Approved GM/AGM'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', compute='_compute_state',
        copy=False, index=True, readonly=True, store=True, tracking=True,
        help=" * Draft: The transfer is not confirmed yet. Reservation doesn't apply.\n"
             " * Waiting another operation: This transfer is waiting for another operation before being ready.\n"
             " * Waiting: The transfer is waiting for the availability of some products.\n(a) The shipping policy is \"As soon as possible\": no product could be reserved.\n(b) The shipping policy is \"When all products are ready\": not all the products could be reserved.\n"
             " * Ready: The transfer is ready to be processed.\n(a) The shipping policy is \"As soon as possible\": at least one product has been reserved.\n(b) The shipping policy is \"When all products are ready\": all product have been reserved.\n"
             " * Done: The transfer has been processed.\n"
             " * Cancelled: The transfer has been cancelled.")
    is_return = fields.Boolean(compute='compute_return_picking')
    bu_br_user_approve = fields.Boolean(compute='compute_bu_br_user_approve')



    # def write(self, vals):
    #     context = self._context
    #     print("context =====>", context)
     
    #     if self.env.context.get('model') == 'stock.picking' and self.env.context.get('view_type') == form:
    #         # print('...................')
    #         if self.picking_type_id.hr_bu_id.id != self.env.user.current_bu_br_id.id:
    #             # print('////////////////')
    #             raise UserError(_("You don't have acccess to edit permission"))
    #     else:
    #         return super(StockPicking, self).write(vals)

    @api.depends('picking_type_id', 'hr_bu_id', 'hr_br_id')
    def compute_bu_br_user_approve(self):
        for rec in self:
            if rec.hr_br_id.id == self.env.user.current_bu_br_id.id and self.env.user.user_type_id == 'br' and rec.picking_type_id.hr_bu_id.id == self.env.user.current_bu_br_id.id:
                rec.bu_br_user_approve = True
            elif rec.hr_bu_id.id == self.env.user.current_bu_br_id.id and self.env.user.user_type_id == 'bu' and rec.picking_type_id.hr_bu_id.id == self.env.user.current_bu_br_id.id:
                rec.bu_br_user_approve = True
            else:
                rec.bu_br_user_approve = False

    @api.depends('state')
    def _compute_show_validate(self):
        for picking in self:
            if not (picking.immediate_transfer) and picking.state == 'draft':
                picking.show_validate = False
            elif picking.state not in (
                    'draft', 'waiting', 'confirmed', 'assigned', 'approve_inv_head', 'approve_finance_head',
                    'approve_gm_agm'):
                picking.show_validate = False
            else:
                picking.show_validate = True

    def compute_return_picking(self):
        for rec in self:
            if rec.picking_type_id.name == 'Returns':
                rec.is_return = True
            else:
                rec.is_return = False

    def check_pickings_without_lotse(self):
        # Clean-up the context key at validation to avoid forcing the creation of immediate
        # transfers.
        ctx = dict(self.env.context)
        ctx.pop('default_immediate_transfer', None)
        self = self.with_context(ctx)

        # Sanity checks.
        pickings_without_moves = self.browse()
        pickings_without_quantities = self.browse()
        pickings_without_lots = self.browse()
        products_without_lots = self.env['product.product']
        for picking in self:
            if not picking.move_lines and not picking.move_line_ids:
                pickings_without_moves |= picking

            picking.message_subscribe([self.env.user.partner_id.id])
            picking_type = picking.picking_type_id
            precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            no_quantities_done = all(
                float_is_zero(move_line.qty_done, precision_digits=precision_digits) for move_line in
                picking.move_line_ids.filtered(lambda m: m.state not in ('done', 'cancel')))
            no_reserved_quantities = all(
                float_is_zero(move_line.product_qty, precision_rounding=move_line.product_uom_id.rounding) for move_line
                in picking.move_line_ids)
            if no_reserved_quantities and no_quantities_done:
                pickings_without_quantities |= picking

            if picking_type.use_create_lots or picking_type.use_existing_lots:
                lines_to_check = picking.move_line_ids
                if not no_quantities_done:
                    lines_to_check = lines_to_check.filtered(
                        lambda line: float_compare(line.qty_done, 0, precision_rounding=line.product_uom_id.rounding))
                for line in lines_to_check:
                    product = line.product_id
                    if product and product.tracking != 'none':
                        if not line.lot_name and not line.lot_id:
                            pickings_without_lots |= picking
                            products_without_lots |= product

        if pickings_without_lots:
            raise UserError(_('You need to supply a Lot/Serial number for products %s.') % ', '.join(
                products_without_lots.mapped('display_name')))

    def action_approve_inv_head(self):
        self.check_pickings_without_lotse()
        self.write({'state': 'approve_inv_head'})

    def action_approve_finance_head(self):
        self.write({'state': 'approve_finance_head'})

    def action_approve_gm_agm(self):
        self.write({'state': 'approve_gm_agm'})

    @api.onchange('hr_br_id')
    def onchange_hr_br_id(self):
        if self.env.user.user_type_id == 'br' and self.env.user.current_bu_br_id:
            if self.hr_br_id:
                return {'domain': {'location_id': [('hr_bu_id', '=', self.hr_br_id.id), ('usage', '=', 'internal')]}}

    @api.onchange('hr_bu_id')
    def onchange_hr_bu_id(self):
        if self.env.user.user_type_id == 'bu' and self.env.user.current_bu_br_id:
            if self.hr_bu_id:
                return {'domain': {'location_id': [('hr_bu_id', '=', self.hr_bu_id.id), ('usage', '=', 'internal')]}}

    # @api.ondelete(at_uninstall=False)
    def unlink(self):
        for rec in self:
            if rec.state not in ('draft', 'cancel'):
                raise UserError(_('You can not delete this transfer. You must first cancel it.'))

    @api.onchange('unit_or_part', 'hr_bu_id')
    def onchange_bu_unit_or_part(self):
        self.move_ids_without_package = False

    def button_new_validate(self):

        for rec in self:
            for line in rec.move_line_ids_without_package:

                if line.lot_id:
                    serial_no_list = []
                    serial_no_list.append(line.lot_id.name)
                    if serial_no_list:
                        view = self.env.ref('stock_journal_on_picking.view_lot_serial_transfer_wizard')
                        res = {
                            'name': _('Credit Alert'),
                            'type': 'ir.actions.act_window',
                            'view_mode': 'form',
                            'res_model': 'lot.serial.transfer.wizard',
                            'views': [(view.id, 'form')],
                            'view_id': view.id,
                            'target': 'new',
                            'context': dict(self.env.context, default_picking_id=self.id,
                                            default_message='Please! firstly, Check Product  Serial Number'),
                        }
                else:
                    res = self.button_validate()

                return res

    def action_get_account_moves(self):
        self.ensure_one()
        action_data = self.env['ir.actions.act_window']._for_xml_id('account.action_move_journal_line')
        action_data['domain'] = [('id', 'in', self.move_lines.account_move_ids.ids)]
        return action_data

    @api.onchange('location_id', 'location_dest_id')
    def _onchange_locations(self):
        (self.move_lines | self.move_ids_without_package).update({
            "location_id": self.location_id,
            "location_dest_id": self.location_dest_id
        })
        for rec in self.move_line_ids_without_package:
            rec.location_id = self.location_id.id

    def compute_validate(self):
        for rec in self:
            if rec.hr_br_id.id == self.env.user.current_bu_br_id.id and rec.is_br == True:
                rec.is_validate = True


            elif rec.hr_bu_id.id == self.env.user.current_bu_br_id.id and rec.is_bu == True:
                rec.is_validate = True

            elif rec.hr_bu_id.id == self.env.user.current_bu_br_id.id and rec.is_bu == False and rec.is_br == False:
                rec.is_validate = True

            elif rec.hr_br_id.id == self.env.user.current_bu_br_id.id and rec.is_bu == False and rec.is_br == False:
                rec.is_validate = True
            else:
                rec.is_validate = False


class stock_move(models.Model):
    _inherit = 'stock.move'

    standard_price = fields.Float(related='product_id.standard_price', string='Cost', company_dependent=True,
                                  digits='Product Price')
    hr_br_id = fields.Many2one('business.unit', string='Branch', related='picking_id.hr_br_id')
    hr_bu_id = fields.Many2one('business.unit', string='Business Unit', related='picking_id.hr_bu_id')

    @api.onchange('product_id')
    def onchange_bu_product(self):
        for rec in self.picking_id:
            return {'domain': {
                'product_id': [('business_id', '=', rec.hr_bu_id.id), ('unit_or_part', '=', rec.unit_or_part)]}}
