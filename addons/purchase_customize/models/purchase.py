from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang, format_amount
from odoo import api, fields, models, SUPERUSER_ID, _


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.model
    def _get_bu(self):
        if self.env.user.user_type_id == 'bu':
            return self.env.user.current_bu_br_id

    def _set_bu_domain(self):
        domain = [('id', 'in', [bu.id for bu in self.env.user.hr_bu_ids])]
        return domain

    hr_bu_id = fields.Many2one('business.unit', string='Business Unit', default=_get_bu, domain=_set_bu_domain)

    purchase_order_type = fields.Selection(
        [('stock', 'Stock Order Type'), ('customer', 'Customer Order Type'), ('emergency', 'Emergency Order Type'),
         ('tender', 'Tender Order Type'), ('management', 'Management Order Type')], default='stock',
        string="Purchase Order Type", required=True)
    shipping_method = fields.Selection([('air', 'Air'), ('sea', 'Sea'), ('landed', 'Landed')], string="Shipping Method")
    ref_no = fields.Char(string='Reference No')
    attached_file = fields.Binary(string="Attached File")
    ceo_ref = fields.Binary()
    ceofile_name = fields.Char()
    coo_ref = fields.Binary()
    coofile_name = fields.Char()
    file_name = fields.Char('File Name')
    discount_view = fields.Selection([('doc_discount', 'Document Discount'), ('line_discount', 'Line Discount')],
                                     string='Discount Type')
    discount_type = fields.Selection([('fixed', 'Fixed'), ('percentage', 'Percentage')], string='Discount Method')
    discount_value = fields.Float(string='Discount Value')
    discounted_amount = fields.Float(string='Discounted Amount', readonly=True, compute='disc_amount')
    is_oversea_purchase = fields.Boolean(string="Is Oversea Purchase")
    unit_or_part = fields.Selection([('unit', 'Unit'), ('part', 'Spare Part')], default='part')
    order_approve_person = fields.Many2one('res.parnter')

    state = fields.Selection([
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('approved_inventory_head', 'Approved Inventory Head'),
        ('approved_gm_agm', 'Approved GM/AGM'),
        ('approved_by_mgt', 'Approved By Management'),
        ('approved_by_po_dept', 'Approved By PO DEPT'),
        ('after_sale_approved', 'After Sale Approved'),
        ('approved_by_finance', 'Finance & Account Approved'),
        ('approved_by_coo', 'COO Approved'),
        ('holding', 'Holding'),
        ('reject', 'Reject'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)

    # state = fields.Selection(selection_add=[
    #     ('approved_inventory_head', 'Approved Inventory Head'),
    #     ('approved_gm_agm', 'Approved GM/AGM'),
    #     ('approved_by_mgt', 'Approved By Management'),
    #     ('approved_by_po_dept', 'Approved By PO DEPT'),
    #     ('after_sale_approved', 'After Sale Approved'),
    #     ('approved_by_finance', 'Finance & Account Approved'),
    #     ('approved_by_coo', 'COO Approved'),
    #     ('holding', 'Holding'),
    #     ('reject', 'Reject')])

    replace_order_line = fields.One2many('replace.order.line', 'purchase_order_id')
    prepayment_id = fields.Many2one('account.payment')

    deliver_id = fields.Many2one('stock.picking')
    saleorder_id = fields.Many2one('sale.order')
    conditional = fields.Selection(
        [('storage', 'Shortage'), ('warranty', 'Warranty'), ('engine', 'Engine'),
         ('breakdown', 'Breakdown')], string="Conditional", required=True)


    def action_approve_inventory_head(self):
        self.write({'state': 'approved_inventory_head'})

    def action_approve_gm_agm(self):
        self.write({'state': 'approved_gm_agm'})

    def _prepare_invoice(self):
        result = super(PurchaseOrder, self)._prepare_invoice()
        result.update({
            'hr_bu_id': self.hr_bu_id and self.hr_bu_id.id,
            'unit_or_part': self.unit_or_part,
            'is_oversea_purchase': self.is_oversea_purchase,
        })

        return result

    @api.onchange('unit_or_part')
    def onchange_unit_part(self):
        self.order_line = False

    def _prepare_picking(self):
        if not self.group_id:
            self.group_id = self.group_id.create({
                'name': self.name,
                'partner_id': self.partner_id.id
            })
        if not self.partner_id.property_stock_supplier.id:
            raise UserError(_("You must set a Vendor Location for this partner %s", self.partner_id.name))
        return {
            'picking_type_id': self.picking_type_id.id,
            'partner_id': self.partner_id.id,
            'user_id': False,
            'date': self.date_order,
            'origin': self.name,
            'location_dest_id': self._get_destination_location(),
            'location_id': self.partner_id.property_stock_supplier.id,
            'company_id': self.company_id.id,
            'hr_bu_id': self.hr_bu_id.id,
            'unit_or_part': self.unit_or_part,
        }

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
            return {'domain': {'hr_bu_id': [('id', 'in', [bu.id for bu in self.env.user.hr_bu_ids])]}}

    # def action_management_approve(self):
    #     for rec in self:
    #         rec.write({'state': 'approved_by_mgt'})
    def action_coo_approve(self):
        for rec in self:
            if rec.unit_or_part == 'unit':
                rec.write({'state': 'approved_by_coo'})

    def action_finance_approve(self):
        for rec in self:
            if rec.unit_or_part == 'unit':
                rec.write({'state': 'approved_by_finance'})

    def action_po_dept_approve(self):
        for rec in self:
            if rec.state == 'after_sale_approved' and rec.unit_or_part == 'part':
                rec.write({'state': 'approved_by_po_dept'})
            if rec.state == 'approved_by_mgt' and rec.unit_or_part == 'unit':
                rec.write({'state': 'approved_by_po_dept'})
            if rec.state == 'approved_by_coo':
                rec.write({'state': 'approved_by_po_dept'})
            if rec.state == 'holding' and rec.unit_or_part == 'unit':
                rec.write({'state': 'approved_by_po_dept'})

    def action_after_sale_approve(self):
        for rec in self:
            if rec.state in ['approved_gm_agm'] and rec.unit_or_part == 'part':
                rec.write({'state': 'after_sale_approved'})

    def button_confirm(self):
        for order in self:
            if order.is_oversea_purchase == True and order.state not in ['after_sale_approved', 'approved_by_po_dept']:
                continue
            # elif order.is_oversea_purchase == False and order.state not in ['draft', 'sent']:
            #     continue
            order._add_supplier_to_product()
            # Deal with double validation process
            if order._approval_allowed():
                order.button_approve()
            else:
                order.write({'state': 'to approve'})
            if order.partner_id not in order.message_partner_ids:
                order.message_subscribe([order.partner_id.id])
        return True
        
    # SLO start
    @api.onchange('discount_type')
    def onchange_discount(self):
        for rec in self:
            rec.discount_value = 0.0
            rec.discounted_amount = 0.0
            for line in rec.order_line:
                line._compute_amount()

    @api.onchange('discount_view')
    def onchange_discount_view(self):
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
    # SLO end

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
                'amount_total': amount_untaxed + amount_tax, #SLO Update
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

    def _create_picking(self):
        StockPicking = self.env['stock.picking']
        for order in self.filtered(lambda po: po.state in ('purchase', 'done')):
            if any(product.type in ['product', 'consu'] for product in order.order_line.product_id):
                order = order.with_company(order.company_id)
                pickings = order.picking_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
                if not pickings:
                    res = order._prepare_picking()
                    picking = StockPicking.with_user(SUPERUSER_ID).create(res)
                else:
                    picking = pickings[0]
                moves = order.order_line._create_stock_moves(picking)
                # moves = moves.filtered(lambda x: x.state not in ('done', 'cancel'))._action_confirm()
                seq = 0
                for move in sorted(moves, key=lambda move: move.date):
                    seq += 5
                    move.sequence = seq
                moves._action_assign()
                picking.message_post_with_view('mail.message_origin_link',
                                               values={'self': picking, 'origin': order},
                                               subtype_id=self.env.ref('mail.mt_note').id)
        return True

    def refuse_goods(self, reason):
        self.write({'state': 'reject'})
        self.message_post_with_view('purchase_customize.po_template_reject_reason',
                                    values={'reason': reason, 'name': self.name})

    def hold_goods(self, reason):
        self.write({'state': 'holding'})
        self.message_post_with_view('purchase_customize.po_template_hold_reason',
                                    values={'reason': reason, 'name': self.name})


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'
    stock_balance = fields.Float(string="Stock Balance", related='product_id.qty_available')
    discount_value = fields.Float(string="Discount Value")
    discount_type = fields.Selection(related='order_id.discount_type', string='Discount Method')
    number = fields.Integer(
        compute='_compute_get_number',
        store=True,
    )
    hr_bu_id = fields.Many2one('business.unit', string='BU', related='order_id.hr_bu_id')



    @api.depends("discount_value")
    def _compute_amount(self):
        return super()._compute_amount()

    @api.depends('product_qty', 'price_unit', 'taxes_id', 'discount_type', 'discount_value')
    def _compute_amount(self):
        for line in self:
            taxes = line.taxes_id.compute_all(**line._prepare_compute_all_values())
            discount_value = (line.discount_value if line.discount_type == 'fixed' else line.price_unit * line.discount_value / 100) * line.product_qty
            price_subtotal = taxes['total_excluded'] - discount_value
            line.update({
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

    def _prepare_compute_all_values(self):
        vals = super()._prepare_compute_all_values()
        vals.update({"price_unit": self._get_discounted_price_unit()})
        return vals

    @api.depends('sequence', 'order_id')
    def _compute_get_number(self):
        for order in self.mapped('order_id'):
            number = 1
            for line in order.order_line:
                line.number = number
                number += 1

    def _onchange_quantity(self):
        if not self.product_id:
            return
        params = {'order_id': self.order_id}
        seller = self.product_id._select_seller(
            partner_id=self.partner_id,
            quantity=self.product_qty,
            date=self.order_id.date_order and self.order_id.date_order.date(),
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
            if price_unit and self.order_id.currency_id and self.order_id.company_id.currency_id != self.order_id.currency_id:
                price_unit = self.order_id.company_id.currency_id._convert(
                    price_unit,
                    self.order_id.currency_id,
                    self.order_id.company_id,
                    self.date_order or fields.Date.today(),
                )

            self.price_unit = price_unit
            return

        price_unit = self.env['account.tax']._fix_tax_included_price_company(seller.price,
                                                                             self.product_id.supplier_taxes_id,
                                                                             self.taxes_id,
                                                                             self.company_id) if seller else 0.0
        if price_unit and seller and self.order_id.currency_id and seller.currency_id != self.order_id.currency_id:
            price_unit = seller.currency_id._convert(
                price_unit, self.order_id.currency_id, self.order_id.company_id, self.date_order or fields.Date.today())

        if seller and self.product_uom and seller.product_uom != self.product_uom:
            price_unit = seller.product_uom._compute_price(price_unit, self.product_uom)

        self.price_unit = price_unit
        product_ctx = {'seller_id': seller.id, 'lang': get_lang(self.env, self.partner_id.lang).code}
        self.name = self._get_product_purchase_description(self.product_id.with_context(product_ctx))

    # _sql_constraints = [
    #     (
    #         "discount_limit",
    #         "CHECK (discount_value <= 100.0)",
    #         "Discount must be lower than 100%.",
    #     )
    # ]

    def _get_discounted_price_unit(self):
        """Inheritable method for getting the unit price after applying
        discount(s).

        :rtype: float
        :return: Unit price after discount(s).
        """
        self.ensure_one()
        if self.order_id.discount_type == 'percentage':
            return self.price_unit * (1 - self.discount_value / 100)
        elif self.order_id.discount_type == 'fixed':
            return self.price_unit - self.discount_value

        return self.price_unit

    @api.onchange('product_id')
    def onchange_bu_product(self):
        for rec in self.order_id:
            return {'domain': {
                'product_id': [('business_id', '=', rec.hr_bu_id.id), ('unit_or_part', '=', rec.unit_or_part)]}}


class ReplaceOrderLine(models.Model):
    _name = 'replace.order.line'

    product_id = fields.Many2one('product.product', string="Product")
    product_uom_qty = fields.Float(string="Quantity")
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure')
    price_unit = fields.Float('Unit Price', required=True, digits='Product Price', default=0.0)
    purchase_order_id = fields.Many2one('purchase.order', string="Purchase Order Ref")

    @api.onchange('product_id')
    def onchange_price(self):
        for order in self:
            if order.product_id:
                order.price_unit = order.product_id.standard_price
