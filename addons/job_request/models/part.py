# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import datetime
from re import L
from odoo import api, fields, models, SUPERUSER_ID, _
# import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError, ValidationError, Warning
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare
from dateutil.relativedelta import relativedelta
from itertools import groupby
from operator import itemgetter
from functools import partial
from odoo.tools.misc import formatLang
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class res_company(models.Model):
    _inherit = "res.company"

    sale_note = fields.Text(string='Sale Default Terms and Conditions', translate=True)


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    part_id = fields.Many2one('part.order', string="Part Order")


class AccountInvoice(models.Model):
    _inherit = 'account.move'

    part_id = fields.Many2one('part.order')
    from_part_order = fields.Boolean(string="Invoice From Part Order")
    job_re_id = fields.Many2one('job.request', 'Job Request')

    def action_approve_service_head(self):
        self.state = 'approved_service_head'

    def action_approve_gm_agm(self):
        self.state = 'approved_gm_agm'

    def invoice_validate(self):
        res = super(AccountInvoice, self).invoice_validate()
        if self.part_id:
            for a in self.invoice_line_ids:
                history_ids = self.env['part.history'].search([('part', '=', self.part_id.id)])
                for hi in history_ids:
                    if hi.production_lot_id_custom.product_id.id == a.product_id.id:
                        hi.invoice_amount = a.price_subtotal
        return res

    def action_app_reman_sale_head(self):
        self.state = 'approved_sale_head'

    def action_app_reman_finance_head(self):
        for rec in self:
            if rec.state == 'approved_sale_head':
                rec.state = 'approved_finance_head'

    def action_app_reman_gm_agm(self):
        for rec in self:
            if rec.state == 'approved_finance_head':
                rec.state = 'approved_gm_agm'


class AccountInvoiceLine(models.Model):
    _inherit = 'account.move.line'
    part_ids = fields.Many2many('part.order.line', string='Part Order Lines', readonly=True, copy=False)


class PartOrder(models.Model):
    _name = "part.order"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _description = "Part Order"
    _order = 'date_order desc, id desc'

    def action_button_close_part(self):
        self.update({'close_date': datetime.datetime.now(), 'state': 'close'})

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'part.order') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('part.order') or _('New')
        result = super(PartOrder, self).create(vals)
        return result

    def _amount_by_group(self):
        for order in self:
            currency = order.company_id.currency_id
            fmt = partial(formatLang, self.with_context(lang=order.partner_id.lang).env, currency_obj=currency)
            res = {}
            for line in order.part_line:
                price_reduce = line.price_unit
                taxes = line.tax_id.compute_all(price_reduce, quantity=line.product_uom_qty, product=line.product_id,
                                                partner=order.partner_shipping_id)['taxes']
                for tax in line.tax_id:
                    group = tax.tax_group_id
                    res.setdefault(group, {'amount': 0.0, 'base': 0.0})
                    for t in taxes:
                        if t['id'] == tax.id or t['id'] in tax.children_tax_ids.ids:
                            res[group]['amount'] += t['amount']
                            res[group]['base'] += t['base']
            res = sorted(res.items(), key=lambda l: l[0].sequence)
            order.amount_by_group = [(
                l[0].name, l[1]['amount'], l[1]['base'],
                fmt(l[1]['amount']), fmt(l[1]['base']),
                len(res),
            ) for l in res]

    @api.depends('part_line.price_total')
    def _amount_all(self):
        """
		Compute the total amounts of the SO.
		"""
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.part_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            for line in order.sale_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_untaxed + amount_tax,
            })

    @api.model
    def _default_warehouse_id(self):
        company = self.env.user.company_id.id
        warehouse_ids = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
        return warehouse_ids

    @api.model
    def _default_note(self):
        return self.env.user.company_id.sale_note

    expired_email_check = fields.Boolean(string="Expired Email Checked", default=False)
    amount_by_group = fields.Binary(string="Tax amount by group", compute='_amount_by_group',
                                    help="type: [(name, amount, base, formated amount, formated base)]")
    name = fields.Char(string='Order Reference', required=True, readonly=True, default='New', copy=False)
    origin = fields.Char(string='Source Document',
                         help="Reference of the document that generated this part orders request.")
    date_order = fields.Datetime(string='Order Date', required=True, readonly=True,
                                 default=fields.Datetime.now)  # ,states={'draft': [('readonly', False)], 'sent': [('readonly', False)]})
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    state = fields.Selection([
        ('draft', 'New'),
        ('approved_production', 'Approved Production Head'),
        ('approved_qa_pic', 'Approved QA PIC'),
        ('confirm', 'Quotation'),
        ('close', 'Closed'),
    ], string='Status', readonly=True, default='draft')
    partner_invoice_id = fields.Many2one('res.partner', string='Invoice Address', required=True,
                                         help="Invoice address for current sales order.")
    partner_shipping_id = fields.Many2one('res.partner', string='Delivery Address', required=True,
                                          help="Delivery address for current sales order.")

    confirmation_date = fields.Datetime('Confirmation Date', readonly=True)

    part_purchase_price = fields.Float(string='Purchase Price')

    client_order_ref = fields.Char(string='Reference')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse',
                                   required=True, default=_default_warehouse_id)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', required=True,
                                   help="Pricelist for current sales order.")
    close_date = fields.Datetime(string='Close Date', readonly=True)
    user_id = fields.Many2one('res.users', string='Salesperson', default=lambda self: self.env.user)
    note = fields.Text('Terms and conditions', default=_default_note)
    sale_line = fields.One2many('sale.part.order.line', 'part_id', string=' Asset Sale Order Line ', copy=False)
    part_line = fields.One2many('part.order.line', 'part_id', string=' Asset Part Line ', copy=False)
    part_serial_line = fields.One2many('asset.serial.wrapper', 'part_id', string='Part Serial Lines', copy=False)
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env['res.company']._company_default_get('part.order'))
    invoice_id = fields.Many2one('account.move', 'Invoice')
    invoice_count = fields.Integer(string='# of Invoices', readonly=True, compute='_get_invoiced')
    invoice_ids = fields.Many2many("account.move", string='Invoices', readonly=True, compute="_get_invoiced")
    procurement_group = fields.Many2one('procurement.group', string="Procurement Group", copy=False)
    amount_untaxed = fields.Float(compute='_amount_all', string='Untaxed Amount', store=True, readonly=True,
                                  track_visibility='onchange')
    amount_tax = fields.Float(compute='_amount_all', string='Taxes', store=True, readonly=True)
    amount_total = fields.Float(compute='_amount_all', string='Total', store=True, readonly=True,
                                track_visibility='always')
    check_saleable = fields.Boolean(string="check saleable product")
    job_ref_id = fields.Many2one('job.request', string="Job Request")
    currency_id = fields.Many2one("res.currency", related='pricelist_id.currency_id', string="Currency", readonly=True,
                                  required=True)
    fiscal_position_id = fields.Many2one(
        'account.fiscal.position', string='Fiscal Position',
        domain="[('company_id', '=', company_id)]", check_company=True,
        help="Fiscal positions are used to adapt taxes and accounts for particular customers or sales orders/invoices."
             "The default value comes from the customer.")
    business_id = fields.Many2one('business.unit', string="Business Unit",
                                  default=lambda self: self.env.user.current_bu_br_id,
                                  domain="[('business_type','=','bu')]")
    note = fields.Text('Remark')
    location_src_id = fields.Many2one('stock.location', 'Source Location')
    location_dest_id = fields.Many2one('stock.location', 'Destination Location')
    picking_type_id = fields.Many2one('stock.picking.type', 'Operation Type')
    is_delivered = fields.Boolean(string="Delivered?", default=False, compute="_compute_is_delivered")
    invoice_created = fields.Boolean(string="Invoice created?", default=False)

    check_availability_finished = fields.Boolean(string="Check Availability Finished", default=False)

    order_ids = fields.One2many('request.quotation', 'part_order_id', string='Transfers')
    sale_order_count = fields.Integer(string='Delivery Orders', compute='_compute_part_order_ids')
    pr_ids = fields.One2many('purchase.quotation', 'part_order_id', string='Purchase Requisition')
    pr_count = fields.Integer(string='Purchase Quotation', compute='_compute_part_order_ids')

    # def _get_order_type(self):
    #     return self.env['sale.order.type'].search([('business_id', '=', False)], limit=1)

    unit_or_part = fields.Selection([('unit', 'Unit'), ('part', 'Spare Part')], string='Units or Parts', default='part')
    replace_ids = fields.One2many('replace.product.line', 'part_order_id', string='Replacement Product')

    def action_approve_production_head(self):
        self.write({'state': 'approved_production'})

    def action_approve_QA(self):
        self.write({'state': 'approved_qa_pic'})

    def replace(self, old, new, desc):
        raw_id = self.part_line.filtered(lambda x: x.product_id == old)
        raw_id.write({'product_id': new.id})
        self.env['replace.product.line'].create({'product_id': old.id,
                                                 'replaced_product_id': new.id,
                                                 'desc': desc,
                                                 'part_order_id': self.id})
        return raw_id

    def action_view_order(self):
        sale_order_ids = self.mapped('order_ids')
        action = self.env.ref('request_quotation.action_request_quotation').read()[0]

        if len(sale_order_ids) > 1:
            action['domain'] = [('id', 'in', sale_order_ids.ids)]
        elif sale_order_ids:
            action['views'] = [(self.env.ref('request_quotation.req_quotation_view_form').id, 'form')]
            action['res_id'] = sale_order_ids.id

        return action

    def action_view_pr(self):
        pr_ids = self.mapped('pr_ids')
        action = self.env.ref('purchase_quotation.action_purchase_quotation').read()[0]

        if len(pr_ids) > 1:
            action['domain'] = [('id', 'in', pr_ids.ids)]
        elif pr_ids:
            action['views'] = [(self.env.ref('purchase_quotation.purchase_quotation_form').id, 'form')]
            action['res_id'] = pr_ids.id

        return action

    def _compute_part_order_ids(self):
        for order in self:
            part_order_id = self.env['request.quotation'].search([('part_order_id', '=', order.id)])
            order.sale_order_count = len(part_order_id)
            part_pr_id = self.env['purchase.quotation'].search([('part_order_id', '=', order.id)])
            order.pr_count = len(part_pr_id)

    def _compute_is_delivered(self):
        # test for delivery
        for rec in self:
            if rec.order_ids:
                for order in self.order_ids:
                    order_id = self.env['sale.order'].search([('req_quot_id', '=', order.id)])
                    if order_id:
                        if order_id.picking_ids:
                            for p in order_id.picking_ids:
                                if p.state == "done":
                                    rec.is_delivered = True
                                else:
                                    rec.is_delivered = False
                        else:
                            rec.is_delivered = False
                    else:
                        rec.is_delivered = False
            else:
                rec.is_delivered = False

    @api.model
    def default_get(self, fields):
        """Method to set default warehouse of user branch."""
        result = super(PartOrder, self).default_get(fields)
        company = self.env.user.company_id.id
        if result.get('business_id', False):
            warehouse_id = self.env['stock.warehouse'].search([
                ('hr_bu_id', '=', result.get('business_id')),
                ('company_id', '=', company)], limit=1)
            result.update({
                'warehouse_id': warehouse_id and warehouse_id.id or False
            })
        return result

    @api.depends('state')
    def _get_invoiced(self):
        for rental in self:
            invoice = self.env['account.move'].search([('part_id', '=', rental.id)])
            rental.update({
                'invoice_count': len(set(invoice)),
                'invoice_ids': invoice.ids,
            })

    def action_view_invoice_part(self):
        invoice_ids = self.mapped('invoice_ids')
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('account.action_move_out_invoice_type')
        list_view_id = imd.xmlid_to_res_id('account.view_invoice_tree')
        form_view_id = imd.xmlid_to_res_id('account.view_move_form')

        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[list_view_id, 'tree'], [form_view_id, 'form']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }
        if len(invoice_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % invoice_ids.ids
        elif len(invoice_ids) == 1:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = invoice_ids.ids[0]
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result

    def action_view_sale_order_line(self):
        sale_order_ids = self.mapped('sale_order_ids')
        action = self.env.ref('sale.action_quotations').read()[0]

        if len(sale_order_ids) > 1:
            action['domain'] = [('id', 'in', sale_order_ids.ids)]
        elif sale_order_ids:
            action['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
            action['res_id'] = sale_order_ids.id

        return action

    def action_view_delivery_part(self):
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        pickings = self.mapped('picking_ids')

        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif pickings:
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = pickings.id
        # Prepare the context.
        return action

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        """
		Update the following fields when the partner is changed:
		- Pricelist
		- Invoice address
		- Delivery address
		"""
        values = {}
        addr = self.partner_id.address_get(['delivery', 'invoice'])
        values = {
            'pricelist_id': self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.id or False,
            'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
            'note': self.with_context(lang=self.partner_id.lang).env.user.company_id.sale_note,
        }
        if self.partner_id.user_id:
            values['user_id'] = self.partner_id.user_id.id
        self.update(values)

    def _create_invoice_with_saleable(self, force=False):
        inv_obj = self.env['account.move']
        inv_line = []
        for part in self:
            for line in part.part_line:
                account_id = False
                if line.product_id.id:
                    account_id = line.product_id.categ_id.property_account_income_categ_id.id
                if not account_id:
                    raise UserError(
                        _('There is no income account defined for this product: "%s". You may have to install a chart of account from Accounting app, settings menu.') % \
                        (line.product_id.name,))
                name = _('Down Payment')
                inv_line.append((0, 0, {
                    'name': line.product_id.name or line.name or " ",
                    'account_id': account_id,
                    'price_unit': line.price_unit,
                    'quantity': line.product_uom_qty,
                    'part_ids': [(6, 0, [line.id])],
                    'product_uom_id': line.product_id.uom_id.id,
                    'product_id': line.product_id.id,
                    'tax_ids': [(6, 0, line.tax_id.ids)],
                }))
            invoice = inv_obj.create({
                'name': part.client_order_ref or part.name or " ",
                'invoice_origin': part.name or " ",
                'type': 'out_invoice',
                'part_id': part.id,
                'ref': False,
                'partner_id': part.partner_invoice_id.id,
                'invoice_line_ids': inv_line,
                'currency_id': part.pricelist_id.currency_id.id,
                'user_id': part.user_id.id,
                'from_part_order': True,
            })
        return invoice

    def _create_picking(self):
        pick_obj = self.env['stock.picking']
        move_lines = []
        for part in self:
            if part.picking_type_id:
                picking_type_id = part.picking_type_id
                location_dest_id = self.env.ref('stock.stock_location_customers').id
            else:
                picking_type_id = self.env['stock.picking.type'].search(
                    [('code', '=', 'internal'), ('is_part_order', '=', True),
                     ('business_id', '=', part.create_uid.hr_bu_id.id)], limit=1)
                location_dest_id = picking_type_id.default_location_dest_id.id
            for line in part.part_line:
                if line.product_id.type in ['consu', 'product']:
                    move_lines.append((0, 0, {
                        'name': part.name,
                        'company_id': part.company_id.id,
                        'product_id': line.product_id.id,
                        'product_uom': line.product_uom.id,
                        'product_uom_qty': line.product_uom_qty,
                        'partner_id': part.partner_id.id,
                        'location_id': picking_type_id.default_location_src_id.id,
                        'location_dest_id': location_dest_id,
                        'origin': part.name,
                        'warehouse_id': picking_type_id.warehouse_id.id,
                        'priority': '1',
                    }))
            picking = pick_obj.create({
                'partner_id': self.env.user.partner_id.id,
                'origin': part.name,
                'move_type': 'direct',
                'company_id': part.company_id.id,
                'move_lines': move_lines,
                'picking_type_id': picking_type_id.id,
                'location_id': picking_type_id.default_location_src_id.id,
                'location_dest_id': location_dest_id,
                'business_id': part.create_uid.hr_bu_id.id,
            })
        return picking

    def action_button_invoice(self):
        for part in self:
            if not part.is_delivered:
                raise UserError(_("You cannot create invoice before products are delivered"))
            invoice = part._create_invoice_with_saleable(force=True)
            part.update({'invoice_id': invoice.id})
            part.update({'invoice_created': True})

    def action_button_confirm_part(self):
        for part in self:
            part.write({
                'confirmation_date': datetime.datetime.now()
            })
            part._create_picking()
            part.state = 'confirm'

    def action_button_check_availability(self):
        self = self.with_context(inventory_mode=True)
        src_location = self.warehouse_id.lot_stock_id
        for part in self.part_line:
            res = self.env['stock.quant'].search(
                [('location_id', '=', src_location.id), ('product_id', '=', part.product_id.id)])

            if res.quantity >= part.product_uom_qty:
                part.update({'check': False})
        if self.part_line:
            line_id = self.part_line.filtered(lambda x: x.check != False)
            if len(line_id) == 0:
                self.check_availability_finished = True

    def action_button_create_quotation(self):
        for part in self:
            order_line = []
            for line in part.part_line:
                order_line.append((0, 0, {
                    'product_id': line.product_id.id,
                    'price_unit': line.price_unit,
                    'product_uom': line.product_uom.id,
                    'product_uom_qty': line.product_uom_qty,
                    'name': 'Job sales order line',
                    'tax_id': line.tax_id,
                }))
            sale_order = self.env['request.quotation'].create({
                'partner_id': part.partner_id.id,
                'hr_bu_id': part.business_id.id,
                'company_id': part.company_id.id,
                'user_id': part.user_id.id,
                'is_job_request': True,
                'req_quotation_line': order_line,
                'part_order_id': part.id,
                'job_order_id': part.job_ref_id.id,
                'unit_or_part': part.unit_or_part,
                'pr_information': part.name,
                'reman': True,
                'warehouse_id': part.warehouse_id.id,
            })
            part.write({'state': 'confirm'})
        return True

    def action_create_pr(self):
        for part in self:
            order_line = []
            for line in part.part_line:
                if line.check:
                    order_line.append((0, 0, {
                        'date_planned': datetime.datetime.today(),
                        'product_id': line.product_id.id,
                        'product_uom': line.product_id.uom_id.id,
                        'price_unit': line.price_unit,
                        'product_qty': line.product_uom_qty - line.balance,
                        'name': 'Job purchase quotation line',
                        'taxes_id': line.tax_id
                    }))
            po = self.env['purchase.quotation'].create({
                'partner_id': part.partner_id.id,
                'hr_bu_id': part.business_id.id,
                'company_id': part.company_id.id,
                'user_id': part.user_id.id,
                'order_line': order_line,
                'part_order_id': part.id,
                'unit_or_part': 'part' if part.unit_or_part == 'part' else 'unit',
                'picking_type_id': part.warehouse_id.in_type_id.id,
            })
        return po


class SalePartOrderLine(models.Model):
    _name = "sale.part.order.line"
    _description = 'Sale Part Order Line'
    _order = 'part_id desc, sequence, id'

    part_id = fields.Many2one('part.order', string='Part Reference', required=True, ondelete='cascade', index=True,
                              copy=False)
    name = fields.Text(string='Description')
    sequence = fields.Integer(string='Sequence', default=10)
    product_categ_id = fields.Many2one('product.category', related="product_id.categ_id", string='Product Category')
    product_id = fields.Many2one('product.product', string='Product', domain=[('sale_ok', '=', True)])
    product_uom_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', default=1.0)
    price_unit = fields.Float('Price Unit', related="product_id.lst_price", required=True, digits='Product Price',
                              default=0.0)
    lot_id = fields.Many2one('stock.production.lot', string='Serial Number', change_default=True)
    invoice_lines = fields.Many2many('account.move.line', string='Invoice Lines', copy=False)
    tax_id = fields.Many2many('account.tax', string='Taxes',
                              domain=[('type_tax_use', '!=', 'none'), '|', ('active', '=', False),
                                      ('active', '=', True)])
    price_subtotal = fields.Float(compute='_compute_amount', string='Subtotal', readonly=True, store=True)
    price_tax = fields.Float(compute='_compute_amount', string='Price Taxes', readonly=True, store=True)
    price_total = fields.Float(compute='_compute_amount', string='Total', readonly=True, store=True)

    @api.depends('price_unit', 'tax_id')
    def _compute_amount(self):
        """
		Compute the amounts of the SO line.
		"""
        for line in self:
            taxes = line.tax_id.compute_all(line.price_unit)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'] * line.product_uom_qty,
                'price_subtotal': taxes['total_excluded'] * line.product_uom_qty,
            })


class RantalOrderLine(models.Model):
    _name = 'part.order.line'
    _description = 'Part Order Line'
    _order = 'part_id desc, sequence, id'

    part_id = fields.Many2one('part.order', string='Part Reference', required=True, ondelete='cascade', index=True,
                              copy=False)
    name = fields.Text(string='Description')
    sequence = fields.Integer(string='Sequence', default=10)
    product_categ_id = fields.Many2one('product.category', string='Product Category')
    product_id = fields.Many2one('product.product', string='Product')
    product_uom_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', default=1.0)
    price_unit = fields.Float('Price Unit', required=True, digits='Product Price', default=0.0)
    lot_id = fields.Many2one('stock.production.lot', string='Serial Number', change_default=True)
    invoice_lines = fields.Many2many('account.move.line', string='Invoice Lines', copy=False)
    tax_id = fields.Many2many('account.tax', string='Taxes',
                              domain=[('type_tax_use', '!=', 'none'), '|', ('active', '=', False),
                                      ('active', '=', True)])
    price_subtotal = fields.Float(compute='_compute_amount', string='Subtotal', readonly=True, store=True)
    price_tax = fields.Float(compute='_compute_amount', string='Price Taxes', readonly=True, store=True)
    price_total = fields.Float(compute='_compute_amount', string='Total', readonly=True, store=True)
    product_uom = fields.Many2one('uom.uom', string="Unit of Measure")
    currency_id = fields.Many2one(related='part_id.currency_id', depends=['part_id'], store=True, string='Currency',
                                  readonly=True)
    discount = fields.Float(string='Discount (%)', digits='Discount', default=0.0)

    qty_delivered = fields.Float(string="Deliverd", digits="Qty Delivered", default="0.0")
    check = fields.Boolean(default=True)
    balance = fields.Float('Stock Balance', compute='compute_stock_balance')

    def compute_stock_balance(self):
        for rec in self:
            res = self.env['stock.quant'].search(
                [('location_id', '=', rec.part_id.warehouse_id.lot_stock_id.id),
                 ('product_id', '=', rec.product_id.id)])
            rec.balance = res.quantity

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(price, line.part_id.currency_id, line.product_uom_qty,
                                            product=line.product_id, partner=line.part_id.partner_shipping_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

    @api.onchange('lot_id')
    def lot_id_change(self):
        vals = {}

        if not self.lot_id:
            return self.update(vals)

        product = self.lot_id.product_id
        name = product.name_get()[0][1]
        vals['name'] = name

        vals.update({'product_id': product or False,
                     'product_categ_id': product.categ_id or False,
                     'price_unit': product.list_price or 0.0,
                     })
        return self.update(vals)

    # MPT Start
    # def action_part_replace_product(self):
    #     print("Button Clicked!!")
    #
class PartOrderReplaceLine(models.Model):
    _inherit = 'part.order.line'
    def action_part_replace_product(self):
        action = self.env.ref('job_request.part_replace_view').read()[0]
        action['context'] = {'part_line_id': self.id}
        return action

class ProcurementRule(models.Model):
    _inherit = 'stock.rule'

    def _get_stock_move_values(self, product_id, product_qty, product_uom, location_id, name, origin, values, group_id):
        res = super(ProcurementRule, self)._get_stock_move_values(product_id, product_qty, product_uom, location_id,
                                                                  name, origin, values, group_id)
        if res.get('part_line_id', False):
            res['part_line_id'] = values['part_line_id']
            res['for_part_move'] = True
        return res


class StockMove(models.Model):
    _inherit = "stock.move"

    part_line_id = fields.Many2one('part.order.line', 'Part Line')
    for_part_move = fields.Boolean("stock move for part")

    # def _action_done(self, cancel_backorder=False):
    #     # res = super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)

    #     print('override action done**********************',self)
    #     print(self.picking_id.job_re_id.id)
    #     # Init a dict that will group the moves by valuation type, according to `move._is_valued_type`.
    #     valued_moves = {valued_type: self.env['stock.move'] for valued_type in self._get_valued_types()}
    #     for move in self:
    #         if float_is_zero(move.quantity_done, precision_rounding=move.product_uom.rounding):
    #             continue
    #         for valued_type in self._get_valued_types():
    #             if getattr(move, '_is_%s' % valued_type)():
    #                 valued_moves[valued_type] |= move

    #     # AVCO application
    #     valued_moves['in'].product_price_update_before_done()

    #     # res = super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)
    #     # print(res,'/////resssssssssssssssssssssssssss')

    #     # '_action_done' might have created an extra move to be valued
    #     for move in self:
    #         for valued_type in self._get_valued_types():
    #             if getattr(move, '_is_%s' % valued_type)():
    #                 valued_moves[valued_type] |= move

    #     stock_valuation_layers = self.env['stock.valuation.layer'].sudo()
    #     # Create the valuation layers in batch by calling `moves._create_valued_type_svl`.
    #     for valued_type in self._get_valued_types():
    #         todo_valued_moves = valued_moves[valued_type]
    #         if todo_valued_moves:
    #             todo_valued_moves._sanity_check_for_valuation()
    #             stock_valuation_layers |= getattr(todo_valued_moves, '_create_%s_svl' % valued_type)()

    #     if self.picking_id.job_request == False:

    #         print(self.picking_id.job_re_id,'Job Request No')
    #         stock_valuation_layers._validate_accounting_entries()

    #         stock_valuation_layers._validate_analytic_accounting_entries()

    #         stock_valuation_layers._check_company()

    #         # For every in move, run the vacuum for the linked product.
    #         products_to_vacuum = valued_moves['in'].mapped('product_id')
    #         company = valued_moves['in'].mapped('company_id') and valued_moves['in'].mapped('company_id')[0] or self.env.company
    #         for product_to_vacuum in products_to_vacuum:
    #             product_to_vacuum._run_fifo_vacuum(company)

    #     return super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)


class AssetSerialWrapper(models.Model):
    _name = 'asset.serial.wrapper'
    _description = 'Asset Serial Wrapper'

    part_id = fields.Many2one('part.order', string='Part Reference', )
    product_id = fields.Many2one('product.product', string='Product', required=True)
    lot_id = fields.Many2one('stock.production.lot', string='Serial Number', change_default=True)


class PickingType(models.Model):
    _inherit = "stock.picking.type"

    is_part_order = fields.Boolean("Is Part Order?", default=False)
    is_remanufacturing = fields.Boolean("Is Remanufacturing Finished?", default=False)


class SaleOrder(models.Model):
    _inherit = 'request.quotation'

    is_job_request = fields.Boolean("Is Job Request", default=False)
    pr_information = fields.Char("PR Information")
    lead_time = fields.Char("Lead Time")
    part_order_id = fields.Many2one('part.order', string='part Ref', readonly=True, copy=False)
    job_order_id = fields.Many2one('job.request', string='Job Ref', readonly=True, copy=False)
    reman = fields.Boolean()
    state = fields.Selection(
        selection_add=[('approved_gm_agm', 'Approved GM/AGM'), ('approved_sale_head', 'Approved Sale Head')])

    def action_approve_sale_head(self):
        if self.reman == True:
            self.write({'state': 'approved_sale_head'})

    def action_approve_gm_agm(self):
        if self.reman == True:
            self.write({'state': 'approved_gm_agm'})
            return self._create_sale_order()

    def action_approve(self):
        if not self.req_quotation_line:
            raise UserError(_("Order Line doesn't exit"))
        self.write({'state': 'approved_sale_admin'})
        # quots = self.filtered(lambda s: s.state in ['draft'])
        # print("lfmdsk;sdf")
        if self.reman == False:
            return self._create_sale_order()
        if self.reman == True and self.unit_or_part == 'part':
            return self._create_sale_order()

    def _create_sale_order(self):
        sale_obj = self.env['sale.order']

        for request in self:
            request_lines = []
            for line in request.req_quotation_line:
                request_lines.append((0, 0, {
                    'display_type': line.display_type,
                    'product_id': line.product_id.id,
                    'name': line.name,
                    'product_uom': line.product_uom.id,
                    'product_uom_qty': line.product_uom_qty,
                    'price_unit': line.price_unit,
                    'tax_id': line.tax_id,
                    'discount_value': line.discount_value,
                    'br_dis_value': line.br_dis_value,
                    'production_delivery_date': line.delivery_date,
                    'estimated_delivery': line.estimated_delivery,

                }))

            request_new = sale_obj.create({
                # 'name': number,
                'req_quot_id': request.id,
                'date_order': request.date_order,
                'payment_term_id': request.payment_term_id.id,
                'hr_br_id': request.hr_br_id.id,
                'hr_bu_id': request.hr_bu_id.id,
                'partner_id': request.partner_id.id,
                'user_id': request.user_id.id,
                'team_id': request.team_id.id,
                'discount_type': request.discount_type,
                'discount_view': request.discount_view,
                'discount_value': request.discount_value,
                'br_discount': request.br_discount,
                'unit_or_part': request.unit_or_part,
                'order_line': request_lines,
                'reman': request.reman,
                'note': request.note,
                'pricelist_id': request.pricelist_id.id,
                'warehouse_id': request.warehouse_id.id,


            })
            # print("&"*10)
            request_new._onchange_installment_plan_id()
            request_new.compute_installment()
            # self.write({'state': 'approved_sale_admin'})
            return request_new


class SaleQuotationLine(models.Model):
    _inherit = 'request.quotation.line'

    def action_replace_product(self):
        action = self.env.ref('job_request.sale_replace_view').read()[0]
        action['context'] = {'sale_order_line_id': self.id}
        return action


class PurchaseQuotation(models.Model):
    _inherit = 'purchase.quotation'
    _description = 'Purchase Quotation'

    part_order_id = fields.Many2one('part.order', string='part Ref', readonly=True, copy=False)


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    _description = 'Sale Order'

    reman = fields.Boolean()

    def action_sale_head(self):
        for rec in self:
            if rec.reman == True:
                rec.state = 'approved_sale_head'

    def action_finance_pic_approve(self):
        self.state = 'approved_finance_pic'

    def action_new_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        return res

    def _prepare_invoice(self):
        """Overridden this method to update branch_id in move(Invoice Vals)."""
        self.ensure_one()
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals.update({
            'hr_bu_id': self.hr_bu_id.id,
            'hr_br_id': self.hr_br_id.id,
            'service_type': self.service_type or False,
            'unit_or_part': self.unit_or_part,

        })
        if self.reman == True:
            invoice_vals.update({
                'from_part_order': True,
            })
        else:

            invoice_vals.update({
                'from_part_order': False,
            })

        return invoice_vals


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    reman_in_out = fields.Boolean()
    job_re_id = fields.Many2one('job.request', string='job Ref', readonly=True, copy=False)
    for_part_move = fields.Boolean("stock move for part")
    job_request = fields.Boolean('Job Request')

    def button_validate(self):
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

        if not self._should_show_transfers():
            if pickings_without_moves:
                raise UserError(_('Please add some items to move.'))
            if pickings_without_quantities:
                raise UserError(self._get_without_quantities_error_message())
            if pickings_without_lots:
                raise UserError(_('You need to supply a Lot/Serial number for products %s.') % ', '.join(
                    products_without_lots.mapped('display_name')))
        else:
            message = ""
            if pickings_without_moves:
                message += _('Transfers %s: Please add some items to move.') % ', '.join(
                    pickings_without_moves.mapped('name'))
            if pickings_without_quantities:
                message += _(
                    '\n\nTransfers %s: You cannot validate these transfers if no quantities are reserved nor done. To force these transfers, switch in edit more and encode the done quantities.') % ', '.join(
                    pickings_without_quantities.mapped('name'))
            if pickings_without_lots:
                message += _('\n\nTransfers %s: You need to supply a Lot/Serial number for products %s.') % (
                ', '.join(pickings_without_lots.mapped('name')),
                ', '.join(products_without_lots.mapped('display_name')))
            if message:
                raise UserError(message.lstrip())

        # Run the pre-validation wizards. Processing a pre-validation wizard should work on the
        # moves and/or the context and never call `_action_done`.
        if not self.env.context.get('button_validate_picking_ids'):
            self = self.with_context(button_validate_picking_ids=self.ids)
        res = self._pre_action_done_hook()
        if res is not True:
            return res

        # Call `_action_done`.
        if self.env.context.get('picking_ids_not_to_backorder'):
            pickings_not_to_backorder = self.browse(self.env.context['picking_ids_not_to_backorder'])
            pickings_to_backorder = self - pickings_not_to_backorder
        else:
            pickings_not_to_backorder = self.env['stock.picking']
            pickings_to_backorder = self
        pickings_not_to_backorder.with_context(cancel_backorder=True)._action_done()
        pickings_to_backorder.with_context(cancel_backorder=False)._action_done()

        if self.user_has_groups('stock.group_reception_report') \
                and self.user_has_groups('stock.group_auto_reception_report') \
                and self.filtered(lambda p: p.picking_type_id.code != 'outgoing'):
            lines = self.move_lines.filtered(lambda
                                                 m: m.product_id.type == 'product' and m.state != 'cancel' and m.quantity_done and not m.move_dest_ids)
            if lines:
                # don't show reception report if all already assigned/nothing to assign
                wh_location_ids = self.env['stock.location']._search(
                    [('id', 'child_of', self.picking_type_id.warehouse_id.view_location_id.id),
                     ('usage', '!=', 'supplier')])
                if self.env['stock.move'].search([
                    ('state', 'in', ['confirmed', 'partially_available', 'waiting', 'assigned']),
                    ('product_qty', '>', 0),
                    ('location_id', 'in', wh_location_ids),
                    ('move_orig_ids', '=', False),
                    ('picking_id', 'not in', self.ids),
                    ('product_id', 'in', lines.product_id.ids)], limit=1):
                    action = self.action_view_reception_report()
                    action['context'] = {'default_picking_ids': self.ids}
                    return action
        if picking.sale_id.reman:
            dest_location = self.env['stock.location'].search(
                [('part_location', '=', True), ('hr_bu_id', '=', self.hr_bu_id.id)])
            for move in picking.move_ids_without_package:
                part_sale_move_id = self.env['stock.move'].create({
                    'product_id': move.product_id.id,
                    'product_uom_qty': move.quantity_done,
                    'product_uom': move.product_id.uom_id.id,
                    'location_id': self.env['stock.location'].search([('usage', '=', 'production')], limit=1).id,
                    'location_dest_id': dest_location.id,
                    'partner_id': picking.partner_id.id,
                    'name': "Part Sale move",
                    'state': 'confirmed',
                })
                part_sale_move_id._action_assign()
                part_sale_move_id._set_quantity_done(move.quantity_done)
                part_sale_move_id._action_done()

        return True
