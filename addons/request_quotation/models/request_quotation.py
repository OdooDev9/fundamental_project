from email.policy import default
from odoo import api, fields, models, SUPERUSER_ID, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError
from odoo.tools.misc import get_lang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare, float_round
import json


class RequestQuotaion(models.Model):
    _name = 'request.quotation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Request for Quotation'
    _order = 'date_order desc, id desc'

    def _default_validity_date(self):
        if self.env['ir.config_parameter'].sudo().get_param('sale.use_quotation_validity_days'):
            days = self.env.company.quotation_validity_days
            if days > 0:
                return fields.Date.to_string(datetime.now() + timedelta(days))
        return False

    @api.model
    def _default_note_url(self):
        return self.env.company.get_base_url()

    @api.model
    def _get_default_team(self):
        return self.env['crm.team']._get_default_team_id()

    @api.model
    def _get_bu(self):
        if self.env.user.user_type_id == 'bu':
            return self.env.user.current_bu_br_id

    def _set_bu_domain(self):
        domain = [('id', 'in', [bu.id for bu in self.env.user.hr_bu_ids])]
        return domain

    def _set_br_domain(self):
        domain = [('id', 'in', [br.id for br in self.env.user.hr_br_ids])]
        return domain

    @api.model
    def _get_br(self):
        if self.env.user.user_type_id == 'br':
            return self.env.user.current_bu_br_id

    @api.model
    def default_get(self, fields):
        """Method to set default warehouse of user branch."""
        result = super(RequestQuotaion, self).default_get(fields)
        company = self.env.user.company_id.id
        warehouse_id = ''
        for sale in self:
            if self.env.user.user_type_id == 'bu' and self.env.user.current_bu_br_id == sale.hr_bu_id.id:
                hr_bu_id = sale.hr_bu_id.id
                warehouse_id = self.env['stock.warehouse'].search([
                    ('hr_bu_id', '=', hr_bu_id),
                    ('company_id', '=', company)], limit=1)
            if self.env.user.user_type_id == 'br' and self.env.user.current_bu_br_id == sale.hr_br_id.id:
                hr_br_id = sale.hr_br_id.id
                warehouse_id = self.env['stock.warehouse'].search([
                    ('hr_bu_id', '=', hr_br_id),
                    ('company_id', '=', company)], limit=1)
            result.update({
                'warehouse_id': warehouse_id and warehouse_id.id or False
            })
        return result

    sale_order_count = fields.Integer(string="Sale Order Count", compute='_compute_sale_order_ids')
    order_ids = fields.One2many('sale.order', 'req_quot_id', string='Sale Orders')
    req_quotation_line = fields.One2many('request.quotation.line', 'request_id', string='Quotation Lines',
                                         states={'cancel': [('readonly', True)], 'done': [('readonly', True)]},
                                         copy=True, auto_join=True)
    name = fields.Char(string='Order Reference', required=True, copy=False, states={'draft': [('readonly', False)]},
                       index=True, default=lambda self: ('New'))

    state = fields.Selection([
        ('draft', 'Quotation'),
        ('approved_sale_admin', 'Approved Sale Admin'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, tracking=3, default='draft')
    date_order = fields.Datetime(string='Quotation Date', required=True, index=True, copy=False,
                                 default=fields.Datetime.now,
                                 help="Creation date of draft/sent orders,\nConfirmation date of confirmed orders.")
    validity_date = fields.Date(string='Expiration', readonly=True, copy=False)
    user_id = fields.Many2one(
        'res.users', string='Salesperson', index=True, tracking=2, default=lambda self: self.env.user,
        domain=lambda self: "[('groups_id', '=', {}), ('share', '=', False), ('company_ids', '=', company_id)]".format(
            self.env.ref("sales_team.group_sale_salesman").id
        ), )
    team_id = fields.Many2one(
        'crm.team', 'Sales Team',
        ondelete="set null", tracking=True,
        change_default=True, default=_get_default_team, check_company=True,  # Unrequired company
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    partner_id = fields.Many2one(
        'res.partner', string='Customer', states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        required=True, change_default=True, index=True, tracking=1,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", )
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True,
                                 default=lambda self: self.env.company)
    payment_term_id = fields.Many2one(
        'account.payment.term', string='Payment Terms', check_company=True,  # Unrequired company
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", )
    show_update_pricelist = fields.Boolean(string='Has Pricelist Changed',
                                           help="Technical Field, True if the pricelist was changed;\n"
                                                " this will then display a recomputation button")
    pricelist_id = fields.Many2one(
        'product.pricelist', string='Pricelist', check_company=True,  # Unrequired company
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", tracking=1,
        help="If you change the pricelist, only newly added lines will be affected.")
    currency_id = fields.Many2one(related='pricelist_id.currency_id', depends=["pricelist_id"], store=True,
                                  ondelete="restrict")
    analytic_account_id = fields.Many2one(
        'account.analytic.account', 'Analytic Account',
        readonly=True, copy=False, check_company=True,  # Unrequired company
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="The analytic account related to a sales order.")
    hr_br_id = fields.Many2one('business.unit', string='Branch', default=_get_br, domain=_set_br_domain)
    hr_bu_id = fields.Many2one('business.unit', string='Business Unit', default=_get_bu, domain=_set_bu_domain)
    note = fields.Html('Terms and conditions')
    fiscal_position_id = fields.Many2one(
        'account.fiscal.position', string='Fiscal Position',
        domain="[('company_id', '=', company_id)]", check_company=True,
        help="Fiscal positions are used to adapt taxes and accounts for particular customers or sales orders/invoices."
             "The default value comes from the customer.")
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, compute='_amount_all', tracking=5)
    tax_totals_json = fields.Char(compute='_compute_tax_totals_json')
    amount_tax = fields.Monetary(string='Taxes', store=True, compute='_amount_all')
    amount_total = fields.Monetary(string='Total', store=True, compute='_amount_all', tracking=4)
    discount_view = fields.Selection([('doc_discount', 'Document Discount'), ('line_discount', 'Line Discount')],
                                     string='Discount Type')
    discount_type = fields.Selection([('fixed', 'Fixed'), ('percentage', 'Percentage')], string='Discount Method')
    discount_value = fields.Float(string='Discount Value')
    discounted_amount = fields.Float(compute='disc_amount', string='Discounted Amount', readonly=True)
    br_discount = fields.Boolean(string="Branch Discount")
    unit_or_part = fields.Selection([('unit', 'Unit'), ('part', 'Spare Part')], string='Units or Part', default='part')
    is_gov_tender = fields.Boolean(string="Is for Government Tender Sales", default=False)
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse',
        required=True, readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        check_company=True)
    bu_br_user_approve = fields.Boolean(compute='compute_bu_br_user_approve')


    def compute_bu_br_user_approve(self):
        for rec in self:
            if rec.unit_or_part == 'part' and self.env.user.user_type_id == 'br':
                rec.bu_br_user_approve = True
                
            elif self.env.user.user_type_id == 'bu':
                rec.bu_br_user_approve = True      
            else:
                rec.bu_br_user_approve = False

    @api.onchange('pricelist_id', 'req_quotation_line')
    def _onchange_pricelist_id(self):
        if self.req_quotation_line and self.pricelist_id and self._origin.pricelist_id != self.pricelist_id:
            self.show_update_pricelist = True
        else:
            self.show_update_pricelist = False

    def update_prices(self):
        self.ensure_one()
        lines_to_update = []
        for line in self.req_quotation_line.filtered(lambda line: not line.display_type):
            product = line.product_id.with_context(
                partner=self.partner_id,
                quantity=line.product_uom_qty,
                date=self.date_order,
                pricelist=self.pricelist_id.id,
                uom=line.product_uom.id
            )
            price_unit = self.env['account.tax']._fix_tax_included_price_company(
                line._get_display_price(product), line.product_id.taxes_id, line.tax_id, line.company_id)
            if self.pricelist_id.discount_policy == 'without_discount' and price_unit:
                price_discount_unrounded = self.pricelist_id.get_product_price(product, line.product_uom_qty,
                                                                               self.partner_id, self.date_order,
                                                                               line.product_uom.id)
                discount = max(0, (price_unit - price_discount_unrounded) * 100 / price_unit)
            else:
                discount = 0
            lines_to_update.append((1, line.id, {'price_unit': price_unit, 'discount': discount}))
        self.update({'req_quotation_line': lines_to_update})
        self.show_update_pricelist = False
        self.message_post(body=_("Product prices have been recomputed according to pricelist <b>%s<b> ",
                                 self.pricelist_id.display_name))

    # @api.onchange('unit_or_part')
    # def onchange_unit_part(self):

    #     for rec in self:
    #         rec.req_quotation_line = False
    #         rec.pricelist_id = False

    #         if rec.unit_or_part == 'unit':

    #             return {'domain': {
    #                 'pricelist_id': [('state', '=', 'approved_finance_head'), ('unit_or_part', '=', 'unit')]}}
    #         else:
    #             return {'domain': {
    #                 'pricelist_id': [('state', '=', 'approved_finance_pic'), ('unit_or_part', '=', 'part')]}}

    @api.onchange('discount_view', 'discount_type')
    def onchange_discount(self):
        for rec in self:
            rec.discount_value = 0.0
            rec.discounted_amount = 0.0
            rec.br_discount = False
            for line in rec.req_quotation_line:
                line.br_dis_value = 0.0
                line.discount_value = 0.0

    @api.onchange('br_discount')
    def onchange_br_discount(self):
        for rec in self.req_quotation_line:
            rec.br_dis_value = 0.0

    @api.onchange('discount_value','req_quotation_line')
    def onchange_discount_value(self):
        if self.discount_value > 0.0:
            for rec in self.req_quotation_line:
                if self.discount_view == 'doc_discount' and self.discount_type == 'fixed':
                    rec.discount_value = self.discount_value/len(self.req_quotation_line)
                    print(rec.discount_value,'//////////////')
                else:
                    rec.discount_value = self.discount_value
                

    @api.onchange('hr_br_id')
    def onchange_br(self):
        company = self.env.user and self.env.user.company_id and \
                  self.env.user.company_id.id or False
        if self.env.user.user_type_id == 'br' and self.env.user.current_bu_br_id:
            hr_br_id = self.hr_br_id.id
            warehouse_id = self.env['stock.warehouse'].search([
                ('hr_bu_id', '=', hr_br_id),
                ('company_id', '=', company)], limit=1)
            self.warehouse_id = warehouse_id and warehouse_id.id or False
        return {'domain': {
            'hr_br_id': [('id', 'in', [br.id for br in self.env.user.hr_br_ids]), ('business_type', '=', 'br')]}}

    @api.onchange('hr_bu_id')
    def onchange_bu(self):
        self.req_quotation_line = False
        company = self.env.user and self.env.user.company_id and \
                  self.env.user.company_id.id or False
        if self.env.user.user_type_id == 'bu' and self.env.user.current_bu_br_id:
            hr_bu_id = self.hr_bu_id.id
            warehouse_id = self.env['stock.warehouse'].search([
                ('hr_bu_id', '=', hr_bu_id),
                ('company_id', '=', company)], limit=1)
            self.warehouse_id = warehouse_id and warehouse_id.id or False
        return {'domain': {
            'hr_bu_id': [('id', 'in', [bu.id for bu in self.env.user.hr_bu_ids]), ('business_type', '=', 'bu')]}}

    @api.model
    def create(self, vals):
        user = self.env.uid
        user_id = self.env['res.users'].browse(user)
        if user_id.user_type_id == 'br':
            bu_code = self.env['business.unit'].browse(vals.get('hr_br_id')).code
        elif user_id.user_type_id == 'bu':
            bu_code = self.env['business.unit'].browse(vals.get('hr_bu_id')).code
        elif user_id.user_type_id == 'cfd':
            bu_code = self.env['business.unit'].browse(vals.get('hr_bu_id')).code
        elif user_id.user_type_id == 'div':
            bu_code = self.env['business.unit'].browse(vals.get('hr_bu_id')).code
        so = self.env['request.quotation'].search([])
        date = fields.Date.today()
        order_date = vals.get('date_order') or datetime.today()

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
        so_id = self.env['request.quotation'].search([('date_order', '>=', starting_date),
                                                      ('date_order', '<=', ending_date),
                                                      ('name', 'like', bu_code),
                                                      ], order="name desc",
                                                     limit=1)
        name = 'RQ' + "-" + str(bu_code) + "-" + str(years) + "-" + str(date_months) + "-00001"
        digit = 0
        if so_id:
            name = so_id.name
            code = name.split('-')
            month = int(code[3])
            if month != int(months):
                name = 'RQ' + "-" + str(bu_code) + "-" + str(years) + "-" + str(date_months) + "-00001"
            elif digit == 0:
                digit = int(code[4])
                digit += 1
                code = '%05d' % (int(digit))
                name = 'RQ' + "-" + str(bu_code) + "-" + str(years) + "-" + str(
                    date_months) + "-" + str(
                    code)

        if vals.get('name', _('New')) == _('New'):
            vals['name'] = name
        result = super(RequestQuotaion, self).create(vals)
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_except_draft_or_cancel(self):
        for rec in self:
            if rec.state not in ('draft', 'cancel'):
                raise UserError(_('You can not delete a confirmed sales quotation.'))

    def action_draft(self):
        quots = self.filtered(lambda s: s.state in ['cancel', 'approved_sale_admin'])
        return quots.write({'state': 'draft'})

    def action_approve(self):
        if not self.req_quotation_line:
            raise UserError(_("Order Line doesn't exit"))
        self.write({'state': 'approved_sale_admin'})
        if self.reman == False:
            return self._create_sale_order()

    def action_cancel(self):
        quots = self.filtered(lambda s: s.state in ['approved_sale_admin'])
        return quots.write({'state': 'cancel'})

    def update_prices(self):
        self.ensure_one()
        lines_to_update = []
        for line in self.req_quotation_line.filtered(lambda line: not line.display_type):
            product = line.product_id.with_context(
                partner=self.partner_id,
                quantity=line.product_uom_qty,
                date=self.date_order,
                pricelist=self.pricelist_id.id,
                uom=line.product_uom.id
            )
            price_unit = self.env['account.tax']._fix_tax_included_price_company(
                line._get_display_price(product), line.product_id.taxes_id, line.tax_id, line.company_id)
            if self.pricelist_id.discount_policy == 'without_discount' and price_unit:
                price_discount_unrounded = self.pricelist_id.get_product_price(product, line.product_uom_qty,
                                                                               self.partner_id, self.date_order,
                                                                               line.product_uom.id)
                discount = max(0, (price_unit - price_discount_unrounded) * 100 / price_unit)
            else:
                discount = 0
            lines_to_update.append((1, line.id, {'price_unit': price_unit, 'discount': discount}))
        self.update({'req_quotation_line': lines_to_update})
        self.show_update_pricelist = False
        self.message_post(body=_("Product prices have been recomputed according to pricelist <b>%s<b> ",
                                 self.pricelist_id.display_name))

    # def action_confirm(self):
    #     return self._create_sale_order()

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
            # print("*"*10)
            # print("request.installment_plan_id",request.installment_plan_id)
            request_new = sale_obj.create({
                'req_quot_id': request.id,
                'date_order': request.date_order,
                'payment_term_id': request.payment_term_id.id,
                'pricelist_id': request.pricelist_id.id,
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
                'note': request.note,
                # 'order_line': request_lines,
                'is_gov_tender': request.is_gov_tender,
                'warehouse_id': request.warehouse_id.id,
                # 'installment_plan_id':request.installment_plan_id.id
            })

    def action_view_sale_order(self):
        action = self.env.ref('request_quotation.action_quot_to_sale').read()[0]

        sales = self.mapped('req_quot_id')
        if len(sales) > 1:
            action['domain'] = [('id', 'in', sales.ids)]
        elif sales:
            action['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
            action['res_id'] = sales.id
        # Prepare the context.

        return action

    def _compute_sale_order_ids(self):
        for order in self:
            request_ids = self.env['sale.order'].search([('req_quot_id', '=', order.id)])
            order.sale_order_count = len(request_ids)

    @api.depends('req_quotation_line.price_total')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.req_quotation_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_untaxed + amount_tax,
            })
    
    #SLO start
    @api.depends('req_quotation_line.tax_id', 'req_quotation_line.price_unit', 'amount_total', 'amount_untaxed')
    def _compute_tax_totals_json(self):
        def compute_taxes(req_quotation_line):
            return req_quotation_line.tax_id._origin.compute_all(**req_quotation_line._prepare_compute_all_values())
        account_move = self.env['account.move']
        for order in self:
            tax_lines_data = account_move._prepare_tax_lines_data_for_totals_from_object(order.req_quotation_line,compute_taxes)
            tax_totals = account_move._get_tax_totals(order.partner_id, tax_lines_data, order.amount_total,order.amount_untaxed, order.currency_id)
            order.tax_totals_json = json.dumps(tax_totals)
    #SLO end

    @api.onchange('partner_id','hr_bu_id','hr_br_id','unit_or_part')
    def onchange_partner_id(self):
        """
        Update the following fields when the partner is changed:
        - Pricelist
        - Payment terms
        - Invoice address
        - Delivery address
        - Sales Team
        """
        if not self.partner_id:
            self.update({
                # 'partner_invoice_id': False,
                # 'partner_shipping_id': False,
                'fiscal_position_id': False,
            })
            return

        self = self.with_company(self.company_id)

        addr = self.partner_id.address_get(['delivery', 'invoice'])
        partner_user = self.partner_id.user_id or self.partner_id.commercial_partner_id.user_id
        pricelists = self.env['product.pricelist'].search([('unit_or_part', '=', self.unit_or_part),('hr_br_ids', 'in', self.hr_br_id.id), ('hr_bu_id', '=', self.hr_bu_id.id)])
        if self.env.user.user_type_id == 'bu':
            pricelists = self.env['product.pricelist'].search([('unit_or_part', '=', self.unit_or_part),('hr_bu_id', '=', self.hr_bu_id.id),('hr_br_ids', '=', False)])
        values = {
            'pricelist_id': pricelists[0].id if pricelists else False,
            'payment_term_id': self.partner_id.property_payment_term_id and self.partner_id.property_payment_term_id.id or False,
            # 'partner_invoice_id': addr['invoice'],
            # 'partner_shipping_id': addr['delivery'],
        }
        user_id = partner_user.id
        if not self.env.context.get('not_self_saleperson'):
            user_id = user_id or self.env.context.get('default_user_id', self.env.uid)
        if user_id and self.user_id.id != user_id:
            values['user_id'] = user_id
        self.update(values)
        return {'domain': {'pricelist_id': [('id', 'in', pricelists.ids)]}}


class RequestQuotaionLine(models.Model):
    _name = 'request.quotation.line'
    _description = 'Quotation Line'

    request_id = fields.Many2one('request.quotation', string='Quotation Reference', required=True, ondelete='cascade',
                                 index=True, copy=False)
    name = fields.Text(string='Description', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    state = fields.Selection(
        related='request_id.state', string='Order Status', copy=False, store=True)

    delivery_date = fields.Date('Production Delivery Date', default=datetime.today())
    estimated_delivery = fields.Date('Estimated Delivery Date')
    price_unit = fields.Float('Unit Price', required=True, digits='Product Price', default=0.0)

    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', store=True)
    price_tax = fields.Float(compute='_compute_amount', string='Total Tax', store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', store=True)

    price_reduce = fields.Float(compute='_compute_price_reduce', string='Price Reduce', digits='Product Price',
                                store=True)
    tax_id = fields.Many2many('account.tax', string='Taxes', context={'active_test': False})
    # price_reduce_taxinc = fields.Monetary(compute='_compute_price_reduce_taxinc', string='Price Reduce Tax inc', store=True)
    # price_reduce_taxexcl = fields.Monetary(compute='_compute_price_reduce_taxexcl', string='Price Reduce Tax excl', store=True)

    discount = fields.Float(string='Discount (%)', digits='Discount', default=0.0)

    product_id = fields.Many2one(
        'product.product', string='Product',
        domain="[('sale_ok', '=', True), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        change_default=True, ondelete='restrict', check_company=True)  # Unrequired company
    product_template_id = fields.Many2one(
        'product.template', string='Product Template',
        related="product_id.product_tmpl_id", domain=[('sale_ok', '=', True)])
    # product_updatable = fields.Boolean(compute='_compute_product_updatable', string='Can Edit Product', default=True)
    product_uom_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', required=True, default=1.0)
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure',
                                  domain="[('category_id', '=', product_uom_category_id)]", ondelete="restrict")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')

    product_custom_attribute_value_ids = fields.One2many('product.attribute.custom.value', 'sale_order_line_id',
                                                         string="Custom Values", copy=True)

    # M2M holding the values of product.attribute with create_variant field set to 'no_variant'
    # It allows keeping track of the extra_price associated to those attribute values and add them to the SO line description
    product_no_variant_attribute_value_ids = fields.Many2many('product.template.attribute.value', string="Extra Values",
                                                              ondelete='restrict')

    salesman_id = fields.Many2one(related='request_id.user_id', store=True, string='Salesperson')
    currency_id = fields.Many2one(related='request_id.currency_id', depends=['request_id.currency_id'], store=True,
                                  string='Currency')
    company_id = fields.Many2one(related='request_id.company_id', string='Company', store=True, index=True)
    order_partner_id = fields.Many2one(related='request_id.partner_id', store=True, string='Customer')
    analytic_line_ids = fields.One2many('account.analytic.line', 'so_line', string="Analytic lines")
    is_expense = fields.Boolean('Is expense',
                                help="Is true if the sales order line comes from an expense or a vendor bills")
    is_downpayment = fields.Boolean(
        string="Is a down payment", help="Down payments are made when creating invoices from a sales order."
                                         " They are not copied when duplicating a sales order.")

    state = fields.Selection(
        related='request_id.state', string='Order Status', copy=False, store=True)

    customer_lead = fields.Float(
        'Lead Time', required=True, default=0.0,
        help="Number of days between the order confirmation and the shipping of the products to the customer")

    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note")], default=False, help="Technical field for UX purpose.")

    product_packaging_id = fields.Many2one('product.packaging', string='Packaging', default=False,
                                           domain="[('sales', '=', True), ('product_id','=',product_id)]",
                                           check_company=True)
    product_packaging_qty = fields.Float('Packaging Quantity')
    discount_type = fields.Selection(related='request_id.discount_type', string='Discount Method')

    discount_value = fields.Float(string='Discount Value')
    br_dis_value = fields.Float(string="BR Discount Value")

    number = fields.Integer(
        compute='_compute_get_number',
        store=True,
    )


    # @api.onchange('unit_or_part')
    # def onchange_bu_product(self):
    #     for rec in self:
    #         if rec.unit_or_part  == 'unit':

    #             return {'domain': {
    #             'pricelist_id': [('state', '=', 'approved_finance_head')]}}
    #         else:
    #             return {'domain': {
    #             'pricelist_id': [('state', '=', 'approved_finance_pic')]}}
    #SLO start
    def _get_discounted_price_unit(self):
        """Inheritable method for getting the unit price after applying
        discount(s).

        :rtype: float
        :return: Unit price after discount(s).
        """
        self.ensure_one()
        if self.request_id.discount_type == 'percentage':
            return self.price_unit * (1 - (self.discount_value + self.br_dis_value) / 100)
        elif self.request_id.discount_type == 'fixed' and self.request_id.discount_view == 'doc_discount':
            # return self.price_unit - self.discount_value - self.br_dis_value
            return self.price_unit - round(self.discount_value/self.product_uom_qty)
        elif self.request_id.discount_type == 'fixed' and self.request_id.discount_view == 'line_discount':
            return self.price_unit - self.discount_value - self.br_dis_value

        return self.price_unit

    def _prepare_compute_all_values(self):
        # Hook method to returns the different argument values for the
        # compute_all method, due to the fact that discounts mechanism
        # is not implemented yet on the purchase orders.
        # This method should disappear as soon as this feature is
        # also introduced like in the sales module.
        self.ensure_one()
        return {
            'price_unit': self._get_discounted_price_unit(),
            'currency': self.request_id.currency_id,
            'quantity': self.product_uom_qty,
            'product': self.product_id,
            'partner': self.request_id.partner_id,
        }
    #SLO end

    @api.depends('sequence', 'request_id')
    def _compute_get_number(self):
        for order in self.mapped('request_id'):
            number = 1
            for line in order.req_quotation_line:
                line.number = number
                number += 1

    # SLO start
    @api.depends('product_uom_qty', 'discount_type', 'discount_value', 'br_dis_value', 'price_unit', 'tax_id')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            br_discount = discount_value = 0.0
            taxes = line.tax_id.compute_all(**line._prepare_compute_all_values())
            discount_value = (
                                 line.discount_value if line.discount_type == 'fixed' else line.price_unit * line.discount_value / 100) * line.product_uom_qty
            br_discount = (
                              line.br_dis_value if line.discount_type == 'fixed' else line.price_unit * line.br_dis_value / 100) * line.product_uom_qty
            price_subtotal = taxes['total_excluded']# - discount_value - br_discount
            line.update({
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'price_subtotal': price_subtotal,
            })
            if self.env.context.get('import_file', False) and not self.env.user.user_has_groups(
                    'account.group_account_manager'):
                line.tax_id.invalidate_cache(['invoice_repartition_line_ids'], [line.tax_id.id])
        # SLO end

    def _get_real_price_currency(self, product, rule_id, qty, uom, pricelist_id):
        """Retrieve the price before applying the pricelist
            :param obj product: object of current product record
            :parem float qty: total quentity of product
            :param tuple price_and_rule: tuple(price, suitable_rule) coming from pricelist computation
            :param obj uom: unit of measure of current order line
            :param integer pricelist_id: pricelist id of sales order"""
        PricelistItem = self.env['product.pricelist.item']
        field_name = 'lst_price'
        currency_id = None
        product_currency = product.currency_id
        if rule_id:
            pricelist_item = PricelistItem.browse(rule_id)
            if pricelist_item.pricelist_id.discount_policy == 'without_discount':
                while pricelist_item.base == 'pricelist' and pricelist_item.base_pricelist_id and pricelist_item.base_pricelist_id.discount_policy == 'without_discount':
                    _price, rule_id = pricelist_item.base_pricelist_id.with_context(uom=uom.id).get_product_price_rule(product, qty, self.order_id.partner_id)
                    pricelist_item = PricelistItem.browse(rule_id)

            if pricelist_item.base == 'standard_price':
                field_name = 'standard_price'
                product_currency = product.cost_currency_id
            elif pricelist_item.base == 'pricelist' and pricelist_item.base_pricelist_id:
                field_name = 'price'
                product = product.with_context(pricelist=pricelist_item.base_pricelist_id.id)
                product_currency = pricelist_item.base_pricelist_id.currency_id
            currency_id = pricelist_item.pricelist_id.currency_id

        if not currency_id:
            currency_id = product_currency
            cur_factor = 1.0
        else:
            if currency_id.id == product_currency.id:
                cur_factor = 1.0
            else:
                cur_factor = currency_id._get_conversion_rate(product_currency, currency_id, self.company_id or self.env.company, self.order_id.date_order or fields.Date.today())

        product_uom = self.env.context.get('uom') or product.uom_id.id
        if uom and uom.id != product_uom:
            # the unit price is in a different uom
            uom_factor = uom._compute_price(1.0, product.uom_id)
        else:
            uom_factor = 1.0

        return product[field_name] * uom_factor * cur_factor, currency_id
    def _get_display_price(self, product):
        # TO DO: move me in master/saas-16 on sale.order
        # awa: don't know if it's still the case since we need the "product_no_variant_attribute_value_ids" field now
        # to be able to compute the full price

        # it is possible that a no_variant attribute is still in a variant if
        # the type of the attribute has been changed after creation.
        no_variant_attributes_price_extra = [
            ptav.price_extra for ptav in self.product_no_variant_attribute_value_ids.filtered(
                lambda ptav:
                ptav.price_extra and
                ptav not in product.product_template_attribute_value_ids
            )
        ]
        if no_variant_attributes_price_extra:
            product = product.with_context(
                no_variant_attributes_price_extra=tuple(no_variant_attributes_price_extra)
            )

        if self.request_id.pricelist_id.discount_policy == 'with_discount':
            return product.with_context(pricelist=self.request_id.pricelist_id.id, uom=self.product_uom.id).price
        product_context = dict(self.env.context, partner_id=self.request_id.partner_id.id,
                               date=self.request_id.date_order, uom=self.product_uom.id)

        final_price, rule_id = self.request_id.pricelist_id.with_context(product_context).get_product_price_rule(
            product or self.product_id, self.product_uom_qty or 1.0, self.request_id.partner_id)
        base_price, currency = self.with_context(product_context)._get_real_price_currency(product, rule_id,
                                                                                           self.product_uom_qty,
                                                                                           self.product_uom,
                                                                                           self.request_id.pricelist_id.id)
        if currency != self.request_id.pricelist_id.currency_id:
            base_price = currency._convert(
                base_price, self.request_id.pricelist_id.currency_id,
                self.request_id.company_id or self.env.company, self.request_id.date_order or fields.Date.today())
        # negative discounts (= surcharge) are included in the display price
        return max(base_price, final_price)

    def _compute_tax_id(self):
        for line in self:
            line = line.with_company(line.company_id)
            fpos = line.request_id.fiscal_position_id or line.request_id.fiscal_position_id.get_fiscal_position(
                line.order_partner_id.id)
            # If company_id is set, always filter taxes by the company
            taxes = line.product_id.taxes_id.filtered(lambda t: t.company_id == line.env.company)
            line.tax_id = fpos.map_tax(taxes)

    @api.onchange('product_id')
    def product_id_change(self):
        if not self.product_id:
            return
        valid_values = self.product_id.product_tmpl_id.valid_product_template_attribute_line_ids.product_template_value_ids
        # remove the is_custom values that don't belong to this template
        for pacv in self.product_custom_attribute_value_ids:
            if pacv.custom_product_template_attribute_value_id not in valid_values:
                self.product_custom_attribute_value_ids -= pacv

        # remove the no_variant attributes that don't belong to this template
        for ptav in self.product_no_variant_attribute_value_ids:
            if ptav._origin not in valid_values:
                self.product_no_variant_attribute_value_ids -= ptav

        vals = {}
        if not self.product_uom or (self.product_id.uom_id.id != self.product_uom.id):
            vals['product_uom'] = self.product_id.uom_id
            vals['product_uom_qty'] = self.product_uom_qty or 1.0

        product = self.product_id.with_context(
            lang=get_lang(self.env, self.request_id.partner_id.lang).code,
            partner=self.request_id.partner_id,
            quantity=vals.get('product_uom_qty') or self.product_uom_qty,
            date=self.request_id.date_order,
            pricelist=self.request_id.pricelist_id.id,
            uom=self.product_uom.id
        )

        vals.update(name=self.get_sale_order_line_multiline_description_sale(product))

        self._compute_tax_id()

        if self.request_id.pricelist_id and self.request_id.partner_id:
            vals['price_unit'] = self.env['account.tax']._fix_tax_included_price_company(
                self._get_display_price(product), product.taxes_id, self.tax_id, self.company_id)
        self.update(vals)

        if product.sale_line_warn != 'no-message':
            if product.sale_line_warn == 'block':
                self.product_id = False

            return {
                'warning': {
                    'title': _("Warning for %s", product.name),
                    'message': product.sale_line_warn_msg,
                }
            }

    @api.onchange('product_id')
    def onchange_bu_product(self):
        for rec in self.request_id:
            return {'domain': {
                'product_id': [('business_id', '=', rec.hr_bu_id.id), ('unit_or_part', '=', rec.unit_or_part)]}}

    def get_sale_order_line_multiline_description_sale(self, product):
        """ Compute a default multiline description for this sales order line.

        In most cases the product description is enough but sometimes we need to append information that only
        exists on the sale order line itself.
        e.g:
        - custom attributes and attributes that don't create variants, both introduced by the "product configurator"
        - in event_sale we need to know specifically the sales order line as well as the product to generate the name:
          the product is not sufficient because we also need to know the event_id and the event_ticket_id (both which belong to the sale order line).
        """
        return product.get_product_multiline_description_sale() + self._get_sale_order_line_multiline_description_variants()

    def _get_sale_order_line_multiline_description_variants(self):
        """When using no_variant attributes or is_custom values, the product
        itself is not sufficient to create the description: we need to add
        information about those special attributes and values.

        :return: the description related to special variant attributes/values
        :rtype: string
        """
        if not self.product_custom_attribute_value_ids and not self.product_no_variant_attribute_value_ids:
            return ""

        name = "\n"

        custom_ptavs = self.product_custom_attribute_value_ids.custom_product_template_attribute_value_id
        no_variant_ptavs = self.product_no_variant_attribute_value_ids._origin

        # display the no_variant attributes, except those that are also
        # displayed by a custom (avoid duplicate description)
        for ptav in (no_variant_ptavs - custom_ptavs):
            name += "\n" + ptav.with_context(lang=self.request_id.partner_id.lang).display_name

        # Sort the values according to _order settings, because it doesn't work for virtual records in onchange
        custom_values = sorted(self.product_custom_attribute_value_ids,
                               key=lambda r: (r.custom_product_template_attribute_value_id.id, r.id))
        # display the is_custom values
        for pacv in custom_values:
            name += "\n" + pacv.with_context(lang=self.request_id.partner_id.lang).display_name

        return name
