from datetime import datetime
from collections import defaultdict
from itertools import groupby
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError
from odoo.tools import date_utils, float_round, float_is_zero
import logging

_logger = logging.getLogger(__name__)


class JobRequestLine(models.Model):
    _name = "job.request.line"
    _description = "Job Request Line"

    raw_material_job_id = fields.Many2one('job.request', 'Job request for components', check_compnay=True)
    name = fields.Text(string='Description')
    sequence = fields.Integer(string='Sequence', default=10)
    product_id = fields.Many2one('product.product', string='Product', domain=[('sale_ok', '=', True)])
    product_uom_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', default=1.0)
    price_unit = fields.Float('Price Unit', related="product_id.lst_price", required=True, digits='Product Price',
                              default=0.0)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    lot_id = fields.Many2one('stock.production.lot', string='Serial Number', change_default=True)
    bom_line_id = fields.Many2one('mrp.bom.line', 'BoM Line', check_company=True)
    product_uom = fields.Many2one('uom.uom', string="Unit of Measure")
    unit_factor = fields.Float('Unit Factor', default=1)
    date = fields.Datetime('Date', default=fields.Datetime.now, index=True, required=True)


class JobRequestUnbuild(models.Model):
    _name = "job.request.unbuild.line"
    _description = "Job Request Unbuild"

    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    raw_material_job_id = fields.Many2one('job.request', string='Job Request Unbuild', required=True,
                                          ondelete='cascade', index=True, copy=False)
    name = fields.Text(string='Description')
    product_id = fields.Many2one('product.product', string='Product', domain=[('sale_ok', '=', True)])
    original_product_uom_qty = fields.Float(string='BOM Qty(Original Components Qty)', digits='Product Unit of Measure',
                                            default=1.0)
    product_uom_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', default=1.0)
    price_unit = fields.Float('Price Unit', related="product_id.lst_price", required=True, digits='Product Price',
                              default=0.0)
    lot_id = fields.Many2one('stock.production.lot', string='Serial Number', change_default=True)
    product_uom = fields.Many2one('uom.uom', string="Unit of Measure")
    unit_factor = fields.Float('Unit Factor', default=1)
    date = fields.Datetime('Date', default=fields.Datetime.now, index=True, required=True)
    is_order = fields.Boolean("Order Part", default=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('unbuild', 'Unbuild'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], string="State", store=True, related="raw_material_job_id.state")
    qty_done = fields.Float(string='Order Quantity', digits='Product Unit of Measure', default=0.0)


class JobRequestDamage(models.Model):
    _name = "damage.component.line"
    _description = "Damage Component"

    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    raw_material_job_id = fields.Many2one('job.request', string='Job Request Unbuild', required=True,
                                          ondelete='cascade', index=True, copy=False)
    product_id = fields.Many2one('product.product', string='Product', domain=[('sale_ok', '=', True)])
    product_uom_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', default=1.0)
    lot_id = fields.Many2one('stock.production.lot', string='Serial Number', change_default=True)
    product_uom = fields.Many2one('uom.uom', string="Unit of Measure")
    unit_factor = fields.Float('Unit Factor', default=1)
    date = fields.Datetime('Date', default=fields.Datetime.now, index=True, required=True)
    note = fields.Text('Remark')


class PartRecommendation(models.Model):
    _name = "part.recommendation.line"
    _description = "Part Recommendation"

    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    raw_material_job_id = fields.Many2one('job.request', string='Job Request Unbuild', required=True,
                                          ondelete='cascade', index=True, copy=False)
    name = fields.Text(string='Description')
    product_id = fields.Many2one('product.product', string='Product', domain=[('sale_ok', '=', True)])
    original_product_uom_qty = fields.Float(string='BOM Qty(Original Components Qty)', digits='Product Unit of Measure',
                                            default=1.0)
    product_uom_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', default=1.0)
    price_unit = fields.Float('Price Unit', related="product_id.lst_price", required=True, digits='Product Price',
                              default=0.0)
    lot_id = fields.Many2one('stock.production.lot', string='Serial Number', change_default=True)
    product_uom = fields.Many2one('uom.uom', string="Unit of Measure")
    unit_factor = fields.Float('Unit Factor', default=1)
    date = fields.Datetime('Date', default=fields.Datetime.now, index=True, required=True)

class JobOrderType(models.Model):
    _name = 'job.order.type'
    _description = 'Job Order Type'

    name = fields.Char('Name')
    code = fields.Char('Code')
    type = fields.Selection([('service', 'Service'), ('overall', 'Overhaul')], string='Job Order Type', default='overall')

class JobRequest(models.Model):
    _name = "job.request"
    _description = "Job Request"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    def action_move_items(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_account_moves_all_a")
        action['domain'] = [('request_id', '=', self.id)]
        return action

    def action_see_move_scrap(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_stock_scrap")
        action['domain'] = [('order_id', '=', self.id)]
        action['context'] = dict(self._context, default_origin=self.name)
        return action

    def action_see_service(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_invoice_type")
        action['domain'] = [('job_re_id', '=', self.id)]
        action['context'] = dict(self._context, default_origin=self.name)
        return action

    def _compute_picking_ids(self):
        for order in self:
            picking_type_id = self.env['stock.picking.type'].search(
                [('code', '=', 'internal'), ('default_location_dest_id.scrap_location', '=', True),
                 ('business_id', '=', order.create_uid.hr_bu_id.id), ('warehouse_id', '=', order.warehouse_id.id)],
                limit=1)
            job_ref_ids = self.env['stock.picking'].search(
                [('job_re_id', '=', order.id), ('picking_type_id', '=', picking_type_id.id)])
            order.damage_delivery_count = len(job_ref_ids)

    def _compute_picking_finish_ids(self):
        for order in self:
            job_ref_ids = self.env['stock.picking'].search([('job_re_id', '=', order.id), ('picking_type_id', '=', self.warehouse_id.out_type_id.id)])
            order.delivery_count = len(job_ref_ids)

    def action_view_finish(self):
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        pickings = self.env['stock.picking'].search([('job_re_id', '=', self.id), ('picking_type_id', '=', self.warehouse_id.out_type_id.id)])
        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif pickings:
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = pickings.id
        return action

    def _compute_picking_receipt(self):
        for order in self:
            job_ref_ids = self.env['stock.picking'].search([('job_re_id', '=', order.id), ('picking_type_id', '=', self.warehouse_id.in_type_id.id)])
            order.receipt_count = len(job_ref_ids)

    def action_view_receipt(self):
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        pickings = self.env['stock.picking'].search([('job_re_id', '=', self.id), ('picking_type_id', '=', self.warehouse_id.in_type_id.id)])
        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif pickings:
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = pickings.id
        return action

    def action_view_delivery_part(self):
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        picking_type_id = self.env['stock.picking.type'].search(
            [('code', '=', 'internal'), ('default_location_dest_id.scrap_location', '=', True),
             ('business_id', '=', self.create_uid.hr_bu_id.id), ('warehouse_id', '=', self.warehouse_id.id)], limit=1)
        pickings = self.env['stock.picking'].search(
            [('job_re_id', '=', self.id), ('picking_type_id', '=', picking_type_id.id)])
        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif pickings:
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = pickings.id
        # Prepare the context.
        return action

    def action_done(self):
        self.write({'state': 'done'})
        self._create_picking()

    def _create_picking(self):
        pick_obj = self.env['stock.picking']
        move_lines = []
        location_dest_id = self.env['stock.location'].search([('usage', '=', 'customer')], limit=1).id
        for request in self:
            if request.product_id.type in ['consu', 'product']:
                move_lines.append((0, 0, {
                    'name': request.product_id.name + '-' + request.name,
                    'company_id': request.company_id.id,
                    'product_id': request.product_id.id,
                    'product_uom': request.product_id.uom_id.id,
                    'product_uom_qty': request.product_qty,
                    'partner_id': request.partner_id.id,
                    'location_id': request.warehouse_id.lot_stock_id.id,
                    'location_dest_id': location_dest_id,
                    'origin': request.name,
                    'warehouse_id': request.warehouse_id.id,
                    'priority': '1',
                    # 'price_unit':1,
                    
                }))
            picking = pick_obj.create({
                'partner_id': request.partner_id.id,
                'origin': request.name,
                'move_type': 'direct',
                'company_id': request.company_id.id,
                'move_lines': move_lines,
                'picking_type_id': request.warehouse_id.out_type_id.id,
                'location_id': request.warehouse_id.lot_stock_id.id,
                'location_dest_id': location_dest_id,
                'job_re_id': request.id,
                'hr_bu_id': request.create_uid.current_bu_br_id.id,
                'unit_or_part': request.product_id.unit_or_part,
                'reman_in_out':True,
            })
        picking.action_confirm()
        return True

    @api.model
    def _get_default_picking_type(self):
        company_id = self.env.context.get('default_company_id', self.env.company.id)
        test = self.env['stock.picking.type'].search([
            ('code', '=', 'mrp_operation'),
            ('warehouse_id.company_id', '=', company_id),
        ], limit=1).id

        return self.env['stock.picking.type'].search([
            ('code', '=', 'mrp_operation'),
            ('warehouse_id.company_id', '=', company_id),
        ], limit=1).id

    @api.model
    def _get_default_location_src_id(self):
        location = False
        company_id = self.env.context.get('default_company_id', self.env.company.id)
        if self.env.context.get('default_picking_type_id'):
            location = self.env['stock.picking.type'].browse(
                self.env.context['default_picking_type_id']).default_location_src_id
        if not location:
            location = self.env['stock.warehouse'].search([('company_id', '=', company_id)], limit=1).lot_stock_id
        return location and location.id or False

    @api.model
    def _get_default_location_dest_id(self):
        location = False
        company_id = self.env.context.get('default_company_id', self.env.company.id)
        if self._context.get('default_picking_type_id'):
            location = self.env['stock.picking.type'].browse(
                self.env.context['default_picking_type_id']).default_location_dest_id
        if not location:
            location = self.env['stock.warehouse'].search([('company_id', '=', company_id)], limit=1).lot_stock_id
        return location and location.id or False

    @api.model
    def _default_warehouse_id(self):
        return self.env['stock.warehouse'].search(
            [('company_id', '=', self.env.company.id), ('hr_bu_id', '=', self.env.user.current_bu_br_id.id)], limit=1)

    name = fields.Char('Reference', copy=False, readonly=True, default=lambda x: _('New'))
    partner_id = fields.Many2one('res.partner', string='Partner')
    product_id = fields.Many2one(
        'product.product', 'Product',
        domain="[('bom_ids', '!=', False), ('bom_ids.active', '=', True), ('bom_ids.type', '=', 'normal'), ('type', 'in', ['product', 'consu']), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        readonly=True, required=True, check_company=True,
        states={'draft': [('readonly', False)]})

    product_tmpl_id = fields.Many2one('product.template', 'Product Template', related='product_id.product_tmpl_id')

    product_qty = fields.Float(
        'Quantity To Produce',
        default=1.0, digits='Product Unit of Measure',
        readonly=True, required=True, tracking=True,
        states={'draft': [('readonly', False)]})

    product_uom_id = fields.Many2one(
        'uom.uom', 'Product Unit of Measure',
        readonly=True, required=True,
        states={'draft': [('readonly', False)]})

    picking_type_id = fields.Many2one(
        'stock.picking.type', 'Operation Type',
        domain="[('code', '=', 'mrp_operation'), ('company_id', '=', company_id)]",
        default=_get_default_picking_type, required=True, check_company=True)

    location_src_id = fields.Many2one(
        'stock.location', 'Components Location',
        default=_get_default_location_src_id,
        readonly=True, required=True,
        domain="[('usage','=','internal'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        states={'draft': [('readonly', False)]}, check_company=True,
        help="Location where the system will look for components.")
    location_dest_id = fields.Many2one(
        'stock.location', 'Finished Products Location',
        default=_get_default_location_dest_id,
        readonly=True, required=True,
        domain="[('usage','=','internal'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        states={'draft': [('readonly', False)]}, check_company=True,
        help="Location where the system will stock the finished products.")

    date_planned_start = fields.Datetime(
        'Planned Date', copy=False, default=fields.Datetime.now,
        help="Date at which you plan to start the production.",
        index=True, required=True, store=True)

    bom_id = fields.Many2one(
        'mrp.bom', 'Bill of Material',
        readonly=True, states={'draft': [('readonly', False)]},
        domain="""['&','|',('company_id', '=', False),('company_id', '=', company_id),'&','|',
        ('product_id','=',product_id),'&',('product_tmpl_id.product_variant_ids','=',product_id),
        ('product_id','=',False),('type', '=', 'normal')]""",check_company=True,
        help="Bill of Materials allow you to define the list of required components to make a finished product.")

    state = fields.Selection([
        ('draft', 'Draft'),
        ('unbuild', 'Unbuild'),
        ('confirm', 'Confirm'),
        ('build', 'build'),
        ('ready', 'Ready to Deliver'),
        ('done', 'Close'),
        ('cancel', 'Cancelled')
    ], string="State", default='draft', copy=False, index=True, readonly=True, tracking=True, store=True)
    move_raw_ids = fields.One2many(
        'job.request.line', 'raw_material_job_id', 'components', copy=False,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})

    unbuild_ids = fields.One2many(
        'job.request.unbuild.line', 'raw_material_job_id', 'Unbuild Part', copy=False,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})

    damage_ids = fields.One2many(
        'damage.component.line', 'raw_material_job_id', 'Damage Component', copy=False,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})

    partrecommendation_ids = fields.One2many('part.recommendation.line', 'raw_material_job_id', '', copy=False)

    user_id = fields.Many2one('res.users', 'Responsible', default=lambda self: self.env.user,
                              states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
                              domain=lambda self: [('groups_id', 'in', self.env.ref('mrp.group_mrp_user').id)])

    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company,
                                 index=True, required=True)

    is_locked = fields.Boolean('Is Locked', default=True, copy=False)
    is_order = fields.Boolean('Is Locked', default=False, copy=False)

    show_final_lots = fields.Boolean('Show Final Lots', compute='_compute_show_lots')
    production_location_id = fields.Many2one('stock.location', "Production Location",
                                             related='product_id.property_stock_production',
                                             readonly=False)  # FIXME sle: probably wrong if document in another company
    procurement_group_id = fields.Many2one('procurement.group', 'Procurement Group', copy=False)

    propagate_cancel = fields.Boolean(
        'Propagate cancel and split',
        help='If checked, when the previous move of the move (which was generated by a next procurement) is cancelled or split, the move generated by this move will too')

    service_charge = fields.Float('Service Charge', digits='Product Price', default=0.0, required=True)
    part_order_ids = fields.One2many('part.order', 'job_ref_id', string='Transfers')
    part_order_count = fields.Integer(string='Part Orders', compute='_compute_part_order_ids')
    business_id = fields.Many2one('business.unit', string="Business Unit", default=lambda self: self.env.user.current_bu_br_id)
    note = fields.Text('Remark')

    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position',
                                         domain="[('company_id', '=', company_id)]", check_company=True,
                                         help="Fiscal positions are used to adapt taxes and accounts for particular customers or sales orders/invoices."
                                              "The default value comes from the customer.")

    opportunity_id = fields.Many2one(
        'crm.lead', string="Opportunity", check_company=True,
        domain="[('type','=','opportunity'),'|',('company_id','=',False),('company_id','=',company_id)]")

    job_checklist_template = fields.Many2many('job.html.checklist.template', string=' ')

    checklist_template = fields.Many2many("html.checklist.template", string="Checklist Template")

    checklist_progress = fields.Float(string='Progress', store=True, recompute=True,
                                      default=0.0)
    max_rate = fields.Integer(string='Maximum rate', default=100)

    delivered_damage = fields.Boolean("Delivered damage?", default=False)
    picking_ids = fields.One2many('stock.picking', 'job_re_id', string='Transfers')
    damage_delivery_count = fields.Integer(string='Delivery Orders')
    delivery_count = fields.Integer(string='Delivery Orders', compute='_compute_picking_finish_ids')

    order_ids = fields.One2many('request.quotation', 'job_order_id', string='Orders')
    sale_order_count = fields.Integer(string='Sale order count', readonly=True, compute='_get_sale_order_count')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True, default=_default_warehouse_id)
    scrap_count = fields.Integer(compute='_compute_scrap_move_count', string='Scrap Move')
    invoice_count = fields.Integer(compute='_compute_invoice_count', string='Invoice')
    replace_ids = fields.One2many('replace.product.line', 'job_order_id', string='Replacement Product')
    note = fields.Text('Note')
    type = fields.Selection([('service', 'Service'), ('overall', 'Overhaul')], string='Job Order Type', default='overall')
    order_type = fields.Many2one('job.order.type', string='Order Type',domain="[('type','=',type)]")
    sequence = fields.Integer('Sequence')
    receipt_count = fields.Integer(compute='_compute_picking_receipt')
    inv_cancel = fields.Boolean(compute='compute_inv_cancel',default=False)

    def compute_inv_cancel(self):
        picking_id = self.env['stock.picking'].search([('origin','=',self.name)])
        self.inv_cancel = False
        for pick in picking_id:
            if pick.state == 'done':
                self.inv_cancel = True

    @api.onchange('business_id')
    def _onchange_bu(self):
        return {'domain': {'business_id': [('id', 'in', [bu.id for bu in self.env.user.hr_bu_ids])]}}

    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'Reference must be unique per Company!'),
        ('qty_positive', 'check (product_qty > 0)', 'The quantity to produce must be positive!'),
    ]

    def replace(self, old, new, desc, product_uom_qty):
        raw_id = self.move_raw_ids.filtered(lambda x: x.product_id == old)
        if raw_id.product_uom_qty <= product_uom_qty:
            raw_id.write({'product_id': new.id})
        else:
            raw_id.write({'product_uom_qty': raw_id.product_uom_qty - product_uom_qty})
            self.env['job.request.line'].create({'product_id': new.id,
                                                 'product_uom_qty': product_uom_qty,
                                                 'product_uom': new.uom_id.id,
                                                 'raw_material_job_id': raw_id.raw_material_job_id.id})
        self.env['replace.product.line'].create({'product_id': old.id,
                                                 'replaced_product_id': new.id,
                                                 'desc': desc,
                                                 'qty': product_uom_qty,
                                                 'uom_id': new.uom_id.id,
                                                 'job_order_id': self.id})
        return raw_id

    def _compute_scrap_move_count(self):
        data = self.env['stock.scrap'].read_group([('order_id', 'in', self.ids)], ['order_id'],
                                                  ['order_id'])
        count_data = dict((item['order_id'][0], item['order_id_count']) for item in data)
        for order in self:
            order.scrap_count = count_data.get(order.id, 0)

    def _compute_invoice_count(self):
        data = self.env['account.move'].read_group([('job_re_id', 'in', self.ids)], ['job_re_id'],
                                                  ['job_re_id'])
        count_data = dict((item['job_re_id'][0], item['job_re_id_count']) for item in data)
        for order in self:
            order.invoice_count = count_data.get(order.id, 0)

    def job_close(self):
        for rec in self:
            rec.state = 'done'
            if rec.type == 'overall':
                rec._create_processing_transition()

    def action_view_order(self):
        sale_order_ids = self.mapped('order_ids')
        action = self.env.ref('request_quotation.action_request_quotation').read()[0]

        if len(sale_order_ids) > 1:
            action['domain'] = [('id', 'in', sale_order_ids.ids)]
        elif sale_order_ids:
            action['views'] = [(self.env.ref('request_quotation.req_quotation_view_form').id, 'form')]
            action['res_id'] = sale_order_ids.id

        return action

    def action_confirm_jo(self):
        dest_location_id = self.env['stock.location'].search(
            [('hr_bu_id', '=', self.business_id.id), ('part_location', '=', True)], limit=1)
        if not dest_location_id:
            dest_location_id = self.env['stock.location'].create({'name': 'Production',
                                                                  'hr_bu_id': self.business_id.id,
                                                                  'usage': 'internal',
                                                                  'location_id': self.warehouse_id.lot_stock_id.location_id.id,
                                                                  'part_location': True, })
       
        if self.type == 'overall':
            if not self.business_id.inventory_machine_account_id or not self.business_id.processing_account_id:
                raise UserError(_('You Need To Configure Processing Account'))
            
            self._create_processing_transition(self, True)
            self._create_receipt(dest_location_id, self)
        self.write({'state': 'confirm'})

    def _get_sale_order_count(self):
        for order in self:
            order_id = self.env['request.quotation'].search([('job_order_id', '=', order.id)])
            order.sale_order_count = len(order_id)

    @api.onchange('checklist_template')
    def _get_checklist(self):
        checklist = [(5, 0, 0)]

        for temp in self.checklist_template:
            f = False

            for i in self.job_checklist_template:
                if temp._origin.id == i.template_id.id:
                    checklist.append((0, 0, {
                        'template_id': temp._origin.id,
                        'name': temp.name,
                        'body_html': i.body_html,
                    }))

                    f = True
            if f:
                continue

            checklist.append((0, 0, {
                'template_id': temp._origin.id,
                'name': temp.name,
                'body_html': temp.body_html,
            }))

        if len(checklist) > 0:
            self.job_checklist_template = checklist

    def action_view_part_order(self):
        action = self.env.ref('job_request.action_part_orders').read()[0]
        part_orders = self.mapped('part_order_ids')

        if len(part_orders) > 1:
            action['domain'] = [('id', 'in', part_orders.ids)]
        elif part_orders:
            action['views'] = [(self.env.ref('job_request.view_part_order_form').id, 'form')]
            action['res_id'] = part_orders.id
        # Prepare the context.
        return action

    def _compute_part_order_ids(self):
        for order in self:
            job_ref_ids = self.env['part.order'].search([('job_ref_id', '=', order.id)])
            order.part_order_count = len(job_ref_ids)

    @api.depends('product_id.tracking')
    def _compute_show_lots(self):
        for production in self:
            production.show_final_lots = production.product_id.tracking != 'none'

    @api.onchange('product_id', 'picking_type_id', 'company_id')
    def onchange_product_id(self):
        """ Finds UoM of changed product. """
        if not self.product_id:
            self.bom_id = False
        else:
            bom = self.env['mrp.bom']._bom_find(products=self.product_id, picking_type=self.picking_type_id,
                                                company_id=self.company_id.id, bom_type='normal')[self.product_id]
            if bom:
                self.bom_id = bom
                self.product_qty = self.bom_id.product_qty
                self.product_uom_id = self.bom_id.product_uom_id.id
            else:
                self.bom_id = False
                self.product_uom_id = self.product_id.uom_id.id
            return {'domain': {'product_uom_id': [('category_id', '=', self.product_id.uom_id.category_id.id)]}}

    @api.onchange('bom_id')
    def _onchange_bom_id(self):
        self.product_qty = self.bom_id.product_qty
        self.product_uom_id = self.bom_id.product_uom_id.id
        self.move_raw_ids = [(2, move.id) for move in self.move_raw_ids.filtered(lambda m: m.bom_line_id)]
        self.picking_type_id = self.bom_id.picking_type_id or self.picking_type_id

    @api.onchange('bom_id', 'product_id', 'product_qty', 'product_uom_id')
    def _onchange_move_raw(self):
        if self.bom_id and self.product_qty > 0:
            # keep manual entries
            self.move_raw_ids = []
            list_move_raw = [(4, move.id) for move in self.move_raw_ids.filtered(lambda m: not m.bom_line_id)]
            moves_raw_values = self._get_moves_raw_values()
            move_raw_dict = {move.bom_line_id.id: move for move in self.move_raw_ids.filtered(lambda m: m.bom_line_id)}

            temp = [1 for line in moves_raw_values]
            temp_pro = []
            p = 0
            product_qty = 0
            for line in moves_raw_values:
                if temp[p] == 0:
                    p += 1
                    continue
                product_qty = line['product_uom_qty']
                temp[p] = 0
                p += 1
                pp = p
                while (pp < len(moves_raw_values)):
                    if line['product_id'] == moves_raw_values[pp]['product_id']:
                        temp[pp] = 0
                        product_qty += moves_raw_values[pp]['product_uom_qty']

                    pp += 1

                _dic = {'sequence': line['sequence'], 'name': line['name'], 'bom_line_id': line['bom_line_id'],
                        'product_id': line['product_id'], 'product_uom_qty': product_qty,
                        'product_uom': line['product_uom'], 'raw_material_job_id': line['raw_material_job_id'],
                        'price_unit': line['price_unit']}
                temp_pro.append(_dic)

            for move_raw_values in temp_pro:
                if move_raw_values['bom_line_id'] in move_raw_dict:
                    # update existing entries
                    list_move_raw += [(1, move_raw_dict[move_raw_values['bom_line_id']].id, move_raw_values)]
                else:
                    # add new entries
                    list_move_raw += [(0, 0, move_raw_values)]
            self.move_raw_ids = list_move_raw
        else:
            self.move_raw_ids = [(2, move.id) for move in self.move_raw_ids.filtered(lambda m: m.bom_line_id)]

    def _get_moves_raw_values(self):
        moves = []
        for production in self:
            factor = production.product_uom_id._compute_quantity(production.product_qty,
                                                                 production.bom_id.product_uom_id) / production.bom_id.product_qty
            boms, lines = production.bom_id.explode(production.product_id, factor,
                                                    picking_type=production.bom_id.picking_type_id)
            for bom_line, line_data in lines:
                if bom_line.child_bom_id and bom_line.child_bom_id.type == 'phantom' or \
                        bom_line.product_id.type not in ['product', 'consu']:
                    continue
                moves.append(production._get_move_raw_values(bom_line, line_data))
        return moves

    def _get_move_raw_values(self, bom_line, line_data):
        quantity = line_data['qty']
        # alt_op needed for the case when you explode phantom bom and all the lines will be consumed in the operation given by the parent bom line
        data = {
            'sequence': bom_line.sequence,
            'name': self.name,
            'bom_line_id': bom_line.id,
            'product_id': bom_line.product_id.id,
            'product_uom_qty': quantity,
            'product_uom': bom_line.product_uom_id.id,
            'raw_material_job_id': self.id,
            'price_unit': bom_line.product_id.standard_price,
        }
        return data

    def get_sequence(self, order_type):
        job_id = self.env['job.request'].search([('order_type', '=', order_type)], order="sequence desc", limit=1)
        sequence = job_id.sequence
        order_type = self.env['job.order.type'].browse(order_type)
        code = order_type.code +'-'+ datetime.today().strftime("%Y%m")+'%04d' % (int(sequence)+1,)
        return code, int(sequence)+1
    
    def _create_processing_transition(self,request_id=False,param=False):
        res = []
        request_id = request_id or self
        move_line = {'name': request_id.name,
                     # 'account_id': request_id.product_id.categ_id.property_stock_valuation_account_id.id,
                     'account_id': request_id.business_id.inventory_machine_account_id.id,
                     'partner_id': request_id.partner_id.id,
                     'date': datetime.today(),
                     'amount_currency': 1 if param else -1,
                     'debit': 1.0 if param else 0.0,
                     'credit': 0.0 if param else 1,
                     'currency_id': self.env.company.currency_id.id,
                     'request_id': request_id.id, }
        res.append(move_line)

        move_line = {'name': request_id.name,
                     # 'account_id': request_id.product_id.categ_id.property_stock_account_input_categ_id.id,
                     'account_id': request_id.business_id.processing_account_id.id,
                     'partner_id': request_id.partner_id.id,
                     'date': datetime.today(),
                     'amount_currency': -1 if param else 1,
                     'credit': 1.0 if param else 0.0,
                     'debit': 0.0 if param else 1.0,
                     'currency_id': self.env.company.currency_id.id,
                     'request_id': request_id.id, }
        res.append(move_line)
        line_ids = [(0, 0, l) for l in res]
        journal_id = self.env['account.journal'].search([('type','=','general'),('bu_br_id','=',request_id.business_id.id)], limit=1)
        if not journal_id:
            raise UserError(_(
                "No journal could be found in %(bu)s for any of those types: %(journal_types)s",
                bu=request_id.business_id.code,
                journal_types=', '.join(['Miscellaneous']),
            ))
        move_vals = {
            'journal_id': journal_id.id,
            'ref': request_id.name,
            'date': datetime.today(),
            'line_ids': line_ids,
        }
        move_id = self.env['account.move'].create(move_vals)
        move_id.action_post()
        return True

    def get_move_lines(self,location_id, dest_location_id, res):
        move_lines = []
        move_lines.append((0, 0, {
            'name': res.product_id.name + '-' + res.name,
            'company_id': res.company_id.id,
            'product_id': res.product_id.id,
            'product_uom': res.product_id.uom_id.id,
            'product_uom_qty': res.product_qty,
            'partner_id': res.partner_id.id,
            'location_id': location_id,
            'location_dest_id': dest_location_id.id,
            'origin': res.name,
            'warehouse_id': res.warehouse_id.id,
            'priority': '1',
            # 'price_unit':0,
        }))
        return move_lines

    def _create_receipt(self, dest_location_id, res):
        pick_obj = self.env['stock.picking']
        location_id = self.env['stock.location'].search([('usage', '=', 'customer')], limit=1).id
        move_lines = self.get_move_lines(location_id, dest_location_id, res)
        picking = pick_obj.create({
            'partner_id': res.partner_id.id,
            'origin': res.name,
            'move_type': 'direct',
            'company_id': res.company_id.id,
            'move_lines': move_lines,
            'picking_type_id': res.warehouse_id.in_type_id.id,
            'location_id': location_id,
            'location_dest_id': dest_location_id.id,
            'job_re_id': res.id,
            'hr_bu_id': res.business_id.id,
            'unit_or_part': res.product_id.unit_or_part,
            'reman_in_out':True,
        })
        picking.action_confirm()
        return picking

    @api.model
    def create(self, values):

        _logger.info(values)
        if not values.get('name', False) or values['name'] == _('New'):
            values['name'], values['sequence'] = self.get_sequence(values.get('order_type', False)) or _('New')
        res = super(JobRequest, self).create(values)
        src_location = self.env.ref('stock.stock_location_customers')
        # dest_location_id = self.env['stock.location'].search(
        #     [('hr_bu_id', '=', res.business_id.id), ('part_location', '=', True)], limit=1)
        # if not dest_location_id:
        #     dest_location_id = self.env['stock.location'].create({'name': 'Production',
        #                                                           'hr_bu_id': res.business_id.id,
        #                                                           'usage': 'internal',
        #                                                           'location_id': res.warehouse_id.lot_stock_id.location_id.id,
        #                                                           'part_location': True, })
        # self._create_processing_transition(res,True)
        # if res.type == 'overall':
        #     self._create_receipt(dest_location_id, res)
        return res

    def write(self, vals):
        res = super(JobRequest, self).write(vals)
        return res

    def action_cancel(self):
        # view_id = self.env.ref('job_request.choose_delivery_carrier_view_form').id
        # name = _('Add a shipping method')

        # if self.state == 'draft':
        # self._create_processing_transition()
        return self.write({'state': 'cancel'})
        # return {
        #     'name': name,
        #     'type': 'ir.actions.act_window',
        #     'view_mode': 'form',
        #     'res_model': 'job.order.delivery',
        #     'view_id': view_id,
        #     'views': [(view_id, 'form')],
        #     'target': 'new',
        #     'context': {
        #         'default_job_id': self.id,
        #     }
        # }

    def _check_line_unlink(self):
        return self.filtered(lambda line: line.state in ('unbuild'))

    def unlink(self):
        if self._check_line_unlink():
            raise UserError(_('You can not remove unbuild request'))
        return super(JobRequest, self).unlink()

    def part_order(self):
        pick_obj = self.env['part.order']
        order_lines = []
        for request in self:
            for line in request.unbuild_ids:
                if line.product_id.type in ['consu', 'product']:
                    if line.qty_done > 0 and line.is_order:
                        order_lines.append((0, 0, {
                            'name': line.product_id.name + '-' + request.name,
                            'product_categ_id': line.product_id.categ_id.id,
                            'product_id': line.product_id.id,
                            'product_uom': line.product_id.uom_id.id,
                            'product_uom_qty': line.qty_done,
                            'price_unit': line.product_id.list_price or 0.0,
                            'tax_id': request.company_id.account_sale_tax_id,

                        }))
                        origin_uom_qty = 0.0
                        for origin in request.move_raw_ids:
                            if origin.product_id.id == line.product_id.id:
                                origin_uom_qty = origin.product_uom_qty

                        recommendation = self.env['part.recommendation.line'].create({
                            'name': line.product_id.name,
                            'product_id': line.product_id.id,
                            'original_product_uom_qty': origin_uom_qty,
                            'product_uom_qty': line.qty_done,
                            'product_uom': line.product_id.uom_id.id,
                            'raw_material_job_id': request.id,
                        })
            addr = request.partner_id.address_get(['delivery', 'invoice'])
            part_order = pick_obj.create({
                'partner_id': request.partner_id.id,
                'date_order': datetime.today().date(),
                'client_order_ref': request.partner_id.ref,
                'pricelist_id': request.partner_id.property_product_pricelist.id,
                'part_line': order_lines,
                'job_ref_id': request.id,
                'origin': request.name,
                'partner_invoice_id': addr['invoice'],
                'partner_shipping_id': addr['delivery'],
                'note': self.with_context(lang=request.partner_id.lang).env.user.company_id.sale_note,
                'warehouse_id': request.warehouse_id.id,
            })
            for line in request.unbuild_ids:
                line.write({
                    'is_order': False
                })

    def _create_delivery_line(self, carrier, price_unit, part_order):
        SaleOrderLine = self.env['part.order.line']
        if self.partner_id:
            # set delivery detail in the customer language
            carrier = carrier.with_context(lang=self.partner_id.lang)

        # Apply fiscal position
        taxes = carrier.product_id.taxes_id.filtered(lambda t: t.company_id.id == self.company_id.id)
        taxes_ids = taxes.ids
        if self.partner_id and self.fiscal_position_id:
            taxes_ids = self.fiscal_position_id.map_tax(taxes, carrier.product_id, self.partner_id).ids

        # Create the sales order line
        carrier_with_partner_lang = carrier.with_context(lang=self.partner_id.lang)
        if carrier_with_partner_lang.product_id.description_sale:
            so_description = '%s: %s' % (carrier_with_partner_lang.name,
                                         carrier_with_partner_lang.product_id.description_sale)
        else:
            so_description = carrier_with_partner_lang.name
        values = {
            'part_id': part_order.id,
            'name': so_description,
            'product_uom_qty': 1,
            'product_uom': carrier.product_id.uom_id.id,
            'product_id': carrier.product_id.id,
            'tax_id': [(6, 0, taxes_ids)],
        }
        if carrier.invoice_policy == 'real':
            values['price_unit'] = 0
            values['name'] += _(' (Estimated Cost: %s )') % self._format_currency_amount(price_unit)
        else:
            values['price_unit'] = price_unit
        if carrier.free_over and self.company_id.currency_id.is_zero(price_unit):
            values['name'] += '\n' + 'Free Shipping'
        sol = SaleOrderLine.sudo().create(values)
        return sol

    def _create_service_line(self, product_id, service_charge, part_order):
        SaleOrderLine = self.env['part.order.line']
        so_description = "Service Charge for " + self.name
        values = {
            'part_id': part_order.id,
            'name': so_description,
            'product_uom_qty': 1,
            'product_uom': product_id.uom_id.id,
            'product_id': product_id.id,
            'price_unit': service_charge
        }
        sol = SaleOrderLine.sudo().create(values)
        return sol

    def _create_part_line(self, part_order):
        SaleOrderLine = self.env['part.order.line']

        src_location = self.env['stock.picking.type'].search([('code', '=', 'internal'), ('is_part_order', '=', True),
                                                              ('business_id', '=', self.env.user.business_id.id),
                                                              ('warehouse_id', '=', self.warehouse_id.id)],
                                                             limit=1).default_location_dest_id
        des_location = self.env['stock.picking.type'].search([('code', '=', 'internal'), ('is_part_order', '=', True),
                                                              ('business_id', '=', self.env.user.business_id.id),
                                                              ('warehouse_id', '=', self.warehouse_id.id)],
                                                             limit=1).default_location_src_id

        for line in self.unbuild_ids:
            values = {
                'part_id': part_order.id,
                'name': line.product_id.name,
                'product_uom_qty': line.product_uom_qty,
                'product_uom': line.product_uom.id,
                'product_id': line.product_id.id,
                'price_unit': 0
            }
            sol = SaleOrderLine.sudo().create(values)
            move_line = self.env['stock.move'].create({
                'product_id': line.product_id.id,
                'product_uom_qty': line.product_uom_qty,
                'product_uom': line.product_uom.id,
                'location_id': src_location.id,
                'location_dest_id': des_location.id,
                'partner_id': self.partner_id.id,
                'name': _("Finish Product move :") + " %s" % (self.name),
                'state': 'confirmed',
            })
            move_line._action_assign()
            move_line._set_quantity_done(line.product_uom_qty)
            move_line._action_done()

        return sol

    def _format_currency_amount(self, amount):
        pre = post = u''
        if self.company_id.currency_id.position == 'before':
            pre = u'{symbol}\N{NO-BREAK SPACE}'.format(symbol=self.company_id.currency_id.symbol or '')
        else:
            post = u'\N{NO-BREAK SPACE}{symbol}'.format(symbol=self.company_id.currency_id.symbol or '')
        return u' {pre}{0}{post}'.format(amount, pre=pre, post=post)

    def part_order_fro_delivery_service(self):
        pick_obj = self.env['part.order']
        order_lines = []
        for request in self:
            order_lines.append((0, 0, {
                'name': request.product_id.name + '-' + request.name,
                'product_categ_id': request.product_id.categ_id.id,
                'product_id': request.product_id.id,
                'product_uom': request.product_id.uom_id.id,
                'product_uom_qty': request.product_qty,
                'price_unit': 0.0,
                'tax_id': request.company_id.account_sale_tax_id,
            }))
            addr = request.partner_id.address_get(['delivery', 'invoice'])
            company_id = self.env.context.get('default_company_id', self.env.company.id)
            picking_type_id = self.env['stock.picking.type'].search(
                [('code', '=', 'outgoing'), ('warehouse_id.company_id', '=', company_id),
                 ('business_id', '=', self.env.user.business_id.id)], limit=1).id
            part_order = pick_obj.create({
                'picking_type_id': picking_type_id,
                'partner_id': request.partner_id.id,
                'date_order': datetime.today().date(),
                'client_order_ref': request.partner_id.ref,
                'pricelist_id': request.partner_id.property_product_pricelist.id,
                'part_line': order_lines,
                'job_ref_id': request.id,
                'origin': request.name,
                'partner_invoice_id': addr['invoice'],
                'partner_shipping_id': addr['delivery'],
                'note': self.with_context(lang=request.partner_id.lang).env.user.company_id.sale_note,
            })
        return part_order

    def part_order_fro_delivery_service_cancel_build_state(self):
        pick_obj = self.env['part.order']
        order_lines = []
        src_location = self.env['stock.picking.type'].search([('code', '=', 'internal'), ('is_part_order', '=', True),
                                                              ('business_id', '=', self.env.user.business_id.id),
                                                              ('warehouse_id', '=', self.warehouse_id.id)],
                                                             limit=1).default_location_dest_id
        des_location = self.env['stock.picking.type'].search([('code', '=', 'internal'), ('is_part_order', '=', True),
                                                              ('business_id', '=', self.env.user.business_id.id),
                                                              ('warehouse_id', '=', self.warehouse_id.id)],
                                                             limit=1).default_location_src_id
        for request in self:
            order_lines.append((0, 0, {
                'name': request.product_id.name + '-' + request.name,
                'product_categ_id': request.product_id.categ_id.id,
                'product_id': request.product_id.id,
                'product_uom': request.product_id.uom_id.id,
                'product_uom_qty': request.product_qty,
                'price_unit': 0.0,
                'tax_id': request.company_id.account_sale_tax_id,
            }))
            addr = request.partner_id.address_get(['delivery', 'invoice'])
            company_id = self.env.context.get('default_company_id', self.env.company.id)
            picking_type_id = self.env['stock.picking.type'].search(
                [('code', '=', 'outgoing'), ('warehouse_id.company_id', '=', company_id),
                 ('business_id', '=', self.env.user.business_id.id)], limit=1).id
            part_order = pick_obj.create({
                'picking_type_id': picking_type_id,
                'partner_id': request.partner_id.id,
                'date_order': datetime.today().date(),
                'client_order_ref': request.partner_id.ref,
                'pricelist_id': request.partner_id.property_product_pricelist.id,
                'part_line': order_lines,
                'job_ref_id': request.id,
                'origin': request.name,
                'partner_invoice_id': addr['invoice'],
                'partner_shipping_id': addr['delivery'],
                'note': self.with_context(lang=request.partner_id.lang).env.user.company_id.sale_note,
                'warehouse_id': self.warehouse_id.id,
            })
            move_line = self.env['stock.move'].create({
                'product_id': request.product_id.id,
                'product_uom_qty': request.product_qty,
                'product_uom': request.product_id.uom_id.id,
                'location_id': src_location.id,
                'location_dest_id': des_location.id,
                'partner_id': request.partner_id.id,
                'name': _("Finish Product move :") + " %s" % (request.name),
                'state': 'confirmed',
            })
            move_line._action_assign()
            move_line._set_quantity_done(request.product_qty)
            move_line._action_done()

        return part_order

    def part_order_fro_delivery_service_cancel(self):
        pick_obj = self.env['part.order']
        order_lines = []
        for request in self:
            addr = request.partner_id.address_get(['delivery', 'invoice'])
            company_id = self.env.context.get('default_company_id', self.env.company.id)
            picking_type_id = self.env['stock.picking.type'].search(
                [('code', '=', 'outgoing'), ('warehouse_id.company_id', '=', company_id),
                 ('business_id', '=', self.env.user.business_id.id)], limit=1).id
            part_order = pick_obj.create({
                'picking_type_id': picking_type_id,
                'partner_id': request.partner_id.id,
                'date_order': datetime.today().date(),
                'client_order_ref': request.partner_id.ref,
                'pricelist_id': request.partner_id.property_product_pricelist.id,
                'part_line': [],
                'job_ref_id': request.id,
                'origin': request.name,
                'partner_invoice_id': addr['invoice'],
                'partner_shipping_id': addr['delivery'],
                'note': self.with_context(lang=request.partner_id.lang).env.user.company_id.sale_note,
            })
        return part_order


class Location(models.Model):
    _inherit = "stock.location"
    part_location = fields.Boolean('Is a Part Location?',
                                   help='Check this box to allow using this location as a part location.')


class Scrap(models.Model):
    _inherit = 'stock.scrap'
    _description = 'Stock Scrap'

    order_id = fields.Many2one('job.request', 'Job Order')

class Replacement(models.Model):
    _name = 'replace.product.line'

    product_id = fields.Many2one('product.product', string='Origin Product')
    replaced_product_id = fields.Many2one('product.product', string='Replaced Product')
    qty = fields.Float('Replaced Qty')
    uom_id = fields.Many2one('uom.uom')
    desc = fields.Text('Remark')
    job_order_id = fields.Many2one('job.request')
    part_order_id = fields.Many2one('part.order')

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    request_id = fields.Many2one('job.request')
