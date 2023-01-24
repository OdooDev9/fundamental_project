import logging

_logger = logging.getLogger(__name__)
from odoo.exceptions import UserError, AccessError, ValidationError
from datetime import datetime
from dateutil import relativedelta
from itertools import groupby
from operator import itemgetter
from re import findall as regex_findall, split as regex_split

from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools.float_utils import float_compare, float_round, float_is_zero


class sale_order_line_request(models.Model):
    _name = 'sale.order.line.request'
    _description = 'sale order line request'

    # sale_order_line = fields.Many2one('sale.order.line',string="Order Line")
    sale_order_line_number = fields.Char(string="Order Line Number")
    quote_request_id = fields.Many2one('sale.order.request', string="quote references")
    product_id = fields.Many2one('product.product', string="Product")
    product_uom_qty = fields.Float(string="Quantity")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure',
                                  domain="[('category_id', '=', product_uom_category_id)]", ondelete="restrict")

    @api.onchange('product_id')
    def onchange_bu_product(self):
        self.product_uom = self.product_id.uom_id.id
        for rec in self.quote_request_id:
            return {'domain': {
                'product_id': [('business_id', '=', rec.hr_bu_id.id), ('unit_or_part', '=', rec.unit_or_part)]}}

        # return {'domain': {'product_id': [('business_id', '=', rec.hr_bu_id.id),('unit_or_part','=','rec.unit_or_part')]}}


class sale_order_request(models.Model):
    _name = 'sale.order.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'sale order request'
    _order = 'id desc'

    @api.model
    def _get_br(self):
        if self.env.user.user_type_id == 'br':
            return self.env.user.current_bu_br_id

    # YZO add _get_bu
    @api.model
    def _get_bu(self):
        if self.env.user.user_type_id == 'bu':
            return self.env.user.current_bu_br_id

    def set_bu_domain(self):
        domain = [('id', 'in', [bu.id for bu in self.env.user.hr_bu_ids])]
        return domain

    def set_br_domain(self):
        domain = [('id', 'in', [br.id for br in self.env.user.hr_br_ids])]
        return domain

    name = fields.Char(string='Goods Request', required=True, readonly=True, default='New', copy=False)
    state = fields.Selection([
        ('new', 'To Approve'),
        ('approved', 'Approved BOH'),
        ('confirmed', 'Done'),
        ('cancel', 'Cancel'),
    ], string='Status', readonly=True, default='new')
    quote_name = fields.Many2one('sale.order', string="Sale Order")
    request_date = fields.Datetime(string='Request Date', required=True)
    custom_order_line = fields.One2many('sale.order.line.request', 'quote_request_id', string="Order Lines")
    request_user_id = fields.Many2one('res.users', required=True, default=lambda self: self.env.user)
    hr_br_id = fields.Many2one('business.unit', string="Branch", default=_get_br, domain=set_br_domain)
    # YZO add default of hr_bu_id
    hr_bu_id = fields.Many2one('business.unit', string="Business Unit", default=_get_bu, domain=set_bu_domain)
    delivery_count = fields.Integer(string='Delivery Orders', compute='_compute_delivery_count')
    picking_ids = fields.One2many('stock.picking', 'request_ref_id', string='Transfers')
    unit_or_part = fields.Selection([('unit', 'Unit'), ('part', 'Spare Part')], string='Units or Parts', default='part')
    br_user_approve = fields.Boolean(compute='compute_br_approve')
    # YZO add br_user_approve field
    bu_user_approve = fields.Boolean(compute='compute_bu_approve')

    # YZO update compute_br_approve for user type of form create user
    def compute_br_approve(self):
        if self.request_user_id.user_type_id == 'br':
            self.br_user_approve = True
        else:
            self.br_user_approve = False

    # YZO add compute_bu_approve for user type of login user
    def compute_bu_approve(self):
        if self.env.user.user_type_id == 'bu':
            self.bu_user_approve = True
        else:
            self.bu_user_approve = False

    # @api.model
    # def create(self, vals):
    #     if vals.get('name', 'New') == 'New':
    #
    #         vals['name'] = self.env.user.current_bu_br_id.name + '-' + self.env['ir.sequence'].next_by_code(
    #             'sale.order.request') or 'New'
    #
    #     result = super(sale_order_request, self).create(vals)
    #     return result

    # YZO update Sequence code creation
    @api.model
    def create(self, vals):
        bu_br_code = self.env.user.current_bu_br_id.name
        gr_id = self.env['sale.order.request'].search([('name', 'like', bu_br_code)],
                                                      order="name desc", limit=1)
        name = bu_br_code + "-GR" + "-000001"
        digit = 0
        if gr_id:
            name = gr_id.name
            code = name.split('-')

            if digit == 0:
                digit = int(code[2])
                digit += 1
                code = '%06d' % (int(digit))
                name = bu_br_code + "-GR" + "-" + str(code)

        if vals.get('name', _('New')) == _('New'):
            vals['name'] = name
        result = super(sale_order_request, self).create(vals)
        return result

    # @api.onchange('hr_br_id')
    # def onchange_br(self):
    # 	return {'domain': {'hr_br_id': [('id', 'in', [br.id for br in self.env.user.hr_br_ids])]}}

    @api.onchange('unit_or_part')
    def _onchange_unit_part(self):
        self.custom_order_line = False

    def _compute_delivery_count(self):
        requests = []
        for order in self:
            request_ids = self.env['stock.picking'].search([('request_ref_id', '=', order.id)])
            order.delivery_count = len(request_ids)

    def button_approve(self):
        self.write({'state': 'approved'})
        picking = self._create_picking()

    # YZO add confirm function
    def button_confirm(self):
        self.write({'state': 'confirmed'})
        picking = self._create_picking()

    # else:
    # 	raise UserError(_("Only Managers can approve"))

    # YZO update _create_picking
    def _create_picking(self):
        pick_obj = self.env['stock.picking']
        br_move_lines = []
        bu_move_lines = []
        for request in self:
            transit_location_obj = self.env['stock.location'].search([('usage', '=', 'transit')])
            br_warehouse_id = self.env['stock.warehouse'].search(
                [('hr_bu_id', '=', request.hr_br_id.id), ('hr_bu_id.business_type', '=', 'br')], limit=1)
            bu_warehouse_id = self.env['stock.warehouse'].search(
                [('hr_bu_id', '=', request.hr_bu_id.id), ('hr_bu_id.business_type', '=', 'bu')], limit=1)
            if self.env.user.user_type_id == 'br':
                for line in request.custom_order_line:
                    if line.product_id.type in ['consu', 'product']:
                        br_move_lines.append((0, 0, {
                            'name': request.name,
                            'company_id': self.env.user.company_id.id,
                            'product_id': line.product_id.id,
                            'product_uom': line.product_uom.id,
                            'product_uom_qty': line.product_uom_qty,
                            'partner_id': self.env.user.partner_id.id,
                            'location_id': transit_location_obj.id,
                            'location_dest_id': br_warehouse_id.lot_stock_id.id,
                            'origin': request.name,
                            # 'request_ref_id' : request.id,
                            'warehouse_id': br_warehouse_id.id,
                            'priority': '1',

                        }))
                        bu_move_lines.append((0, 0, {
                            'name': request.name,
                            'company_id': self.env.user.company_id.id,
                            'product_id': line.product_id.id,
                            'product_uom': line.product_uom.id,
                            'product_uom_qty': line.product_uom_qty,
                            'partner_id': self.env.user.partner_id.id,
                            'location_dest_id': transit_location_obj.id,
                            'location_id': bu_warehouse_id.lot_stock_id.id,
                            'origin': request.name,
                            # 'request_ref_id' : request.id,
                            'warehouse_id': bu_warehouse_id.id,
                            'priority': '1',

                        }))

                br_picking = pick_obj.sudo().create({
                    'request_ref_id': request.id,
                    'partner_id': self.env.user.partner_id.id,
                    'scheduled_date': request.request_date,
                    'origin': request.name,
                    'move_type': 'direct',
                    'company_id': self.env.user.company_id.id,
                    'move_lines': br_move_lines,
                    'picking_type_id': br_warehouse_id.int_type_id.id,
                    'location_id': transit_location_obj.id,
                    'location_dest_id': br_warehouse_id.lot_stock_id.id,
                    'hr_br_id': request.hr_br_id.id,
                    'hr_bu_id': request.hr_bu_id.id,
                    'is_br': True,
                    'unit_or_part': request.unit_or_part,

                })
                # br_picking.action_confirm()
                bu_picking = pick_obj.sudo().create({
                    'request_ref_id': request.id,
                    'partner_id': self.env.user.partner_id.id,
                    'scheduled_date': request.request_date,
                    'origin': request.name,
                    'move_type': 'direct',
                    'company_id': self.env.user.company_id.id,
                    'move_lines': bu_move_lines,
                    'picking_type_id': bu_warehouse_id.int_type_id.id,
                    'location_dest_id': transit_location_obj.id,
                    'location_id': bu_warehouse_id.lot_stock_id.id,
                    'hr_br_id': request.hr_br_id.id,
                    'hr_bu_id': request.hr_bu_id.id,
                    'is_bu': True,
                    'unit_or_part': request.unit_or_part,

                })
                # bu_picking.action_confirm()
            elif self.env.user.user_type_id == 'bu':
                for line in request.custom_order_line:
                    if line.product_id.type in ['consu', 'product']:
                        br_move_lines.append((0, 0, {
                            'name': request.name,
                            'company_id': self.env.user.company_id.id,
                            'product_id': line.product_id.id,
                            'product_uom': line.product_uom.id,
                            'product_uom_qty': line.product_uom_qty,
                            'partner_id': self.env.user.partner_id.id,
                            'location_id': br_warehouse_id.lot_stock_id.id,
                            'location_dest_id': transit_location_obj.id,
                            'origin': request.name,
                            # 'request_ref_id' : request.id,
                            'warehouse_id': br_warehouse_id.id,
                            'priority': '1',

                        }))
                        bu_move_lines.append((0, 0, {
                            'name': request.name,
                            'company_id': self.env.user.company_id.id,
                            'product_id': line.product_id.id,
                            'product_uom': line.product_uom.id,
                            'product_uom_qty': line.product_uom_qty,
                            'partner_id': self.env.user.partner_id.id,
                            'location_dest_id': bu_warehouse_id.lot_stock_id.id,
                            'location_id': transit_location_obj.id,
                            'origin': request.name,
                            # 'request_ref_id' : request.id,
                            'warehouse_id': bu_warehouse_id.id,
                            'priority': '1',

                        }))

                bu_picking = pick_obj.sudo().create({
                    'request_ref_id': request.id,
                    'partner_id': self.env.user.partner_id.id,
                    'scheduled_date': request.request_date,
                    'origin': request.name,
                    'move_type': 'direct',
                    'company_id': self.env.user.company_id.id,
                    'move_lines': bu_move_lines,
                    'picking_type_id': bu_warehouse_id.int_type_id.id,
                    'location_id': transit_location_obj.id,
                    'location_dest_id': bu_warehouse_id.lot_stock_id.id,
                    'hr_br_id': request.hr_br_id.id,
                    'hr_bu_id': request.hr_bu_id.id,
                    'is_bu': True,
                    'unit_or_part': request.unit_or_part,

                })
                # bu_picking.action_confirm()
                br_picking = pick_obj.sudo().create({
                    'request_ref_id': request.id,
                    'partner_id': self.env.user.partner_id.id,
                    'scheduled_date': request.request_date,
                    'origin': request.name,
                    'move_type': 'direct',
                    'company_id': self.env.user.company_id.id,
                    'move_lines': br_move_lines,
                    'picking_type_id': br_warehouse_id.int_type_id.id,
                    'location_dest_id': transit_location_obj.id,
                    'location_id': br_warehouse_id.lot_stock_id.id,
                    'hr_br_id': request.hr_br_id.id,
                    'hr_bu_id': request.hr_bu_id.id,
                    'is_br': True,
                    'unit_or_part': request.unit_or_part,

                })
                # br_picking.action_confirm()
        return True
