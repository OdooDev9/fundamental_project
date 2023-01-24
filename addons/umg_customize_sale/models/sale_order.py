from odoo import api, models, fields, _
from ast import literal_eval
from odoo.exceptions import UserError, ValidationError
import logging
from datetime import date, datetime, timedelta
from itertools import groupby
import json

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    user_type_id = fields.Selection([('br', 'Branch'), ('bu', 'Business Unit'), ('div', 'DIV'), ('cfd', 'CFD')],
                                    string='User Type', default=lambda self: self.env.user.user_type_id)

    @api.model
    def _get_bu(self):
        if self.env.user.user_type_id == 'bu':
            return self.env.user.current_bu_br_id

    @api.model
    def _get_br(self):
        if self.env.user.user_type_id == 'br':
            return self.env.user.current_bu_br_id

    def _set_bu_domain(self):
        domain = [('id', 'in', [bu.id for bu in self.env.user.hr_bu_ids])]
        return domain

    def _set_br_domain(self):
        domain = [('id', 'in', [br.id for br in self.env.user.hr_br_ids])]
        return domain

    @api.model
    def default_get(self, fields):
        """Method to set default warehouse of user branch."""
        result = super(SaleOrder, self).default_get(fields)
        company = self.env.user.company_id.id
        warehouse_id = ''
        for sale in self:
            if self.env.user.user_type_id == 'bu' and self.env.user.current_bu_br_id.id == sale.hr_bu_id.id:
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

    @api.depends('order_line.price_total', 'discounted_amount')
    def _amount_all(self):
        """
        Compute the total amounts of the SO Testing.
        """
        for order in self:
            amount_untaxed = amount_tax = dis_amount = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_untaxed + amount_tax - order.discounted_amount,
            })

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if not self.warehouse_id:
            self.warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)], limit=1)

    broker_fees_id = fields.Many2one('broker.fees', string='Broker Fees')
    discount_view = fields.Selection([('doc_discount', 'Document Discount'), ('line_discount', 'Line Discount')],
                                     string='Discount Type')
    discount_type = fields.Selection([('fixed', 'Fixed'), ('percentage', 'Percentage')], string='Discount Method')
    discount_value = fields.Float(string='Discount Value', store=True)
    discounted_amount = fields.Float(string='Discounted Amount', readonly=True)
    br_discount = fields.Boolean(string="Branch Discount")
    unit_or_part = fields.Selection([('unit', 'Unit'), ('part', 'Spare Part')], string='Units or Parts')
    br_discount_amount = fields.Float('Br Discount', compute='compute_br_discount')
    # state = fields.Selection(selection_add=[('confirm', 'Confirmed')])
    broker_button = fields.Boolean('Hide Button')
    state = fields.Selection(
        selection_add=[('approved_sale_admin', 'Approved Sale Admin'), ('approved_sale_head', 'Approved Sale Head'),
                       ('approved_finance_head', 'Approved Finance Head'),
                       ('approved_gm_agm', 'Approved GM/AGM'), ('approved_finance_pic', 'Approved F & A PIC'),('approved_finance_head', 'Approved F & A Head'),
                       ('approved_corporate_finance', 'Corp. F & A Head')])

    # state = fields.Selection([
    #     ('draft', 'Quotation'),
    #     ('sent', 'Quotation Sent'),
    #     ('confirm', 'Confirmed'),
    #     ('sale', 'Sales Order'),
    #     ('done', 'Locked'),
    #     ('cancel', 'Cancelled'),
    # ], string='Status', readonly=True, copy=False, index=True, tracking=3, default='draft')
    service_type = fields.Boolean(string='Service Type')
    hr_bu_id = fields.Many2one('business.unit', string='Business Unit', default=_get_bu, domain=_set_bu_domain)
    hr_br_id = fields.Many2one('business.unit', string='Branch', default=_get_br, domain=_set_br_domain)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse',
                                   required=True, readonly=True,
                                   states={'draft': [('readonly', False)], 'sent': [('readonly', False)]})
    is_gov_tender = fields.Boolean(string="Is for Government Tender Sales", default=False)
    due_amount = fields.Float(string='Due Amount',compute='compute_due_amount')
    is_cor = fields.Boolean(string='Is Cor', compute='compute_cor')
    bu_br_user_approve = fields.Boolean(compute='compute_bu_br_user_approve')

    
    def compute_bu_br_user_approve(self):
        for rec in self:
            # if self.env.user.current_bu_br_id and self.env.user.user_type_id == 'br':
            #     rec.bu_br_user_approve = True
                
            if self.env.user.user_type_id == 'bu':
                rec.bu_br_user_approve = True      
            else:
                rec.bu_br_user_approve = False

    # ///For show corporate finance head approve and due amount > 0
    @api.depends('due_amount', 'state')
    def compute_cor(self):
        for rec in self:
            if rec.due_amount > 0 and rec.state == 'approved_gm_agm' and rec.env.user.user_type_id == 'cfd':
                rec.is_cor = True
            else:
                rec.is_cor = False

    # //compute customer due amount depens on payments term
    @api.depends('partner_id')
    def compute_due_amount(self):
        self.due_amount = self.partner_id.total_due
        # partner = self.env['account.move.line'].search([('partner_id', '=', self.partner_id.id)])
        # receivable = partner.filtered(
        #     (lambda x: x.account_id.user_type_id.id == 1 and x.date_maturity and x.date_maturity < date.today()))
        # self.due_amount = 0.0
        # if self.partner_id:
        #     for line in receivable:
        #         self.due_amount += line.balance
        # else:
        #     self.due_amount = 0.0

    def action_s_m_head(self):
        sales = self.filtered(lambda x: x.state == 'draft')
        return sales.write({'state': 'approved_sale_head'})

    def action_sale_admin_approve(self):
        sales = self.filtered(lambda x: x.state == 'draft')
        return sales.write({'state': 'approved_sale_admin'})

    def action_gm_agm_approve(self):
        # sales = self.filtered(lambda x:x.state == 'approved_sale_admin')
        return self.write({'state': 'approved_gm_agm'})

    def action_approve_finance(self):
        # sales = self.filtered(lambda x:x.state == 'approved_sale_admin')
        return self.write({'state': 'approved_finance_head'})

    def action_approve_corporate_finance(self):
        return self.write({'state': 'approved_corporate_finance'})

    def action_gm_agm_credit_approve(self):
        return self.write({'state': 'approved_gm_agm'})

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
        return invoice_vals

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
        so = self.env['sale.order'].search([])
        date = fields.Date.today()
        order_date = vals.get('date_order') or datetime.today()
        so_type = ''
        if vals.get('service_type') == True:
            so_type = 'SV'
        else:
            so_type = 'SO'

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
        so_id = self.env['sale.order'].search([('date_order', '>=', starting_date),
                                               ('date_order', '<=', ending_date),
                                               ('name', 'like', bu_code),
                                               ('name', 'like', so_type),
                                               ], order="name desc",
                                              limit=1)
        # if len(so) != 0:
        #     last_avg_number = self.env['sale.order'].search([])[0].name
        if vals.get('service_type') == True:
            name = 'SV' + "-" + str(bu_code) + "-" + str(years) + "-" + str(date_months) + "-00001"
            digit = 0
            if so_id:
                name = so_id.name
                code = name.split('-')
                month = int(code[3])
                if month != int(months):
                    name = 'SV' + "-" + str(bu_code) + "-" + str(years) + "-" + str(date_months) + "-00001"
                elif digit == 0:
                    digit = int(code[4])
                    digit += 1
                    code = '%05d' % (int(digit))
                    name = 'SV' + "-" + str(bu_code) + "-" + str(years) + "-" + str(
                        date_months) + "-" + str(
                        code)
        else:
            name = 'SO' + "-" + str(bu_code) + "-" + str(years) + "-" + str(date_months) + "-00001"
            digit = 0
            if so_id:
                name = so_id.name
                code = name.split('-')
                month = int(code[3])
                if month != int(months):
                    name = 'SO' + "-" + str(bu_code) + "-" + str(years) + "-" + str(date_months) + "-00001"
                elif digit == 0:
                    digit = int(code[4])
                    digit += 1
                    code = '%05d' % (int(digit))
                    name = 'SO' + "-" + str(bu_code) + "-" + str(years) + "-" + str(
                        date_months) + "-" + str(
                        code)
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = name
        result = super(SaleOrder, self).create(vals)
        return result

    # @api.onchange('unit_or_part')
    # def onchange_unit_part(self):
    #     self.order_line = False
    # @api.onchange('unit_or_part')
    # def onchange_unit_part(self):
    #     for rec in self:
    #         rec.pricelist_id = False
    #         rec.order_line = False

    #         if rec.unit_or_part == 'unit':

    #             return {'domain': {
    #                 'pricelist_id': [('state', '=', 'approved_finance_head'), ('unit_or_part', '=', 'unit')]}}
    #         else:
    #             return {'domain': {
    #                 'pricelist_id': [('state', '=', 'approved_finance_pic'), ('unit_or_part', '=', 'part')]}}

    def action_confirm(self):
        if self.br_discount:
            self.state = 'sale'
        else:
            if self._get_forbidden_state_confirm() & set(self.mapped('state')):
                raise UserError(_(
                    'It is not allowed to confirm an order in the following states: %s'
                ) % (', '.join(self._get_forbidden_state_confirm())))

        for order in self.filtered(lambda order: order.partner_id not in order.message_partner_ids):
            order.message_subscribe([order.partner_id.id])
        self.write(self._prepare_confirmation_values())

        # Context key 'default_name' is sometimes propagated up to here.
        # We don't need it and it creates issues in the creation of linked records.
        context = self._context.copy()
        context.pop('default_name', None)

        self.with_context(context)._action_confirm()
        if self.env.user.has_group('sale.group_auto_done_setting'):
            self.action_done()
        # self.compute_commission()
        return True

    def bu_approved(self):
        if self._get_forbidden_state_confirm() & set(self.mapped('state')):
            raise UserError(_(
                'It is not allowed to confirm an order in the following states: %s'
            ) % (', '.join(self._get_forbidden_state_confirm())))

        for order in self.filtered(lambda order: order.partner_id not in order.message_partner_ids):
            order.message_subscribe([order.partner_id.id])
        self.write(self._prepare_confirmation_values())

        # Context key 'default_name' is sometimes propagated up to here.
        # We don't need it and it creates issues in the creation of linked records.
        context = self._context.copy()
        context.pop('default_name', None)

        self.with_context(context)._action_confirm()
        if self.env.user.has_group('sale.group_auto_done_setting'):
            self.action_done()
        self.compute_commission()
        return True

    @api.depends('order_line.br_dis_value')
    def compute_br_discount(self):
        if self.order_line:
            for rec in self.order_line:
                self.br_discount_amount += (
                                               rec.br_dis_value if rec.discount_type == 'fixed' else rec.price_unit * rec.br_dis_value / 100) * rec.product_uom_qty
        else:
            self.br_discount_amount = 0.0

    @api.onchange('discount_view', 'discount_type')
    def onchange_discount(self):
        for rec in self:
            rec.discount_value = 0.0
            rec.discounted_amount = 0.0
            rec.br_discount = False
            for line in rec.order_line:
                line.br_dis_value = 0.0
                # line.discount_value = 0.0 #SLO remove

    @api.onchange('br_discount')
    def onchange_br_discount(self):
        for rec in self.order_line:
            rec.br_dis_value = 0.0

    @api.onchange('discount_value','order_line')
    def onchange_discount_value(self):
        if self.discount_value > 0.0:
            for rec in self.order_line:
                if self.discount_view == 'doc_discount' and self.discount_type == 'fixed':
                    rec.discount_value = self.discount_value/len(self.order_line)
                else:
                    rec.discount_value = self.discount_value
                # rec.discount_value = self.discount_value

    @api.constrains('order_line')
    def _check_order_line(self):
        if len(self.order_line) < 1:
            raise ValidationError(_("User must be add one product"))

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
        self.order_line = False
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

    def _action_confirm(self):
        result = super(SaleOrder, self)._action_confirm()
        for rec in self.picking_ids:
            rec.write({'hr_br_id': self.hr_br_id.id,
                       'hr_bu_id': self.hr_bu_id.id,
                       'unit_or_part': self.unit_or_part})

    ############################################
    #
    # REPORTING: Intend to Open Partner Ledger view directly from SaleOrder
    #
    ############################################
    def open_partner_ledger(self):

        # <record id="action_account_moves_ledger_partner" model="ir.actions.act_window">
        #     <field name="context">{'journal_type':'general', 'search_default_group_by_partner': 1, 'search_default_posted':1, 'search_default_payable':1, 'search_default_receivable':1, 'search_default_unreconciled':1}</field>
        #     <field name="name">Partner Ledger</field>
        #     <field name="res_model">account.move.line</field>
        #     <field name="domain">[('display_type', 'not in', ('line_section', 'line_note'))]</field>
        #     <field name="view_id" ref="view_move_line_tree_grouped_partner"/>
        #     <field name="search_view_id" ref="view_account_move_line_filter"/>
        #     <field name="view_mode">tree,pivot,graph</field>
        # </record>
        
        # return {
        #     'type': 'ir.actions.act_window',
        #     'name': _('Partner Ledger'),
        #     'res_model': 'account.move.line',
        #     # 'params': {
        #     #     'options': {'partner_ids': [self.partner_id.id]},
        #     #     'ignore_session': 'both',
        #     # },
        #     'context': "{'journal_type':'general', 'search_default_group_by_partner': 1, 'search_default_posted':1, 'search_default_payable':1, 'search_default_receivable':1, 'search_default_unreconciled':1}"
        # }
        return {
            'name': _('Partner Ledger'),
            'view_mode': 'tree',
            'res_model': 'account.move.line',
            'views': [[self.env.ref('account.view_move_line_tree_grouped_partner').id, 'list'],[False, 'form']],
            'type': 'ir.actions.act_window',
            'domain': [('display_type', 'not in', ('line_section', 'line_note')), ('partner_id','=',self.partner_id.id)],
            'context': "\
                {'journal_type':'general', 'search_default_group_by_partner': 1, 'search_default_posted':1,\
                'group_by':['business_id'],\
                'search_default_payable':1, 'search_default_receivable':1, 'search_default_unreconciled':1}\
            "
        } 

    # SLO start
    @api.depends('order_line.tax_id', 'order_line.price_unit', 'amount_total', 'amount_untaxed')
    def _compute_tax_totals_json(self):
        def compute_taxes(order_line):
            # price = order_line.price_unit * (1 - (order_line.discount or 0.0) / 100.0)
            # order = order_line.order_id
            # return order_line.tax_id._origin.compute_all(price, order.currency_id, order_line.product_uom_qty, product=order_line.product_id, partner=order.partner_shipping_id)
            return order_line.tax_id._origin.compute_all(**order_line._prepare_compute_all_values())
        account_move = self.env['account.move']
        for order in self:
            tax_lines_data = account_move._prepare_tax_lines_data_for_totals_from_object(order.order_line, compute_taxes)
            tax_totals = account_move._get_tax_totals(order.partner_id, tax_lines_data, order.amount_total, order.amount_untaxed, order.currency_id)
            order.tax_totals_json = json.dumps(tax_totals)       
    # SLO end

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
        
        super(SaleOrder, self).onchange_partner_id()
        
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

        if self.service_type:
            service_domain = []
            if self.env.user.user_type_id == 'br':
                service_domain = [('unit_or_part', '=', False),('hr_br_ids', 'in', self.hr_br_id.id), ('hr_bu_id', '=', False)]
            if self.env.user.user_type_id == 'bu':
                service_domain = [('unit_or_part', '=', False),('hr_br_ids', '=', False), ('hr_bu_id', '=', self.hr_bu_id.id)]
            pricelists = self.env['product.pricelist'].search(service_domain)
        else:
            p_domain = [('unit_or_part', '=', self.unit_or_part),('unit_or_part', '!=', False)] if self.unit_or_part else [('unit_or_part', '!=', False)]
            if self.hr_br_id:
                p_domain.append(('hr_br_ids', 'in', self.hr_br_id.id))
            if self.hr_br_id:
                p_domain.append(('hr_bu_id', '=', self.hr_bu_id.id))
            pricelists = self.env['product.pricelist'].search(p_domain)

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


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    discount_type = fields.Selection(related='order_id.discount_type', string='Discount Method')

    discount_value = fields.Float(string='Discount Value')
    br_dis_value = fields.Float(string="BR Discount Value")
    # delivery_date = fields.Date('Production Delivery Date', default=fields.Date.today())
    production_delivery_date = fields.Date(default=fields.Date.today())
    estimated_delivery = fields.Date('Estimated Delivery Date')
    number = fields.Integer(
        compute='_compute_get_number',
        store=True,
    )
    hr_br_id = fields.Many2one('business.unit', string='HR Branch', related='order_id.hr_br_id')
    hr_bu_id = fields.Many2one('business.unit', string='HR Business Unit', related='order_id.hr_bu_id')

    # SLO start
    def _get_discounted_price_unit(self):
        """Inheritable method for getting the unit price after applying
        discount(s).

        :rtype: float
        :return: Unit price after discount(s).
        """
        self.ensure_one()
        if self.order_id.discount_type == 'percentage':
            return self.price_unit * (1 - (self.discount_value + self.br_dis_value) / 100)
        elif self.order_id.discount_type == 'fixed' and self.order_id.discount_view == 'doc_discount':
            print('***********************')
            # return self.price_unit - self.discount_value - self.br_dis_value
            return self.price_unit - self.discount_value/self.product_uom_qty
           
        elif self.order_id.discount_type == 'fixed' and self.order_id.discount_view == 'line_discount':
            return self.price_unit - self.discount_value - self.br_dis_value

        # elif self.order_id.discount_type == 'fixed':
        #     return self.price_unit - self.discount_value - self.br_dis_value

        return self.price_unit

    def _prepare_compute_all_values(self):
        # Hook method to returns the different argument values for the
        # compute_all method, due to the fact that discounts mechanism
        # is not implemented yet on the purchase orders.
        # This method should disappear as soon as this feature is
        # also introduced like in the sales module.
        self.ensure_one()
        data ={
            'price_unit': self._get_discounted_price_unit(),
            'currency': self.order_id.currency_id,
            'quantity': self.product_uom_qty,
            'product': self.product_id,
            'partner': self.order_id.partner_id,
        }
        return data
    # SLO end
    def _prepare_invoice_line(self, **optional_values):
        """
        Prepare the dict of values to create the new invoice line for a sales order line.

        :param qty: float quantity to invoice
        :param optional_values: any parameter that should be added to the returned invoice line
        """
        self.ensure_one()
        res = {
            'display_type': self.display_type,
            'sequence': self.sequence,
            'name': self.name,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom.id,
            'quantity': self.qty_to_invoice,
            'discount': self.discount_value, #SLO
            'price_unit': self.price_unit,
            'tax_ids': [(6, 0, self.tax_id.ids)],
            'analytic_tag_ids': [(6, 0, self.analytic_tag_ids.ids)],
            'sale_line_ids': [(4, self.id)],
            'discount_view': self.order_id.discount_view, #SLO
            'br_dis_value': self.br_dis_value,
            'discount_type': self.discount_type,
        }
        if self.order_id.analytic_account_id:
            res['analytic_account_id'] = self.order_id.analytic_account_id.id
        if optional_values:
            res.update(optional_values)
        if self.display_type:
            res['account_id'] = False
        return res

    @api.depends('product_uom_qty', 'discount_type', 'discount_value', 'br_dis_value', 'price_unit', 'tax_id')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            br_discount = discount_value = 0.0
            taxes = line.tax_id.compute_all(**line._prepare_compute_all_values()) #SLO

            discount_value = (
                                 line.discount_value if line.discount_type == 'fixed' else line.price_unit * line.discount_value / 100) * line.product_uom_qty
            br_discount = (
                              line.br_dis_value if line.discount_type == 'fixed' else line.price_unit * line.br_dis_value / 100) * line.product_uom_qty
            price_subtotal = taxes['total_excluded'] #- discount_value - br_discount #SLO
            line.update({
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'price_subtotal': price_subtotal,
            })
            if self.env.context.get('import_file', False) and not self.env.user.user_has_groups(
                    'account.group_account_manager'):
                line.tax_id.invalidate_cache(['invoice_repartition_line_ids'], [line.tax_id.id])

    @api.depends('sequence', 'order_id')
    def _compute_get_number(self):
        for order in self.mapped('order_id'):
            number = 1
            for line in order.order_line:
                line.number = number
                number += 1

    @api.onchange('product_id')
    def onchange_service(self):
        for rec in self.order_id:
            if rec.service_type == True:
                return {'domain': {
                    'product_id': [('business_id', '=', rec.hr_bu_id.id), ('branch_id', '=', rec.hr_br_id.id),
                                   ('detailed_type', '=', 'service')]}}
            else:
                return {'domain': {
                    'product_id': [('business_id', '=', rec.hr_bu_id.id), ('unit_or_part', '=', rec.unit_or_part)]}}
