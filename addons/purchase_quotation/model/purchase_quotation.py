from datetime import datetime, time
from dateutil.relativedelta import relativedelta
from functools import partial
from itertools import groupby
import json

from markupsafe import escape, Markup
from pytz import timezone, UTC
from werkzeug.urls import url_encode
from datetime import timedelta
from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang, format_amount
from odoo.addons.purchase.models.purchase import PurchaseOrder as Purchase


class PurchaseQuotation(models.Model):
    _name = "purchase.quotation"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _description = "Purchase Order"
    _order = 'id desc'

    def _set_bu_domain(self):
        domain = [('id', 'in', [bu.id for bu in self.env.user.hr_bu_ids])]
        return domain

    @api.model
    def default_get(self, fields):
        """Overriden default get to set warehouse picking."""
        result = super(PurchaseQuotation, self).default_get(fields)
        type_obj = self.env['stock.picking.type']
        company_id = self.env.user and self.env.user.company_id and \
                     self.env.user.company_id.id or False
        hr_bu_id = self.hr_bu_id.id
        types = type_obj.search([('code', '=', 'incoming'),
                                 ('warehouse_id.company_id', '=', company_id),
                                 ('hr_bu_id', '=', hr_bu_id)], limit=1)
        result.update({'picking_type_id': types and types.id or False})
        return result

    @api.depends('order_line.price_total')
    def _amount_all(self):
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                line._compute_amount()
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            currency = order.currency_id or order.partner_id.property_purchase_currency_id or self.env.company.currency_id
            order.update({
                'amount_untaxed': currency.round(amount_untaxed),
                'amount_tax': currency.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax,
            })

    @api.model
    def _get_bu(self):
        return self.env.user.current_bu_br_id

    READONLY_STATES = {
        'purchase': [('readonly', True)],
        'done': [('readonly', True)],
        'cancel': [('readonly', True)],
    }

    name = fields.Char('Order Reference', required=True, index=True, copy=False, default='New')
    priority = fields.Selection(
        [('0', 'Normal'), ('1', 'Urgent')], 'Priority', default='0', index=True)
    origin = fields.Char('Source Document', copy=False,
                         help="Reference of the document that generated this purchase order "
                              "request (e.g. a sales order)")
    partner_ref = fields.Char('Vendor Reference', copy=False,
                              help="Reference of the sales order or bid sent by the vendor. "
                                   "It's used to do the matching when you receive the "
                                   "products as this reference is usually written on the "
                                   "delivery order sent by your vendor.")
    date_order = fields.Datetime('Order Deadline', required=True, states=READONLY_STATES, index=True, copy=False,
                                 default=fields.Datetime.now,
                                 help="Depicts the date within which the Quotation should be confirmed and converted into a purchase order.")
    date_approve = fields.Datetime('Confirmation Date', readonly=1, index=True, copy=False)
    partner_id = fields.Many2one('res.partner', string='Vendor', required=True, states=READONLY_STATES,
                                 change_default=True, tracking=True,
                                 domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
                                 help="You can find a vendor by its Name, TIN, Email or Internal Reference.")
    dest_address_id = fields.Many2one('res.partner',
                                      domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
                                      string='Dropship Address', states=READONLY_STATES,
                                      help="Put an address if you want to deliver directly from the vendor to the customer. "
                                           "Otherwise, keep empty to deliver to your own company.")

    discount_view = fields.Selection([('doc_discount', 'Document Discount'), ('line_discount', 'Line Discount')],
                                     string='Discount Type')

    discount_type = fields.Selection([('fixed', 'Fixed'), ('percentage', 'Percentage')], string='Discount Method')
    discount_value = fields.Float(string='Discount Value')
    discounted_amount = fields.Float(string='Discounted Amount', readonly=True, compute='disc_amount')

    currency_id = fields.Many2one('res.currency', 'Currency', required=True, states=READONLY_STATES,
                                  default=lambda self: self.env.company.currency_id.id)
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all')

    state = fields.Selection([
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('approved_inventory_head', 'Approved Inventory Head'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)
    order_line = fields.One2many('purchase.quotation.line', 'quotation_id', string='Order Lines',
                                 states={'cancel': [('readonly', True)], 'done': [('readonly', True)]}, copy=True)
    notes = fields.Html('Terms and Conditions')
    order_ids = fields.One2many('purchase.order', 'purchase_id', string='Sale Orders')
    date_planned = fields.Datetime(
        string='Receipt Date', index=True, copy=False, compute='_compute_date_planned', store=True, readonly=False,
        help="Delivery date promised by vendor. This date is used to determine expected arrival of products.")
    date_calendar_start = fields.Datetime(compute='_compute_date_calendar_start', readonly=True, store=True)
    payment_term_id = fields.Many2one('account.payment.term', 'Payment Terms',
                                      domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    incoterm_id = fields.Many2one('account.incoterms', 'Incoterm', states={'done': [('readonly', True)]},
                                  help="International Commercial Terms are a series of predefined commercial terms used in international transactions.")

    product_id = fields.Many2one('product.product', related='order_line.product_id', string='Product')
    user_id = fields.Many2one(
        'res.users', string='Purchase Representative', index=True, tracking=True,
        default=lambda self: self.env.user, check_company=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, states=READONLY_STATES,
                                 default=lambda self: self.env.company.id)
    currency_rate = fields.Float("Currency Rate", compute='_compute_currency_rate', compute_sudo=True, store=True,
                                 readonly=True,
                                 help='Ratio between the purchase order currency and the company currency')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all')

    hr_bu_id = fields.Many2one('business.unit', string='Business Unit', required=True, default=_get_bu,
                               domain=_set_bu_domain)
    purchase_order_count = fields.Integer(string="Purchase Order Count", compute='_compute_purchase_order_ids')

    invoice_status = fields.Selection([
        ('no', 'Nothing to Bill'),
        ('to invoice', 'Waiting Bills'),
        ('invoiced', 'Fully Billed'),
    ], string='Billing Status', compute='_get_invoiced', store=True, readonly=True, copy=False, default='no')

    mail_reminder_confirmed = fields.Boolean("Reminder Confirmed", default=False, readonly=True, copy=False,
                                             help="True if the reminder email is confirmed by the vendor.")
    mail_reception_confirmed = fields.Boolean("Reception Confirmed", default=False, readonly=True, copy=False,
                                              help="True if PO reception is confirmed by the vendor.")

    receipt_reminder_email = fields.Boolean('Receipt Reminder Email', related='partner_id.receipt_reminder_email',
                                            readonly=False)
    reminder_date_before_receipt = fields.Integer('Days Before Receipt',
                                                  related='partner_id.reminder_date_before_receipt', readonly=False)
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position',
                                         domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    tax_country_id = fields.Many2one(
        comodel_name='res.country',
        compute='_compute_tax_country_id',
        # Avoid access error on fiscal position, when reading a purchase order with company != user.company_ids
        compute_sudo=True,
        help="Technical field to filter the available taxes depending on the fiscal country and fiscal position.")

    tax_totals_json = fields.Char(compute='_compute_tax_totals_json')
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all',
                                     tracking=True)
    purchase_order_type = fields.Selection(
        [('stock', 'Stock Order Type'), ('customer', 'Customer Order Type'), ('emergency', 'Emergency Order Type'),
         ('tender', 'Tender Order Type'), ('management', 'Management Order Type')], default='stock',
        string="Purchase Order Type", required=True)
    shipping_method = fields.Selection([('air', 'Air'), ('sea', 'Sea'), ('landed', 'Landed')], string="Shipping Method")
    ref_no = fields.Char(string='Reference No')
    attached_file = fields.Binary(string="Attached File")
    file_name = fields.Char('File Name')
    unit_or_part = fields.Selection([('unit', 'Unit'), ('part', 'Spare Part')], string='Unit Or Part', default="part")
    is_oversea_purchase = fields.Boolean('Is Oversea Purchase')
    picking_type_id = fields.Many2one('stock.picking.type', 'Deliver To', states=Purchase.READONLY_STATES,
                                      required=True,
                                      domain="['|', ('warehouse_id', '=', False), ('warehouse_id.company_id', '=', company_id)]",
                                      help="This will determine operation type of incoming shipment")
    prepayment_id = fields.Many2one('account.payment')

    deliver_id = fields.Many2one('stock.picking')
    saleorder_id = fields.Many2one('sale.order')
    conditional = fields.Selection(
        [('storage', 'Shortage'), ('warranty', 'Warranty'), ('engine', 'Engine'),
         ('breakdown', 'Breakdown')], string="Conditional", required=True)

    # YZO Add onchange('is_oversea_purchase')
    @api.onchange('is_oversea_purchase')
    def _onchange_is_oversea_purchase(self):
        if self.is_oversea_purchase:
            self.partner_id = False
            return {'domain': {'partner_id': [('id', 'in', [vendor_id.id for vendor_id in
                                                            self.env['res.partner'].search(
                                                                [('oversea_supplier', '=', True)])])]}}
        else:
            self.partner_id = False
            return {'domain': {'partner_id': [('id', 'in', [vendor_id.id for vendor_id in
                                                            self.env['res.partner'].search(
                                                                [('supplier', '=', True)])])]}}

    @api.onchange('unit_or_part')
    def _onchange_unit_part(self):
        self.order_line = False

    @api.onchange('hr_bu_id')
    def _onchange_hr_bu(self):
        """Onchange method to update the picking type in purchase order."""
        type_obj = self.env['stock.picking.type']
        company_id = self.env.user and self.env.user.company_id and \
                     self.env.user.company_id.id or False
        for purchase in self:
            hr_bu_id = purchase.hr_bu_id and purchase.hr_bu_id.id or False
            types = type_obj.search([
                ('code', '=', 'incoming'),
                ('warehouse_id.company_id', '=', company_id),
                ('hr_bu_id', '=', hr_bu_id)], limit=1)
            purchase.picking_type_id = types and types.id or False
            purchase.order_line = False

    @api.depends('order_line.taxes_id', 'order_line.price_subtotal', 'amount_total', 'amount_untaxed')
    def _compute_tax_totals_json(self):
        def compute_taxes(order_line):
            return order_line.taxes_id._origin.compute_all(**order_line._prepare_compute_all_values())

    def button_approve(self, force=False):
        self = self.filtered(lambda order: order._approval_allowed())
        self.write({'state': 'purchase', 'date_approve': fields.Datetime.now()})
        self.filtered(lambda p: p.company_id.po_lock == 'lock').write({'state': 'done'})
        return {}

    def button_draft(self):
        self.write({'state': 'draft'})
        return {}

    def action_inventory_head(self):
        if not self.order_line:
            raise UserError(_("Order Line doesn't exit"))
        self.state = 'approved_inventory_head'

    def action_confirm(self):
        if not self.order_line:
            raise UserError(_("Order Line doesn't exit"))
        self._create_purchase_order()

    def _approval_allowed(self):
        """Returns whether the order qualifies to be approved by the current user"""
        self.ensure_one()
        return (
                self.company_id.po_double_validation == 'one_step'
                or (self.company_id.po_double_validation == 'two_step'
                    and self.amount_total < self.env.company.currency_id._convert(
                    self.company_id.po_double_validation_amount, self.currency_id, self.company_id,
                    self.date_order or fields.Date.today()))
                or self.user_has_groups('purchase.group_purchase_manager'))

    def button_cancel(self):
        for order in self:
            for inv in order.order_ids:
                if inv and inv.state not in ('cancel', 'draft'):
                    raise UserError(
                        _("Unable to cancel this purchase order. You must first cancel the related vendor bills."))

        self.write({'state': 'cancel', 'mail_reminder_confirmed': False})

    def button_unlock(self):
        self.write({'state': 'draft'})

    def button_done(self):
        self.write({'state': 'done', 'priority': '0'})

    def _create_purchase_order(self):
        purchase_obj = self.env['purchase.order']

        for request in self:
            request_lines = []
            for line in request.order_line:
                if line.product_id.type in ['consu', 'product']:
                    request_lines.append((0, 0, {
                        'product_id': line.product_id.id,
                        'product_uom': line.product_uom.id,
                        'product_qty': line.product_qty,
                        'price_unit': line.price_unit,
                        'taxes_id': line.taxes_id,
                        'discount_value': line.discount_value,
                    }))
            request_new = purchase_obj.create({
                'purchase_id': request.id,
                'partner_ref': request.partner_ref,
                'currency_id': request.currency_id.id,
                'date_order': request.date_order,
                'hr_bu_id': request.hr_bu_id.id,
                'partner_id': request.partner_id.id,
                'user_id': request.user_id.id,
                'purchase_order_type': request.purchase_order_type,
                'ref_no': request.ref_no,
                'attached_file': request.attached_file,
                'file_name': request.file_name,
                'shipping_method': request.shipping_method,
                'unit_or_part': request.unit_or_part,
                'order_line': request_lines,
                'picking_type_id': request.picking_type_id.id,
                'is_oversea_purchase': request.is_oversea_purchase,
                'origin': request.origin,
                'notes': request.notes,
                'payment_term_id': request.payment_term_id.id,
                'discount_type': request.discount_type,
                'discount_view': request.discount_view,
                'discount_value': request.discount_value,
                'date_planned': request.date_planned,

            })
            self.write({'state': 'done', 'date_approve': fields.Datetime.now()})

            # request_new.activity_update()
        return True

    @api.depends('order_line.price_total', 'discount_value')
    def _amount_all(self):
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                line._compute_amount()
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            currency = order.currency_id or order.partner_id.property_purchase_currency_id or self.env.company.currency_id
            order.update({
                'amount_untaxed': currency.round(amount_untaxed),
                'amount_tax': currency.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax #SLO Update
            })

    @api.depends('order_line.price_subtotal', 'discount_type')
    def disc_amount(self):
        val = amount_to_dis = 0.0

        for rec in self:
            for line in rec.order_line:
                val += line.price_tax
            if rec.discount_view == 'doc_discount':
                if rec.discount_type == 'fixed':
                    rec.discounted_amount = rec.discount_value
                elif rec.discount_type == 'percentage':
                    amount_to_dis = (rec.amount_untaxed + val) * (rec.discount_value / 100)
                    rec.discounted_amount = amount_to_dis
                else:
                    rec.discounted_amount = 0.0

            else:
                rec.discounted_amount = 0.0
            rec._amount_all()
    #SLO start
    @api.onchange( 'discount_type')
    def onchange_discount_type(self):
        for rec in self:
            rec.discount_value = 0.0
            rec.discounted_amount = 0.0
            for line in rec.order_line:
                line._compute_amount()

    @api.onchange('discount_view')
    def onchange_discount(self):
        for rec in self:
            rec.discount_value = 0.0
            rec.discounted_amount = 0.0
            for line in rec.order_line:
                line.discount_value = 0.0
                line._compute_amount()

    @api.onchange('discount_value','order_line')
    def onchange_discount_value(self):
        if self.discount_value > 0.0:
            for rec in self.order_line:
                rec.discount_value = self.discount_value
    #SLO end

    def _compute_purchase_order_ids(self):
        print(':::::::::::::')
        requests = []
        for order in self:
            request_ids = self.env['purchase.order'].search([('purchase_id', '=', order.id)])
            order.purchase_order_count = len(request_ids)

    def _prepare_supplier_info(self, partner, line, price, currency):
        # Prepare supplierinfo data when adding a product
        return {
            'name': partner.id,
            'sequence': max(line.product_id.seller_ids.mapped('sequence')) + 1 if line.product_id.seller_ids else 1,
            'min_qty': 0.0,
            'price': price,
            'currency_id': currency.id,
            'delay': 0,
        }

    def _add_supplier_to_product(self):
        # Add the partner in the supplier list of the product if the supplier is not registered for
        # this product. We limit to 10 the number of suppliers for a product to avoid the mess that
        # could be caused for some generic products ("Miscellaneous").
        for line in self.order_line:
            # Do not add a contact as a supplier
            partner = self.partner_id if not self.partner_id.parent_id else self.partner_id.parent_id
            if line.product_id and partner not in line.product_id.seller_ids.mapped('name') and len(
                    line.product_id.seller_ids) <= 10:
                # Convert the price in the right currency.
                currency = partner.property_purchase_currency_id or self.env.company.currency_id
                price = self.currency_id._convert(line.price_unit, currency, line.company_id,
                                                  line.date_order or fields.Date.today(), round=False)
                # Compute the price for the template's UoM, because the supplier's UoM is related to that UoM.
                if line.product_id.product_tmpl_id.uom_po_id != line.product_uom:
                    default_uom = line.product_id.product_tmpl_id.uom_po_id
                    price = line.product_uom._compute_price(price, default_uom)

                supplierinfo = self._prepare_supplier_info(partner, line, price, currency)
                # In case the order partner is a contact address, a new supplierinfo is created on
                # the parent company. In this case, we keep the product name and code.
                seller = line.product_id._select_seller(
                    partner_id=line.partner_id,
                    quantity=line.product_qty,
                    date=line.quotation_id.date_order and line.quotation_id.date_order.date(),
                    uom_id=line.product_uom)
                if seller:
                    supplierinfo['product_name'] = seller.product_name
                    supplierinfo['product_code'] = seller.product_code
                vals = {
                    'seller_ids': [(0, 0, supplierinfo)],
                }
                try:
                    line.product_id.write(vals)
                except AccessError:  # no write access rights -> just ignore
                    break

    @api.constrains('company_id', 'order_line')
    def _check_order_line_company_id(self):
        for order in self:
            companies = order.order_line.product_id.company_id
            if companies and companies != order.company_id:
                bad_products = order.order_line.product_id.filtered(
                    lambda p: p.company_id and p.company_id != order.company_id)
                raise ValidationError(_(
                    "Your quotation contains products from company %(product_company)s whereas your quotation belongs to company %(quote_company)s. \n Please change the company of your quotation or remove the products from other companies (%(bad_products)s).",
                    product_company=', '.join(companies.mapped('display_name')),
                    quote_company=order.company_id.display_name,
                    bad_products=', '.join(bad_products.mapped('display_name')),
                ))

    def write(self, vals):
        vals, partner_vals = self._write_partner_values(vals)
        res = super().write(vals)
        if partner_vals:
            self.partner_id.sudo().write(partner_vals)  # Because the purchase user doesn't have write on `res.partner`
        return res

    @api.depends('date_order', 'currency_id', 'company_id', 'company_id.currency_id')
    def _compute_currency_rate(self):
        for order in self:
            order.currency_rate = self.env['res.currency']._get_conversion_rate(order.company_id.currency_id,
                                                                                order.currency_id, order.company_id,
                                                                                order.date_order)

    @api.depends('order_line.taxes_id', 'order_line.price_subtotal', 'amount_total', 'amount_untaxed')
    def _compute_tax_totals_json(self):
        def compute_taxes(order_line):
            return order_line.taxes_id._origin.compute_all(**order_line._prepare_compute_all_values())

        account_move = self.env['account.move']
        for order in self:
            tax_lines_data = account_move._prepare_tax_lines_data_for_totals_from_object(order.order_line,
                                                                                         compute_taxes)
            tax_totals = account_move._get_tax_totals(order.partner_id, tax_lines_data, order.amount_total,
                                                      order.amount_untaxed, order.currency_id)
            order.tax_totals_json = json.dumps(tax_totals)

    @api.depends('order_line.date_planned')
    def _compute_date_planned(self):
        """ date_planned = the earliest date_planned across all order lines. """
        for order in self:
            dates_list = order.order_line.filtered(lambda x: not x.display_type and x.date_planned).mapped(
                'date_planned')
            if dates_list:
                order.date_planned = fields.Datetime.to_string(min(dates_list))
            else:
                order.date_planned = False

    @api.depends('name', 'partner_ref')
    def name_get(self):
        result = []
        for po in self:
            name = po.name
            if po.partner_ref:
                name += ' (' + po.partner_ref + ')'
            if self.env.context.get('show_total_amount') and po.amount_total:
                name += ': ' + formatLang(self.env, po.amount_total, currency_obj=po.currency_id)
            result.append((po.id, name))
        return result

    @api.depends('order_line.taxes_id', 'order_line.price_subtotal', 'amount_total', 'amount_untaxed')
    def _compute_tax_totals_json(self):
        def compute_taxes(order_line):
            return order_line.taxes_id._origin.compute_all(**order_line._prepare_compute_all_values())

        account_move = self.env['account.move']
        for order in self:
            tax_lines_data = account_move._prepare_tax_lines_data_for_totals_from_object(order.order_line,
                                                                                         compute_taxes)
            tax_totals = account_move._get_tax_totals(order.partner_id, tax_lines_data, order.amount_total,
                                                      order.amount_untaxed, order.currency_id)
            order.tax_totals_json = json.dumps(tax_totals)

    @api.depends('company_id.account_fiscal_country_id', 'fiscal_position_id.country_id',
                 'fiscal_position_id.foreign_vat')
    def _compute_tax_country_id(self):
        for record in self:
            if record.fiscal_position_id.foreign_vat:
                record.tax_country_id = record.fiscal_position_id.country_id
            else:
                record.tax_country_id = record.company_id.account_fiscal_country_id

    @api.onchange('date_planned')
    def onchange_date_planned(self):
        if self.date_planned:
            self.order_line.filtered(lambda line: not line.display_type).date_planned = self.date_planned

    @api.model
    def create(self, vals):
        if 'company_id' in vals:
            self = self.with_company(vals['company_id'])
        result = super(PurchaseQuotation, self).create(vals)
        if vals.get('name', _('New')) == _('New'):
            for line in result:
                bu_code = line.hr_bu_id.code
                so = self.env['purchase.quotation'].search([])
                date = fields.Date.today()
                order_date = vals.get('date_order') or datetime.today()
                if len(so) != 0:
                    # last_avg_number =self.env['sale.order'].search('name')
                    last_avg_number = self.env['purchase.quotation'].search([])[0].name
                    if type(order_date) != str:
                        months = order_date.month
                        years = order_date.year
                    else:
                        months = datetime.strptime(order_date, '%Y-%m-%d %H:%M:%S').month

                        years = datetime.strptime(order_date, '%Y-%m-%d %H:%M:%S').year
                    date_start = datetime(int(years), int(months), 1)
                    date_months = ("0" + str(months)) if months < 10 else months
                    if months == 12:
                        date_end = datetime(int(years) + 1, 1, 1)
                    else:
                        date_end = datetime(int(years), int(months) + 1, 1) - timedelta(days=1)
                    starting_date = date_start.replace(second=1)
                    ending_date = date_end.replace(hour=23, minute=59, second=59)
                    so_id = self.env['purchase.quotation'].search([('date_order', '>=', starting_date),
                                                                   ('date_order', '<=', ending_date),
                                                                   ('name', 'like', bu_code)], order="name desc",
                                                                  limit=1)
                    name = "RQ" + "-" + str(bu_code) + "-" + str(years) + "-" + str(date_months) + "-00001"
                    if last_avg_number == 'New':
                        name = name
                    digit = 0
                    if so_id:
                        name = so_id.name
                        code = name.split('-')
                        month = int(code[3])
                        if month != int(months):
                            name = "RQ" + "-" + str(bu_code) + "-" + str(years) + "-" + str(date_months) + "-00001"
                        elif digit == 0:
                            digit = int(code[4])
                            digit += 1
                            code = '%05d' % (int(digit))
                            name = "RQ" + "-" + str(bu_code) + "-" + str(years) + "-" + str(date_months) + "-" + str(
                                code)
        result.write({'name': name})
        return result

    def _must_delete_date_planned(self, field_name):
        # To be overridden
        return field_name == 'order_line'

    def onchange(self, values, field_name, field_onchange):
        """Override onchange to NOT to update all date_planned on PO lines when
        date_planned on PO is updated by the change of date_planned on PO lines.
        """
        result = super(PurchaseQuotation, self).onchange(values, field_name, field_onchange)
        if self._must_delete_date_planned(field_name) and 'value' in result:
            already_exist = [ol[1] for ol in values.get('order_line', []) if ol[1]]
            for line in result['value'].get('order_line', []):
                if line[0] < 2 and 'date_planned' in line[2] and line[1] in already_exist:
                    del line[2]['date_planned']
        return result

    @api.onchange('partner_id', 'company_id')
    def onchange_partner_id(self):
        # Ensures all properties and fiscal positions
        # are taken with the company of the order
        # if not defined, with_company doesn't change anything.
        self = self.with_company(self.company_id)
        if not self.partner_id:
            self.fiscal_position_id = False
            self.currency_id = self.env.company.currency_id.id
        else:
            self.fiscal_position_id = self.env['account.fiscal.position'].get_fiscal_position(self.partner_id.id)
            self.payment_term_id = self.partner_id.property_supplier_payment_term_id.id
            self.currency_id = self.partner_id.property_purchase_currency_id.id or self.env.company.currency_id.id
        return {}

    @api.onchange('fiscal_position_id', 'company_id')
    def _compute_tax_id(self):
        """
        Trigger the recompute of the taxes if the fiscal position is changed on the PO.
        """
        self.order_line._compute_tax_id()

    def _write_partner_values(self, vals):
        partner_values = {}
        if 'receipt_reminder_email' in vals:
            partner_values['receipt_reminder_email'] = vals.pop('receipt_reminder_email')
        if 'reminder_date_before_receipt' in vals:
            partner_values['reminder_date_before_receipt'] = vals.pop('reminder_date_before_receipt')
        return vals, partner_values

    def view_purchase_order(self):
        form_view_id = self.env.ref('purchase_customize.oversea_purchase_order_form').id
        tree_view_id = self.env.ref('purchase_customize.oversea_purchase_order_view_tree').id
        action = self.env.ref('purchase.purchase_form_action').read()[0]
        if self.is_oversea_purchase:
            action = self.env.ref('purchase_customize.oversea_purchase_action').read()[0]
            action['views'] = [(tree_view_id, 'tree'), (form_view_id, 'form')]
        res_id = self.env['purchase.order'].search([('purchase_id', '=', self.id)])
        action['domain'] = [('purchase_id', '=', self.id)]
        # action['res_id'] = res_id.id
        return action


class PurchaseQuotationLine(models.Model):
    _name = 'purchase.quotation.line'
    _description = 'Purchase quotation Line'

    name = fields.Text(string='Description', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    discount_value = fields.Float(string="Discount Value")
    product_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', required=True)
    product_uom_qty = fields.Float(string='Total Quantity', compute='_compute_product_uom_qty', store=True)
    date_planned = fields.Datetime(string='Delivery Date', index=True,
                                   help="Delivery date expected from vendor. This date respectively defaults to vendor pricelist lead time then today's date.")
    taxes_id = fields.Many2many('account.tax', string='Taxes',
                                domain=['|', ('active', '=', False), ('active', '=', True)])
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure',
                                  domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    product_id = fields.Many2one('product.product', string='Product', domain=[('purchase_ok', '=', True)],
                                 change_default=True)
    product_type = fields.Selection(related='product_id.detailed_type', readonly=True)
    price_unit = fields.Float(string='Unit Price', required=True, digits='Product Price')

    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', store=True)
    price_tax = fields.Float(compute='_compute_amount', string='Tax', store=True)

    quotation_id = fields.Many2one('purchase.quotation', string='Order Reference', index=True, required=True,
                                   ondelete='cascade')
    account_analytic_id = fields.Many2one('account.analytic.account', store=True, string='Analytic Account',
                                          compute='_compute_account_analytic_id', readonly=False)
    analytic_tag_ids = fields.Many2many('account.analytic.tag', store=True, string='Analytic Tags',
                                        compute='_compute_analytic_tag_ids', readonly=False)
    company_id = fields.Many2one('res.company', related='quotation_id.company_id', string='Company', store=True,
                                 readonly=True)
    state = fields.Selection(related='quotation_id.state', store=True)

    invoice_lines = fields.One2many('account.move.line', 'purchase_line_id', string="Bill Lines", readonly=True,
                                    copy=False)

    # Replace by invoiced Qty
    qty_invoiced = fields.Float(compute='_compute_qty_invoiced', string="Billed Qty", digits='Product Unit of Measure',
                                store=True)

    qty_received_method = fields.Selection([('manual', 'Manual')], string="Received Qty Method",
                                           compute='_compute_qty_received_method', store=True,
                                           help="According to product configuration, the received quantity can be automatically computed by mechanism :\n"
                                                "  - Manual: the quantity is set manually on the line\n"
                                                "  - Stock Moves: the quantity comes from confirmed pickings\n")
    qty_received = fields.Float("Received Qty", compute='_compute_qty_received', inverse='_inverse_qty_received',
                                compute_sudo=True, store=True, digits='Product Unit of Measure')
    qty_received_manual = fields.Float("Manual Received Qty", digits='Product Unit of Measure', copy=False)
    qty_to_invoice = fields.Float(compute='_compute_qty_invoiced', string='To Invoice Quantity', store=True,
                                  readonly=True,
                                  digits='Product Unit of Measure')

    partner_id = fields.Many2one('res.partner', related='quotation_id.partner_id', string='Partner', readonly=True,
                                 store=True)
    currency_id = fields.Many2one(related='quotation_id.currency_id', store=True, string='Currency', readonly=True)
    date_order = fields.Datetime(related='quotation_id.date_order', string='Order Date', readonly=True)
    product_packaging_id = fields.Many2one('product.packaging', string='Packaging',
                                           domain="[('purchase', '=', True), ('product_id', '=', product_id)]",
                                           check_company=True)
    product_packaging_qty = fields.Float('Packaging Quantity')
    number = fields.Integer(
        compute='_compute_get_number',
        store=True,
    )
    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note")], default=False, help="Technical field for UX purpose.")
    stock_balance = fields.Float(string="Stock Balance", related='product_id.qty_available')
    discount_type = fields.Selection(related='quotation_id.discount_type', string='Discount Method')#SLO

    _sql_constraints = [
        ('accountable_required_fields',
         "CHECK(display_type IS NOT NULL OR (product_id IS NOT NULL AND product_uom IS NOT NULL AND date_planned IS NOT NULL))",
         "Missing required fields on accountable purchase order line."),
        ('non_accountable_null_fields',
         "CHECK(display_type IS NULL OR (product_id IS NULL AND price_unit = 0 AND product_uom_qty = 0 AND product_uom IS NULL AND date_planned is NULL))",
         "Forbidden values on non-accountable purchase order line"),
    ]


    def action_product_forecast_report(self):
        self.ensure_one()
        action = self.product_id.action_product_forecast_report()
        action['context'] = {
            'active_id': self.product_id.id,
            'active_model': 'product.product',
            # 'move_to_match_ids': self.ids,
        }
        # if self.picking_type_id.code in self._consuming_picking_types():
        #     warehouse = self.picking_type_id.warehouse_id
        # else:
        warehouse = self.quotation_id.picking_type_id.warehouse_id

        if warehouse:
            action['context']['warehouse'] = warehouse.id
        return action

    @api.depends("discount_value")
    def _compute_amount(self):
        return super()._compute_amount()

    @api.onchange('product_id')
    def onchange_bu_product(self):
        for rec in self.quotation_id:
            return {'domain': {
                'product_id': [('business_id', '=', rec.hr_bu_id.id), ('unit_or_part', '=', rec.unit_or_part)]}}

    def _get_discounted_price_unit(self):
        """Inheritable method for getting the unit price after applying
        discount(s).

        :rtype: float
        :return: Unit price after discount(s).
        """
        self.ensure_one()
        if self.quotation_id.discount_type == 'percentage':
            return self.price_unit * (1 - self.discount_value / 100)
        elif self.quotation_id.discount_type == 'fixed':
            return self.price_unit - self.discount_value

        return self.price_unit

    @api.depends('product_qty', 'price_unit', 'taxes_id', 'discount_type', 'discount_value') #SLO
    def _compute_amount(self):
        for line in self:
            taxes = line.taxes_id.compute_all(**line._prepare_compute_all_values())
            discount_value = (line.discount_value if line.discount_type == 'fixed' else line.price_unit * line.discount_value / 100) * line.product_qty #SLO
            price_subtotal = taxes['total_excluded'] - discount_value #SLO
            line.update({
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

    @api.depends('sequence', 'quotation_id')
    def _compute_get_number(self):
        for order in self.mapped('quotation_id'):
            number = 1
            for line in order.order_line:
                line.number = number
                number += 1

    @api.onchange('qty_received')
    def _inverse_qty_received(self):
        """ When writing on qty_received, if the value should be modify manually (`qty_received_method` = 'manual' only),
            then we put the value in `qty_received_manual`. Otherwise, `qty_received_manual` should be False since the
            received qty is automatically compute by other mecanisms.
        """
        for line in self:
            if line.qty_received_method == 'manual':
                line.qty_received_manual = line.qty_received
            else:
                line.qty_received_manual = 0.0

    def _prepare_compute_all_values(self):
        # Hook method to returns the different argument values for the
        # compute_all method, due to the fact that discounts mechanism
        # is not implemented yet on the purchase orders.
        # This method should disappear as soon as this feature is
        # also introduced like in the sales module.
        self.ensure_one()
        return {
            'price_unit': self._get_discounted_price_unit(),
            'currency': self.quotation_id.currency_id,
            'quantity': self.product_qty,
            'product': self.product_id,
            'partner': self.quotation_id.partner_id,
        }

    def _compute_tax_id(self):
        for line in self:
            line = line.with_company(line.company_id)
            fpos = line.quotation_id.fiscal_position_id or line.quotation_id.fiscal_position_id.get_fiscal_position(
                line.quotation_id.partner_id.id)
            # filter taxes by company
            taxes = line.product_id.supplier_taxes_id.filtered(lambda r: r.company_id == line.env.company)
            line.taxes_id = fpos.map_tax(taxes)

    @api.depends('invoice_lines.move_id.state', 'invoice_lines.quantity', 'qty_received', 'product_uom_qty',
                 'quotation_id.state')
    def _compute_qty_invoiced(self):
        for line in self:
            # compute qty_invoiced
            qty = 0.0
            for inv_line in line._get_invoice_lines():
                if inv_line.move_id.state not in ['cancel']:
                    if inv_line.move_id.move_type == 'in_invoice':
                        qty += inv_line.product_uom_id._compute_quantity(inv_line.quantity, line.product_uom)
                    elif inv_line.move_id.move_type == 'in_refund':
                        qty -= inv_line.product_uom_id._compute_quantity(inv_line.quantity, line.product_uom)
            line.qty_invoiced = qty

            # compute qty_to_invoice
            if line.quotation_id.state in ['purchase', 'done']:
                if line.product_id.purchase_method == 'purchase':
                    line.qty_to_invoice = line.product_qty - line.qty_invoiced
                else:
                    line.qty_to_invoice = line.qty_received - line.qty_invoiced
            else:
                line.qty_to_invoice = 0

    def _get_invoice_lines(self):
        self.ensure_one()
        if self._context.get('accrual_entry_date'):
            return self.invoice_lines.filtered(
                lambda l: l.move_id.invoice_date and l.move_id.invoice_date <= self._context['accrual_entry_date']
            )
        else:
            return self.invoice_lines

    @api.depends('product_id')
    def _compute_qty_received_method(self):
        for line in self:
            if line.product_id and line.product_id.type in ['consu', 'service']:
                line.qty_received_method = 'manual'
            else:
                line.qty_received_method = False

    @api.depends('qty_received_method', 'qty_received_manual')
    def _compute_qty_received(self):
        for line in self:
            if line.qty_received_method == 'manual':
                line.qty_received = line.qty_received_manual or 0.0
            else:
                line.qty_received = 0.0

    @api.depends('product_id', 'date_order')
    def _compute_account_analytic_id(self):
        for rec in self:
            if not rec.account_analytic_id:
                default_analytic_account = rec.env['account.analytic.default'].sudo().account_get(
                    product_id=rec.product_id.id,
                    partner_id=rec.quotation_id.partner_id.id,
                    user_id=rec.env.uid,
                    date=rec.date_order,
                    company_id=rec.company_id.id,
                )
                rec.account_analytic_id = default_analytic_account.analytic_id

    @api.depends('product_id', 'date_order')
    def _compute_analytic_tag_ids(self):
        for rec in self:
            if not rec.analytic_tag_ids:
                default_analytic_account = rec.env['account.analytic.default'].sudo().account_get(
                    product_id=rec.product_id.id,
                    partner_id=rec.quotation_id.partner_id.id,
                    user_id=rec.env.uid,
                    date=rec.date_order,
                    company_id=rec.company_id.id,
                )
                rec.analytic_tag_ids = default_analytic_account.analytic_tag_ids

    @api.onchange('product_id')
    def onchange_product_id(self):
        if not self.product_id:
            return

        # Reset date, price and quantity since _onchange_quantity will provide default values
        self.price_unit = self.product_qty = 0.0

        self._product_id_change()

        self._suggest_quantity()
        self._onchange_quantity()

    def _product_id_change(self):
        if not self.product_id:
            return

        self.product_uom = self.product_id.uom_po_id or self.product_id.uom_id
        product_lang = self.product_id.with_context(
            lang=get_lang(self.env, self.partner_id.lang).code,
            partner_id=self.partner_id.id,
            company_id=self.company_id.id,
        )
        self.name = self._get_product_purchase_description(product_lang)

        self._compute_tax_id()

    def _onchange_quantity(self):
        if not self.product_id:
            return
        params = {'quotation_id': self.quotation_id}
        seller = self.product_id._select_seller(
            partner_id=self.partner_id,
            quantity=self.product_qty,
            date=self.quotation_id.date_order and self.quotation_id.date_order.date(),
            uom_id=self.product_uom,
            params=params)

        if seller or not self.date_planned:
            self.date_planned = self._get_date_planned(seller).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        # If not seller, use the standard price. It needs a proper currency conversion.
        if not seller:
            po_line_uom = self.product_uom or self.product_id.uom_po_id
            price_unit = self.env['account.tax']._fix_tax_included_price_company(
                self.product_id.uom_id._compute_price(self.product_id.standard_price, po_line_uom),
                self.product_id.supplier_taxes_id,
                self.taxes_id,
                self.company_id,
            )
            if price_unit and self.quotation_id.currency_id and self.quotation_id.company_id.currency_id != self.quotation_id.currency_id:
                price_unit = self.quotation_id.company_id.currency_id._convert(
                    price_unit,
                    self.quotation_id.currency_id,
                    self.quotation_id.company_id,
                    self.date_order or fields.Date.today(),
                )

            self.price_unit = price_unit
            return

        price_unit = self.env['account.tax']._fix_tax_included_price_company(seller.price,
                                                                             self.product_id.supplier_taxes_id,
                                                                             self.taxes_id,
                                                                             self.company_id) if seller else 0.0
        if price_unit and seller and self.quotation_id.currency_id and seller.currency_id != self.quotation_id.currency_id:
            price_unit = seller.currency_id._convert(
                price_unit, self.quotation_id.currency_id, self.quotation_id.company_id,
                self.date_order or fields.Date.today())

        if seller and self.product_uom and seller.product_uom != self.product_uom:
            price_unit = seller.product_uom._compute_price(price_unit, self.product_uom)

        self.price_unit = price_unit
        product_ctx = {'seller_id': seller.id, 'lang': get_lang(self.env, self.partner_id.lang).code}
        self.name = self._get_product_purchase_description(self.product_id.with_context(product_ctx))

    @api.onchange('product_id', 'product_qty', 'product_uom')
    def _onchange_suggest_packaging(self):
        # remove packaging if not match the product
        if self.product_packaging_id.product_id != self.product_id:
            self.product_packaging_id = False
        # suggest biggest suitable packaging
        if self.product_id and self.product_qty and self.product_uom:
            self.product_packaging_id = self.product_id.packaging_ids.filtered(
                'purchase')._find_suitable_product_packaging(self.product_qty, self.product_uom)

    @api.model
    def _get_date_planned(self, seller, po=False):
        """Return the datetime value to use as Schedule Date (``date_planned``) for
           PO Lines that correspond to the given product.seller_ids,
           when ordered at `date_order_str`.

           :param Model seller: used to fetch the delivery delay (if no seller
                                is provided, the delay is 0)
           :param Model po: purchase.order, necessary only if the PO line is
                            not yet attached to a PO.
           :rtype: datetime
           :return: desired Schedule Date for the PO line
        """
        date_order = po.date_order if po else self.quotation_id.date_order
        if date_order:
            return date_order + relativedelta(days=seller.delay if seller else 0)
        else:
            return datetime.today() + relativedelta(days=seller.delay if seller else 0)

    def copy(self, default=None):
        ctx = dict(self.env.context)
        ctx.pop('default_product_id', None)
        self = self.with_context(ctx)
        new_po = super(PurchaseQuotation, self).copy(default=default)
        for line in new_po.order_line:
            if line.product_id:
                seller = line.product_id._select_seller(
                    partner_id=line.partner_id, quantity=line.product_qty,
                    date=line.quotation_id.date_order and line.quotation_id.date_order.date(), uom_id=line.product_uom)
                line.date_planned = line._get_date_planned(seller)
        return new_po

    @api.onchange('product_packaging_id')
    def _onchange_product_packaging_id(self):
        if self.product_packaging_id and self.product_qty:
            newqty = self.product_packaging_id._check_qty(self.product_qty, self.product_uom, "UP")
            if float_compare(newqty, self.product_qty, precision_rounding=self.product_uom.rounding) != 0:
                return {
                    'warning': {
                        'title': _('Warning'),
                        'message': _(
                            "This product is packaged by %(pack_size).2f %(pack_name)s. You should purchase %(quantity).2f %(unit)s.",
                            pack_size=self.product_packaging_id.qty,
                            pack_name=self.product_id.uom_id.name,
                            quantity=newqty,
                            unit=self.product_uom.name
                        ),
                    },
                }

    @api.onchange('product_packaging_id', 'product_uom', 'product_qty')
    def _onchange_update_product_packaging_qty(self):
        if not self.product_packaging_id:
            self.product_packaging_qty = 0
        else:
            packaging_uom = self.product_packaging_id.product_uom_id
            packaging_uom_qty = self.product_uom._compute_quantity(self.product_qty, packaging_uom)
            self.product_packaging_qty = float_round(packaging_uom_qty / self.product_packaging_id.qty,
                                                     precision_rounding=packaging_uom.rounding)

    @api.onchange('product_packaging_qty')
    def _onchange_product_packaging_qty(self):
        if self.product_packaging_id:
            packaging_uom = self.product_packaging_id.product_uom_id
            qty_per_packaging = self.product_packaging_id.qty
            product_qty = packaging_uom._compute_quantity(self.product_packaging_qty * qty_per_packaging,
                                                          self.product_uom)
            if float_compare(product_qty, self.product_qty, precision_rounding=self.product_uom.rounding) != 0:
                self.product_qty = product_qty

    @api.depends('product_uom', 'product_qty', 'product_id.uom_id')
    def _compute_product_uom_qty(self):
        for line in self:
            if line.product_id and line.product_id.uom_id != line.product_uom:
                line.product_uom_qty = line.product_uom._compute_quantity(line.product_qty, line.product_id.uom_id)
            else:
                line.product_uom_qty = line.product_qty

    def _suggest_quantity(self):
        '''
        Suggest a minimal quantity based on the seller
        '''
        if not self.product_id:
            return
        seller_min_qty = self.product_id.seller_ids \
            .filtered(
            lambda r: r.name == self.quotation_id.partner_id and (not r.product_id or r.product_id == self.product_id)) \
            .sorted(key=lambda r: r.min_qty)
        if seller_min_qty:
            self.product_qty = seller_min_qty[0].min_qty or 1.0
            self.product_uom = seller_min_qty[0].product_uom
        else:
            self.product_qty = 1.0

    def _get_product_purchase_description(self, product_lang):
        self.ensure_one()
        name = product_lang.display_name
        if product_lang.description_purchase:
            name += '\n' + product_lang.description_purchase

        return name

    @api.model
    def _prepare_purchase_order_line(self, product_id, product_qty, product_uom, company_id, supplier, po):
        partner = supplier.name
        uom_po_qty = product_uom._compute_quantity(product_qty, product_id.uom_po_id)
        # _select_seller is used if the supplier have different price depending
        # the quantities ordered.
        seller = product_id.with_company(company_id)._select_seller(
            partner_id=partner,
            quantity=uom_po_qty,
            date=po.date_order and po.date_order.date(),
            uom_id=product_id.uom_po_id)

        product_taxes = product_id.supplier_taxes_id.filtered(lambda x: x.company_id.id == company_id.id)
        taxes = po.fiscal_position_id.map_tax(product_taxes)

        price_unit = self.env['account.tax']._fix_tax_included_price_company(
            seller.price, product_taxes, taxes, company_id) if seller else 0.0
        if price_unit and seller and po.currency_id and seller.currency_id != po.currency_id:
            price_unit = seller.currency_id._convert(
                price_unit, po.currency_id, po.company_id, po.date_order or fields.Date.today())

        product_lang = product_id.with_prefetch().with_context(
            lang=partner.lang,
            partner_id=partner.id,
        )
        name = product_lang.with_context(seller_id=seller.id).display_name
        if product_lang.description_purchase:
            name += '\n' + product_lang.description_purchase

        date_planned = self.quotation_id.date_planned or self._get_date_planned(seller, po=po)

        return {
            'name': name,
            'product_qty': uom_po_qty,
            'product_id': product_id.id,
            'product_uom': product_id.uom_po_id.id,
            'price_unit': price_unit,
            'date_planned': date_planned,
            'taxes_id': [(6, 0, taxes.ids)],
            'quotation_id': po.id,
        }

    def _convert_to_middle_of_day(self, date):
        """Return a datetime which is the noon of the input date(time) according
        to order user's time zone, convert to UTC time.
        """
        return timezone(self.quotation_id.user_id.tz or self.company_id.partner_id.tz or 'UTC').localize(
            datetime.combine(date, time(12))).astimezone(UTC).replace(tzinfo=None)

    def _update_date_planned(self, updated_date):
        self.date_planned = updated_date

    def _track_qty_received(self, new_qty):
        self.ensure_one()
        if new_qty != self.qty_received and self.quotation_id.state == 'purchase':
            self.quotation_id.message_post_with_view(
                'purchase.track_po_line_qty_received_template',
                values={'line': self, 'qty_received': new_qty},
                subtype_id=self.env.ref('mail.mt_note').id
            )
