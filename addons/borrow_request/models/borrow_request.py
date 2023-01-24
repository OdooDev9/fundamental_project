from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.exceptions import UserError, AccessError, ValidationError
from datetime import datetime
from dateutil import relativedelta


class BorrowRequest(models.Model):
    _name = 'borrow.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Borrow Request'
    _order = 'id desc'

    def default_bu(self):
        if self.env.user.user_type_id == 'bu':
            return self.env.user.current_bu_br_id

    def default_br(self):
        if self.env.user.user_type_id == 'br':
            return self.env.user.current_bu_br_id

    def set_bu_domain(self):
        domain = [('id', 'in', [bu.id for bu in self.env.user.hr_bu_ids])]
        return domain

    def set_br_domain(self):
        domain = [('id', 'in', [br.id for br in self.env.user.hr_br_ids])]
        return domain

    name = fields.Char(string='Borrow Request', required=True, readonly=True, default='New', copy=False)
    state = fields.Selection([
        ('new', 'To Approve'),
        ('approved', 'Approved'),
        ('quotation', 'Quotation'),
        ('return', 'Returned'),
        ('cancel', 'Cancel'),
    ], string='Status', readonly=True, default='new')
    quote_name = fields.Many2one('sale.order', string="Sale Order")
    request_date = fields.Datetime(string='Request Date', required=True)
    user_id = fields.Many2one('res.users', 'Approval Person', required=True)
    custom_order_line = fields.One2many('borrow.request.line', 'borrow_request_id', string="Order Lines")
    delivery_count = fields.Integer(string='Delivery Orders', compute='_compute_delivery_count')
    orderable = fields.Boolean(string='Condition To Create Sale Orders', compute='_check_orderable', store=False)
    picking_ids = fields.One2many('stock.picking', 'borrow_request_ref_id', string='Transfers')
    hr_bu_id = fields.Many2one('business.unit', string='Business Unit', default=default_bu, domain=set_bu_domain)
    hr_br_id = fields.Many2one('business.unit', string='Branch', default=default_br, domain=set_br_domain)
    from_location_id =fields.Many2one('stock.location', 'From',required=True)
    to_location_id = fields.Many2one('stock.location', 'To')
    sale_order_count = fields.Integer(string="Borrow request Count", compute='_compute_sale_order_ids')
    sale_order_ids = fields.One2many('sale.order', 'borrow_request_id', string='Transfer')
    company_id = fields.Many2one(
        'res.company', 'Company', index=True,
        default=lambda self: self.env.company)
    note = fields.Html(string="Note")
    user_type_id = fields.Selection(related='create_uid.user_type_id')
    from_date = fields.Datetime(default=fields.Datetime.now)
    to_date = fields.Datetime()
    unit_or_part = fields.Selection([('unit', 'Unit'), ('part', 'Spare Part')], string='Units or Parts', default='part')

    return_reason = fields.Text(string="Reason")
    
    @api.onchange('hr_bu_id', 'unit_or_part')
    def _onchange_bu_unit_or_part(self):
        self.custom_order_line = False
        # if self.env.user.user_type_id == 'bu':
        #     return {'domain': {
        #         'from_location_id': [('hr_bu_id', '=', self.hr_bu_id.id),('is_borrow','=',False),('usage','=','internal')]}}
        # elif self.env.user.user_type_id == 'br':
        #     return {'domain': {
        #         'from_location_id': [('hr_bu_id', '=', self.hr_br_id.id),('is_borrow','=',False),('usage','=','internal')]}}

    @api.onchange('from_location_id')
    def _onchange_from_location(self):
        if self.env.user.user_type_id == 'bu':
            return {'domain': {
                'from_location_id': [('hr_bu_id', '=', self.hr_bu_id.id),('is_borrow','=',False),('usage','=','internal')]}}
        elif self.env.user.user_type_id == 'br':
            print('.....................')
            return {'domain': {
                'from_location_id': [('hr_bu_id', '=', self.hr_br_id.id),('is_borrow','=',False),('usage','=','internal')]}}


    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('borrow.request') or 'New'
        # if vals.get('hr_bu_id'):
        if self.env.user.user_type_id == 'bu' and vals.get('hr_bu_id'):
            vals['to_location_id'] = self.env['stock.location'].search(
                [('hr_bu_id', '=', vals.get('hr_bu_id')), ('is_borrow', '=', True)], limit=1).id
        if self.env.user.user_type_id == 'br' and vals.get('hr_bu_id'):
            vals['to_location_id'] = self.env['stock.location'].search(
                [('hr_bu_id', '=', vals.get('hr_br_id')), ('is_borrow', '=', True)], limit=1).id
        result = super(BorrowRequest, self).create(vals)
        self.activity_update()

        return result

    @api.model
    def wrtite(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('borrow.request') or 'New'
        if vals.get('hr_bu_id'):
            vals['to_location_id'] = self.env['stock.location'].search(
                [('hr_bu_id', '=', vals.get('hr_bu_id')), ('is_borrow', '=', True)], limit=1).id
        result = super(BorrowRequest, self).wrtite(vals)
        self.activity_update()

        return result

    def button_approve(self):
        if self.user_id.id == self.env.user.id:
            self.write({'state': 'approved'})
            self.activity_update()
            self.ret_activity_update()

            picking = self._create_picking()
        else:
            raise UserError(_("Only Managers can approve"))

    def refuse_goods(self, reason):
        self.write({'state': 'cancel'})
        self.activity_update()
        self.message_post_with_view('borrow_request.borrow_template_refuse_reason',
                                    values={'reason': reason, 'name': self.name})

    def _get_responsible_for_approval(self):
        return self.user_id

    def _get_responsible_for_return(self):
        return self.create_uid

    def activity_update(self):

        for request in self.filtered(lambda hol: hol.state == 'new'):
            self.activity_schedule(
                'borrow_request.mail_act_borrow_approval',
                user_id=request.sudo()._get_responsible_for_approval().id)
        self.filtered(lambda hol: hol.state == 'approved').activity_feedback(
            ['borrow_request.mail_act_borrow_approval'])
        self.filtered(lambda hol: hol.state == 'cancel').activity_unlink(['borrow_request.mail_act_borrow_approval'])

    def ret_activity_update(self):
        for request in self.filtered(lambda hol: hol.state == 'approved'):
            self.activity_schedule(
                'borrow_request.mail_act_borrow_return_approval',
                user_id=request.sudo()._get_responsible_for_return().id)
        self.filtered(lambda hol: hol.state == 'return').activity_feedback(
            ['borrow_request.mail_act_borrow_return_approval'])
        self.filtered(lambda hol: hol.state == 'cancel').activity_unlink(
            ['borrow_request.mail_act_borrow_return_approval'])

    def _create_picking(self):
        picking_obj = self.env['stock.picking']

        for request in self:

            if self.env.user.user_type_id == 'bu':
                bu_picking_type_id = self.env['stock.picking.type'].search(
                    [('code', '=', 'internal'), ('hr_bu_id', '=', request.hr_bu_id.id)], limit=1)
                bu_move_lines = []
                for line in request.custom_order_line:
                    if line.product_id.type in ['consu', 'product']:
                        bu_move_lines.append((0, 0, {
                            'name': request.name,
                            'company_id': self.env.user.company_id.id,
                            'product_id': line.product_id.id,
                            'product_uom': line.product_id.uom_id.id,
                            'product_uom': line.product_id.uom_id.id,
                            'product_uom_qty': line.product_uom_qty,
                            'partner_id': self.env.user.partner_id.id,
                            'location_id':request.from_location_id.id,
                            # 'location_id': bu_picking_type_id.default_location_src_id.id or bu_picking_type_id.default_location_src_id.id,
                            'location_dest_id': request.to_location_id.id,
                            'origin': request.name,
                            'borrow_request_ref_id': request.id,
                            'warehouse_id': request.to_location_id.warehouse_id.id,
                            'priority': '1',
                        }))

                bu_picking = picking_obj.create({
                    'partner_id': self.env.user.partner_id.id,
                    'scheduled_date': datetime.today(),
                    'origin': request.name,
                    'move_type': 'direct',
                    'company_id': self.env.user.company_id.id,
                    'move_lines': bu_move_lines,
                    'picking_type_id': bu_picking_type_id.id,
                    'location_id':request.from_location_id.id,
                    # 'location_id': bu_picking_type_id.default_location_src_id.id,
                    'location_dest_id': request.to_location_id.id,
                    'borrow_request_ref_id': request.id,
                    'hr_bu_id': request.hr_bu_id.id or False,
                    'unit_or_part': request.unit_or_part,
                })
                print('bu picking',bu_picking)
            # return bu_picking
            if self.env.user.user_type_id == 'br':
                br_picking_type_id = self.env['stock.picking.type'].search(
                    [('code', '=', 'internal'), ('hr_bu_id', '=', request.hr_br_id.id)], limit=1)
                br_move_lines = []
                for line in request.custom_order_line:
                    if line.product_id.type in ['consu', 'product']:
                        br_move_lines.append((0, 0, {
                            'name': request.name,
                            'company_id': self.env.user.company_id.id,
                            'product_id': line.product_id.id,
                            'product_uom': line.product_id.uom_id.id,
                            'product_uom': line.product_id.uom_id.id,
                            'product_uom_qty': line.product_uom_qty,
                            'partner_id': self.env.user.partner_id.id,
                            'location_id':request.from_location_id.id,
                            # 'location_id': br_picking_type_id.default_location_src_id.id or bu_picking_type_id.default_location_src_id.id,
                            'location_dest_id': request.to_location_id.id,
                            'origin': request.name,
                            'borrow_request_ref_id': request.id,
                            'warehouse_id': request.to_location_id.warehouse_id.id,
                            'priority': '1',
                        }))

                br_picking = picking_obj.create({
                    'partner_id': self.env.user.partner_id.id,
                    'scheduled_date': datetime.today(),
                    'origin': request.name,
                    'move_type': 'direct',
                    'company_id': self.env.user.company_id.id,
                    'move_lines': br_move_lines,
                    'picking_type_id': br_picking_type_id.id,
                    'location_id':request.from_location_id.id,
                    # 'location_id': br_picking_type_id.default_location_src_id.id,
                    'location_dest_id': request.to_location_id.id,
                    'borrow_request_ref_id': request.id,
                    'hr_br_id': request.hr_br_id.id or False,
                })

                # picking.action_confirm()
            # return br_picking

    def _compute_delivery_count(self):
        requests = []
        for order in self:
            request_ids = self.env['stock.picking'].search([('borrow_request_ref_id', '=', order.id)])
            order.delivery_count = len(request_ids)
    
    def _check_orderable(self):
        for req in self:
            # if any(req.state == 'done' for item in req.):
                # req.orderable = True
            orderable = False
            picking_ids = self.env['stock.picking'].search([('borrow_request_ref_id', '=', req.id)])
            for picking in picking_ids:
                if picking.state == 'done':
                    orderable = True
            req.orderable = orderable
                

    def button_return(self):
        if self.create_uid.id == self.env.user.id:
            self.write({'state': 'return'})
            picking = self._create_return_picking()
        else:
            raise UserError(_("Only Borrow Person can return"))

    def _create_return_picking(self):
        picking_obj = self.env['stock.picking']
        move_lines = []

        for request in self:
            picking_type_id = self.env['stock.picking.type'].search(
                [('code', '=', 'internal'), ('hr_bu_id', '=', request.hr_bu_id.id)], limit=1)

            for line in request.custom_order_line:
                if line.product_id.type in ['consu', 'product']:
                    move_lines.append((0, 0, {
                        'name': request.name,
                        'company_id': self.env.user.company_id.id,
                        'product_id': line.product_id.id,
                        'product_uom': line.product_id.uom_id.id,
                        'product_uom_qty': line.product_uom_qty,
                        'partner_id': self.env.user.partner_id.id,
                        'picking_type_id': picking_type_id.id,
                        'location_id': request.to_location_id.id,
                        'location_dest_id':request.from_location_id.id,
                        # 'location_dest_id': picking_type_id.default_location_src_id.id or bu_picking_type_id.default_location_src_id.id,
                        'origin': request.name,
                        'borrow_request_ref_id': request.id,
                        'warehouse_id': picking_type_id.warehouse_id.id,
                        'priority': '1',
                    }))

            picking = picking_obj.create({

                'partner_id': self.env.user.partner_id.id,
                'scheduled_date': datetime.today(),
                'origin': request.name,
                'move_type': 'direct',
                'company_id': self.env.user.company_id.id,
                'move_lines': move_lines,
                'picking_type_id': picking_type_id.id,
                'location_dest_id':request.from_location_id.id,
                # 'location_dest_id': picking_type_id.default_location_src_id.id,
                'location_id': request.to_location_id.id,
                'borrow_request_ref_id': request.id,
                'hr_bu_id': request.hr_bu_id.id,
            })

        return picking

    def create_sale_request(self):
        return self._create_sale_order()

    def _create_sale_order(self):
        sale_obj = self.env['sale.order']
        for request in self:
            request_lines = []
            for line in request.custom_order_line:
                if line.product_id.type in ['consu', 'product']:
                    request_lines.append((0, 0, {
                        'product_id': line.product_id.id,
                        'product_uom': line.product_uom.id,
                        'product_uom_qty': line.product_uom_qty,
                        'production_delivery_date': line.delivery_date,
                        'estimated_delivery': line.estimated_delivery,
                    }))
            request_new = sale_obj.create({
                'borrow_request_id': request.id,
                'order_line': request_lines,
                'date_order': request.request_date,
                'note': request.note,
                'partner_id': self.env.user.partner_id.id,
                'user_id': request.user_id.id,
                'pricelist_id': request.pricelist_id.id,

            })
        return True

    def _compute_sale_order_ids(self):
        requests = []
        for order in self:
            request_ids = self.env['sale.order'].search([('borrow_request_id', '=', order.id)])
            order.sale_order_count = len(request_ids)

    def action_view_quotation(self):
        return {
            'name': _("Sale Order"),
            'view_mode': 'tree,form',
            'res_model': 'sale.order',
            'tree_view_id': self.env.ref('sale.view_order_tree').id,
            'form_view_id': self.env.ref('sale.view_order_form').id,
            'type': 'ir.actions.act_window',
            'domain': [('borrow_request_id', '=', self.id)]
        }


class BorrowRequestLine(models.Model):
    _name = 'borrow.request.line'
    _description = 'Borrow Request Line'

    @api.depends('product_split_uom_qty')
    def _count_remaining_qty(self):
        for record in self:
            if record.product_split_uom_qty:
                record.remaining_qty = record.product_uom_qty - record.product_split_uom_qty

    borrow_request_id = fields.Many2one('borrow.request', string="Borrow Request References")
    product_id = fields.Many2one('product.product', string="product")
    product_uom_qty = fields.Float(string="Quantity")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure',
                                  domain="[('category_id', '=', product_uom_category_id)]")

    @api.onchange('product_id')
    def onchange_bu_product(self):
        self.product_uom = self.product_id.uom_id.id
        for rec in self.borrow_request_id:
            return {'domain': {
                'product_id': [('business_id', '=', rec.hr_bu_id.id), ('unit_or_part', '=', rec.unit_or_part)]}}


class SaleOrder(models.Model):
    _inherit = "sale.order"

    borrow_request_id = fields.Many2one('borrow.request')
    is_borrow = fields.Boolean(string='Is Borrow')
