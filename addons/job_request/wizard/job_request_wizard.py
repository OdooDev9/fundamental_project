from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError
import logging
from itertools import groupby
from operator import itemgetter
import collections

_logger = logging.getLogger(__name__)


class RequestWizard(models.TransientModel):
    _name = 'job.request.unbuild'
    _description = 'Job request unbuild'

    def _get_src_location(self):
        location = self.env['stock.location'].search([('usage', '=', 'production')], limit=1)
        if location:
            return location

    product_id = fields.Many2one('product.product', string="Product")
    location_src_id = fields.Many2one('stock.location', 'Source Location', default=_get_src_location)
    location_dest_id = fields.Many2one(
        'stock.location', 'Products Location',
        help="Location where the system will stock the finished products.",
        domain=[('usage', '=', 'internal'), ('part_location', '=', True)])
    existing_components = fields.One2many('unbuild.components', 'request_id', string="Components")

    @api.model
    def default_get(self, fields):
        res = super(RequestWizard, self).default_get(fields)
        jobs = self.env['job.request'].browse(self._context.get('active_id'))
        dest_location_id = self.env['stock.location'].search(
            [('hr_bu_id', '=', jobs.business_id.id), ('part_location', '=', True)], limit=1)
        components = []
        for line in jobs.move_raw_ids:
            components.append((0, 0, {
                'request_id': self.id,
                'product_id': line.product_id.id,
                'product_uom': line.product_uom.id,
                'product_qty': line.product_uom_qty,
                'product_uom_qty': line.product_uom_qty,
            }))
        res.update({'location_dest_id': dest_location_id.id,
                    'existing_components': components,
                    'product_id': jobs.product_id.id
                    })
        return res

    lot_id = fields.Many2one('stock.production.lot', string='Serial Number', change_default=True)
    bom_line_id = fields.Many2one('mrp.bom.line', 'BoM Line', check_company=True)
    product_uom = fields.Many2one('uom.uom', string="Unit of Measure")
    unit_factor = fields.Float('Unit Factor', default=1)
    date = fields.Datetime('Date', default=fields.Datetime.now, index=True, required=True)

    def unbuild(self):
        jobs = self.env['job.request'].browse(self._context.get('active_id'))
        picking_id = self.env['stock.picking'].search([('job_re_id', '=', jobs.id), ('picking_type_id', '=', jobs.warehouse_id.in_type_id.id),
                                                    ('state', '=', 'done')])
        if not picking_id:
            raise UserError(_("Receipt order first."))
        for line in self.existing_components:
            product_uom_qty = 0.0

            for raw in jobs.move_raw_ids:
                if line.product_id.id == raw.product_id.id:
                    product_uom_qty = raw.product_uom_qty
                    break

            unbuild_id = self.env['job.request.unbuild.line'].create({
                'name': line.product_id.name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.product_qty,
                'original_product_uom_qty': product_uom_qty,
                'product_uom': line.product_id.uom_id.id,
                'raw_material_job_id': jobs.id,
            })

            src_location = self.location_src_id
            des_location = self.location_dest_id

            rental_stock_move = self.env['stock.move'].create({
                'product_id': line.product_id.id,
                'product_uom_qty': line.product_qty,
                'product_uom': line.product_id.uom_id.id,
                'location_id': src_location.id,
                'location_dest_id': des_location.id,
                'partner_id': jobs.partner_id.id,
                'unbuild_line_id': unbuild_id.id,
                'name': _("Rental move :") + " %s" % (unbuild_id.name),
                'state': 'confirmed',
            })

            rental_stock_move._action_assign()
            rental_stock_move._set_quantity_done(line.product_qty)
            rental_stock_move._action_done()
        # FG Move
        fg_stock_move = self.env['stock.move'].create({
            'product_id': self.product_id.id,
            'product_uom_qty': jobs.product_qty,
            'product_uom': self.product_id.uom_id.id,
            'location_id': des_location.id,
            'location_dest_id': src_location.id,
            'partner_id': jobs.partner_id.id,
            'name': _("Finish Product move :") + " %s" % (jobs.name),
            'state': 'confirmed',
        })

        fg_stock_move._action_assign()
        fg_stock_move._set_quantity_done(jobs.product_qty)
        fg_stock_move._action_done()

        jobs.update({'state': 'unbuild'})


class UnbuildComponents(models.TransientModel):
    _name = 'unbuild.components'
    _description = 'Unbuild components'

    request_id = fields.Many2one('job.request.unbuild', string="Request Wizard")
    product_id = fields.Many2one('product.product', string="Product ")
    product_uom = fields.Many2one('uom.uom', string="Unit of Measure")
    product_qty = fields.Float(string="Quantity", digits="Product Unit of Measure")
    product_uom_qty = fields.Float(string='Original Qty', digits='Product Unit of Measure', default=1.0)


class RequestDeliverWizard(models.TransientModel):
    _name = 'job.request.deliver'
    _description = " Job Request Deliver"

    def _get_src_location(self):
        job = self.env['job.request'].browse(self.env.context.get('active_id'))
        location_id = self.env['stock.location'].search([('part_location', '=', True), ('hr_bu_id', '=', job.business_id.id)], limit=1)
        return location_id

    def _get_dest_location(self):
        job = self.env['job.request'].browse(self.env.context.get('active_id'))
        return job.warehouse_id.lot_stock_id.id

    product_id = fields.Many2one('product.product', string="Product")
    location_src_id = fields.Many2one('stock.location', 'Source Location', default=_get_src_location)
    location_dest_id = fields.Many2one('stock.location', 'Destination Location', default=_get_dest_location)

    @api.model
    def default_get(self, fields):
        res = super(RequestDeliverWizard, self).default_get(fields)
        jobs = self.env['job.request'].browse(self._context.get('active_id'))
        res.update({'product_id': jobs.product_id.id})
        return res

    def deliver(self):
        jobs = self.env['job.request'].browse(self._context.get('active_id'))

        src_location = self.location_src_id
        des_location = self.location_dest_id
        rental_stock_move = self.env['stock.move'].create({
            'product_id': self.product_id.id,
            'product_uom_qty': jobs.product_qty,
            'product_uom': self.product_id.uom_id.id,
            'location_id': src_location.id,
            'location_dest_id': des_location.id,
            'partner_id': jobs.partner_id.id,
            'name': _("Finish Product move :") + " %s" % (jobs.name),
            'state': 'confirmed',
            'price_unit':1,
        })

        rental_stock_move._action_assign()
        rental_stock_move._set_quantity_done(jobs.product_qty)
        rental_stock_move._action_done()

        jobs.update({'state': 'ready'})


class RequestBuildWizard(models.TransientModel):
    _name = 'job.request.build'
    _description = 'Job request build'

    def _get_src_location(self):
        job = self.env['job.request'].browse(self.env.context.get('active_id'))
        location_id = self.env['stock.location'].search([('part_location', '=', True), ('hr_bu_id', '=', job.business_id.id)], limit=1)
        return location_id

    def _get_dest_location(self):
        job = self.env['job.request'].browse(self.env.context.get('active_id'))
        location = self.env['stock.location'].search([('usage', '=', 'production')], limit=1)
        return location

    product_id = fields.Many2one('product.product', string="Product")
    location_src_id = fields.Many2one('stock.location', 'Source Location', default=_get_src_location)
    location_dest_id = fields.Many2one(
        'stock.location', 'Products Location',
        help="Location where the system will stock the finished products.", default=_get_dest_location)
    existing_components = fields.One2many('build.components', 'request_id', string="Components")
    part_order_components = fields.One2many('build.part.order.components', 'request_id', string="Part Order Components")
    damage_components = fields.One2many('build.damage.components', 'request_id', string="Damage Components")
    receiving_components = fields.One2many('receiving.part.components', 'request_id', string="Receiving Components")
    production_location_id = fields.Many2one('stock.location', "Production Location",
                                             related='product_id.property_stock_production',
                                             readonly=False)  # FIXME sle: probably wrong if document in another company

    @api.model
    def default_get(self, fields):
        res = super(RequestBuildWizard, self).default_get(fields)
        jobs = self.env['job.request'].browse(self._context.get('active_id'))
        components = []
        receiving_components = []
        part_components = []
        damage_components = []

        for line in jobs.move_raw_ids:
            receiving_components.append((0, 0, {
                'request_id': self.id,
                'product_id': line.product_id.id,
                'product_uom': line.product_uom.id,
                'product_uom_qty': line.product_uom_qty,
            }))

        for line in jobs.move_raw_ids:
            components.append((0, 0, {
                'request_id': self.id,
                'product_id': line.product_id.id,
                'product_uom': line.product_uom.id,
                'product_uom_qty': line.product_uom_qty,
                'product_qty': line.product_uom_qty,
            }))

        if len(jobs.part_order_ids) > 0:
            grouped = collections.defaultdict(list)
            for line in jobs.part_order_ids.order_ids.req_quotation_line:
                grouped[line.product_id].append(line)
            for picking_type, mrp_bom_line in grouped.items():
                if picking_type.type in ['consu', 'product']:
                    product_qty = 0
                    product_uom = False
                    for l in mrp_bom_line:
                        product_qty += l.product_uom_qty
                        product_uom = l.product_uom.id

                    part_components.append((0, 0, {
                        'request_id': self.id,
                        'product_id': picking_type.id,
                        'product_uom': product_uom,
                        'product_uom_qty': product_qty,
                    }))
        product_ids = []
        for line in jobs.move_raw_ids:
            temp1 = 0
            product_ids.append(line.product_id)
            for x in jobs.unbuild_ids:
                if x.product_id.id == line.product_id.id:
                    temp1 += x.product_uom_qty
                    break
            for x in part_components:
                if x[2]['product_id'] == line.product_id.id:
                    temp1 += x[2]['product_uom_qty']
                    break

            for y in jobs.move_raw_ids:
                if y.product_id.id == line.product_id.id:
                    temp1 = temp1 - y.product_uom_qty

            if temp1 < 0:
                temp1 = 0.0

            damage_components.append((0, 0, {
                'request_id': self.id,
                'product_id': line.product_id.id,
                'product_uom': line.product_uom.id,
                'product_uom_qty': temp1,
            }))
        if jobs.replace_ids:
            for replace in jobs.replace_ids:
                if replace.product_id not in product_ids:
                    damage_components.append((0, 0, {
                        'request_id': self.id,
                        'product_id': replace.product_id.id,
                        'product_uom': replace.uom_id.id,
                        'product_uom_qty': replace.qty,
                    }))

        res.update({'receiving_components': receiving_components, 'existing_components': components,
                    'part_order_components': part_components, 'damage_components': damage_components})
        res.update({'product_id': jobs.product_id.id})
        return res

    lot_id = fields.Many2one('stock.production.lot', string='Serial Number', change_default=True)
    bom_line_id = fields.Many2one('mrp.bom.line', 'BoM Line', check_company=True)
    product_uom = fields.Many2one('uom.uom', string="Unit of Measure")
    unit_factor = fields.Float('Unit Factor', default=1)
    date = fields.Datetime('Date', default=fields.Datetime.now, index=True, required=True)

    def build(self):
        jobs = self.env['job.request'].browse(self._context.get('active_id'))

        for part_order in jobs.part_order_ids:
            if not part_order.is_delivered:
                raise UserError(_("Part order %s is not delivered yet!") % (part_order.name))

        for ex in jobs.move_raw_ids:
            count = 0
            for line in jobs.unbuild_ids:
                if ex.product_id.id == line.product_id.id:
                    count += line.product_uom_qty
                    break

            if len(jobs.part_order_ids) > 0:
                grouped = collections.defaultdict(list)
                order_ids = self.env['sale.order'].search([('req_quot_id', '=', jobs.part_order_ids.order_ids.id)])
                for line in order_ids.order_line:
                    grouped[line.product_id].append(line)
                for picking_type, mrp_bom_line in grouped.items():
                    if picking_type.type in ['consu', 'product']:
                        product_qty = 0
                        product_uom = False
                        for l in mrp_bom_line:
                            product_qty += l.product_qty
                            product_uom = l.product_uom.id
                        if ex.product_id.id == picking_type.id:
                            count += product_qty

            if ex.product_uom_qty > count:
                raise UserError(_("Components are not enough yet to build the product! Please order parts!"))

        for line in self.existing_components:
            src_location = self.location_src_id
            des_location = self.location_dest_id
            rental_stock_move = self.env['stock.move'].create({
                    'name': jobs.name,
                    'origin': jobs.name,
                    'company_id': self.env.company.id,
                    'product_id': line.product_id.id,
                    'product_uom': line.product_id.uom_id.id,
                    'state': 'draft',
                    'product_uom_qty': line.product_qty,
                    'location_id': src_location.id,
                    'location_dest_id': des_location.id,
                    'move_line_ids': [(0, 0, {'product_id': line.product_id.id,
                                              'product_uom_id': line.product_uom.id,
                                              'qty_done': line.product_qty,
                                              'location_id': src_location.id,
                                              'location_dest_id': des_location.id, })],
                })
            rental_stock_move._action_done()

        des_location = self.location_dest_id
        rental_stock_move = self.env['stock.move'].create({
            'product_id': self.product_id.id,
            'product_uom_qty': jobs.product_qty,
            'product_uom': self.product_id.uom_id.id,
            'location_id': self.location_dest_id.id,
            'location_dest_id': self.location_src_id.id,
            'partner_id': jobs.partner_id.id,
            'name': _("Finish Product move :") + " %s" % (jobs.name),
            'state': 'confirmed',
        })
        rental_stock_move._action_assign()
        rental_stock_move._set_quantity_done(jobs.product_qty)
        rental_stock_move._action_done()

        # location_dest_id =  self.env['stock.picking.type'].search([('code', '=','internal'),('is_part_order', '=',True),('branch_id', '=',self.env.user.branch_id.id)],limit=1)
        create_damage = False
        for line in self.damage_components:
            if line.product_uom_qty > 0:
                damage_id = self.env['damage.component.line'].create({
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.product_uom_qty,
                    'product_uom': line.product_id.uom_id.id,
                    'raw_material_job_id': jobs.id,
                    'note': line.note,
                })
                create_damage = True
        if create_damage:
            self._create_picking_damage()
        jobs.update({'state': 'build'})

    def _create_picking_damage(self):
        request = self.env['job.request'].browse(self._context.get('active_id'))
        dest_location_id = self.env['stock.location'].search([('hr_bu_id', '=', request.business_id.id), ('scrap_location', '=', True)], limit=1)
        if not dest_location_id:
            dest_location_id = self.env['stock.location'].create({'name': 'Damage',
                                                                  'hr_bu_id': request.business_id.id,
                                                                  'usage': 'internal',
                                                                  'location_id': request.warehouse_id.lot_stock_id.location_id.id,
                                                                  'scrap_location': True, })
        for demage in self.damage_components:
            if demage.product_uom_qty > 0:
                scarp_id = self.env['stock.scrap'].create({'product_id': demage.product_id.id,
                                                           'product_uom_id': demage.product_id.uom_id.id,
                                                           'location_id': self.location_src_id.id,
                                                           'scrap_location_id': dest_location_id.id,
                                                           'scrap_qty': demage.product_uom_qty,
                                                           'order_id': request.id,})
                scarp_id.action_validate()
        return scarp_id


class BuildComponents(models.TransientModel):
    _name = 'build.components'
    _description = 'build components'

    request_id = fields.Many2one('job.request.build', string="Request Wizard")
    product_id = fields.Many2one('product.product', string="Product Component")
    product_uom = fields.Many2one('uom.uom', string="Unit of Measure")
    product_uom_qty = fields.Float(string='Original Qty', digits='Product Unit of Measure', default=0.0)
    product_qty = fields.Float(string='Qty', digits='Product Unit of Measure')


class BuildDamageComponents(models.TransientModel):
    _name = 'build.damage.components'
    _description = 'build components'

    request_id = fields.Many2one('job.request.build', string="Request Wizard")
    product_id = fields.Many2one('product.product', string="Product Component")
    product_uom = fields.Many2one('uom.uom', string="Unit of Measure")
    product_uom_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', default=0.0)
    note = fields.Text('Remark')


class PartOrderComponents(models.TransientModel):
    _name = 'build.part.order.components'
    _description = 'part components'

    request_id = fields.Many2one('job.request.build', string="Reqeuest Wizard")
    product_id = fields.Many2one('product.product', string="Product Component")
    product_uom = fields.Many2one('uom.uom', string="Unit of Measure")
    product_uom_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', default=0.0)


class ReceivingComponents(models.TransientModel):
    _name = 'receiving.part.components'
    _description = 'Receiving Part components'

    request_id = fields.Many2one('job.request.build', string="Reqeuest Wizard")
    product_id = fields.Many2one('product.product', string="Product Component")
    product_uom = fields.Many2one('uom.uom', string="Unit of Measure")
    product_uom_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', default=0.0)


class SaleOrderCreateWizard(models.TransientModel):
    _name = 'order.created.wizard'
    _description = "Order Created Wizard"

    message = fields.Text(String="Sale order has been created!")

class JobOrderClose(models.TransientModel):
    _name = 'job.request.close'

    def _get_src_location(self):
        job = self.env['job.request'].browse(self.env.context.get('active_id'))
        return job.warehouse_id.lot_stock_id.id

    def _get_dest_location(self):
        location_id = self.env['stock.location'].search([('usage', '=', 'customer')], limit=1).id
        return location_id

    product_id = fields.Many2one('product.product', string="Product")
    location_src_id = fields.Many2one('stock.location', 'Source Location', default=_get_src_location)
    location_dest_id = fields.Many2one('stock.location', 'Destination Location', default=_get_dest_location)
    damage = fields.Boolean('Is Damage Transfer', default=True)

    @api.model
    def default_get(self, fields):
        res = super(JobOrderClose, self).default_get(fields)
        jobs = self.env['job.request'].browse(self._context.get('active_id'))
        res.update({'product_id': jobs.product_id.id})
        return res

    def close(self):
        jobs = self.env['job.request'].browse(self._context.get('active_id'))
        jobs.action_done()
        jobs._create_processing_transition()
        if self.damage and jobs.damage_ids:
            self._create_picking(jobs)
        return True

    def _create_picking(self, jobs):
        pick_obj = self.env['stock.picking']
        move_lines = []
        location_src_id = self.env['stock.location'].search([('scrap_location', '=', True), ('hr_bu_id', '=', jobs.business_id.id)], limit=1).id
        for damage in jobs.damage_ids:
            if damage.product_id.type in ['consu', 'product']:
                move_lines.append((0, 0, {
                    'name': damage.product_id.name + '-' + jobs.name,
                    'company_id': jobs.company_id.id,
                    'product_id': damage.product_id.id,
                    'product_uom': damage.product_uom.id,
                    'product_uom_qty': damage.product_uom_qty,
                    'partner_id': jobs.partner_id.id,
                    'location_id': location_src_id,
                    'location_dest_id': self.location_dest_id.id,
                    'origin': jobs.name,
                    'warehouse_id': jobs.warehouse_id.id,
                    'priority': '1',
                }))
        picking = pick_obj.create({
            'partner_id': jobs.partner_id.id,
            'origin': jobs.name,
            'move_type': 'direct',
            'company_id': jobs.company_id.id,
            'move_lines': move_lines,
            'picking_type_id': jobs.warehouse_id.out_type_id.id,
            'location_id': location_src_id,
            'location_dest_id': self.location_dest_id.id,
            'job_re_id': jobs.id,
            'hr_bu_id': jobs.create_uid.current_bu_br_id.id,
            'unit_or_part': 'part',
        })
        picking.action_confirm()
        return picking
