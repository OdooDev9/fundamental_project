from operator import mod
from odoo import models, fields, api,_
from datetime import datetime
from odoo.exceptions import UserError
import logging


class trade_in(models.Model):
    _name = 'trade_in.trade_in'
    _description = 'trade_in.trade_in'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order ='id desc'

    def action_move_items(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_account_moves_all_a")
        action['domain'] = [('trade_id', '=', self.id)]
        return action
    def default_bu(self):
        if self.env.user.user_type_id == 'bu':
            return self.env.user.current_bu_br_id
      
    
    def set_bu_domain(self):
        domain = [('id', 'in', [bu.id for bu in self.env.user.hr_bu_ids])]
        return domain



    name = fields.Char(string="Trade In Reference", default="New")
    customer = fields.Many2one('res.partner', string="Customer")
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True,
                                 default=lambda self: self.env.company.id)
    receiving_date = fields.Datetime('Receiving Date', required=True, index=True, copy=False, default=fields.Datetime.now)

    machine_hour = fields.Float(string='Machine Hour')

    hr_bu_id = fields.Many2one('business.unit', string="Trade In BU",default=default_bu,domain=set_bu_domain)
    warehouse_id = fields.Many2one('stock.warehouse')
    product_lines = fields.One2many('trade.line', 'trade_line', string="product_lines")
    create_by =fields.Many2one('res.users',default=lambda self: self.env.user.id)
    state = fields.Selection([
        ('draft', 'DRAFT'),
        ('approved_finance', 'Approved Financce'),
        ('approved_gm_agm','Approved GM/AGM'),
        ('approved_finance_head','Approved Finance & Account Head'),
        ('cancel', 'Cancelled'),
        ('done', 'DONE'),
    ],string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)
    picking_type_id = fields.Many2one('stock.picking.type')
    stock_picking_id =fields.Many2one('stock.picking')
    delivery_count = fields.Integer(string='Receipts', compute='_compute_delivery_count')
    machine_location =fields.Char(string='Machine Location')
    related_bu =fields.Many2one('business.unit',domain=set_bu_domain)
    amount_total = fields.Float(string='Amount Total',compute='_amount_all')
    note =fields.Html(string='Note')
    currency_id = fields.Many2one('res.currency',default=lambda self:self.env.company.currency_id)
    unit_or_part = fields.Selection([('unit', 'Unit'), ('part', 'Spare Part')], string='Units or Parts',default='unit')
    
    @api.onchange('unit_or_part','related_bu')
    def onchange_bu_unit_part(self):
        for rec in self:
            rec.product_lines = False
    
    @api.depends('product_lines.total')
    def _amount_all(self):
        """
		Compute the total amounts of the SO.
		"""
        for order in self:
            amount_total = 0.0
            for line in order.product_lines:
                amount_total += line.total
            order.update({
               
                'amount_total': amount_total,
            })


    def _compute_delivery_count(self):
        for order in self:
            stock_picking = self.env['stock.picking'].search([('trade_in_id', '=', order.id)])
            order.delivery_count = len(stock_picking)

    @api.onchange('hr_bu_id')
    def _onchange_hr_bu(self):
        """Onchange method to update the picking type in purchase order."""
        type_obj = self.env['stock.picking.type']
        company_id = self.env.user and self.env.user.company_id and \
                     self.env.user.company_id.id or False
        for trade in self:
            hr_bu_id = trade.hr_bu_id and trade.hr_bu_id.id or False
            types = type_obj.search([
                ('code', '=', 'incoming'),
                ('warehouse_id.company_id', '=', company_id),
                ('hr_bu_id', '=', hr_bu_id)], limit=1)
            trade.picking_type_id = types and types.id or False
        return {'domain': {'hr_bu_id': [('id', 'in', [bu.id for bu in self.env.user.hr_bu_ids])]}}

    def action_finance_approve(self):
        self.state = 'approved_finance'

    def set_to_draft(self):
        self.state ='draft'
    def action_gm_agm(self):
        self.write({'state':'approved_gm_agm'})

    def cancel_action(self):
        for order in self:
            if order.state not in ('cancel', 'draft', 'trade'):
                raise UserError(_("Unable to cancel this purchase order."))

        self.write({'state': 'cancel'})
    
    def _create_transation(self):
        res = []
        request_id = self
        for line in request_id.product_lines:
            total = self.currency_id._convert(line.total,
                                                self.env.company.currency_id,
                                                self.env.user.company_id,
                                                datetime.today(),)
            move_line = {'name': line.name,
                        'account_id': line.product_id.categ_id.property_stock_account_input_categ_id.id,
                        'partner_id': request_id.related_bu.partner_id and request_id.related_bu.partner_id.id or False,
                        'date': datetime.today(),
                        'amount_currency': line.total,
                        'debit': total,
                        'currency_id': line.currency_id.id,
                        'trade_id': request_id.id, }
            res.append(move_line)

        amount = self.currency_id._convert(request_id.amount_total,
                                                self.env.company.currency_id,
                                                self.env.user.company_id,
                                                datetime.today(),
                                            )
        move_line = {'name': request_id.name,
                     'account_id': request_id.hr_bu_id.aff_account_payable_id.id,
                     'partner_id': request_id.related_bu.partner_id and request_id.related_bu.partner_id.id or False,
                     'date': datetime.today(),
                     'amount_currency': -request_id.amount_total,
                     'credit': amount,
                     'currency_id': request_id.currency_id.id,
                     'trade_id': request_id.id, }
        res.append(move_line)
        line_ids = [(0, 0, l) for l in res]
        journal_id = self.env['account.journal'].search([('type','=','general'),('bu_br_id','=',request_id.hr_bu_id.id)], limit=1)
        if not journal_id:
            raise UserError(_(
                "No journal could be found in %(bu)s for any of those types: %(journal_types)s",
                bu=request_id.hr_bu_id.code,
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
    def action_finance_head(self):
        self.state = 'approved_finance_head'

    def action_confirm(self):
        picking_obj = self.env['stock.picking']
        location_obj = self.env['stock.location'].search([('usage','=','supplier'),('is_trade_in','=','True')])
        # location_obj = self.env['stock.location'].search([('usage','=','customer')])
        move_lines = []
        for request in self:
            request.state = 'done'
            request._create_transation()
            for line in request.product_lines:
                if line.product_id.type in ['consu', 'product']:
                    move_lines.append((0, 0, {
                        'product_id': line.product_id.id,
                        'name': line.product_id.name,
                        'price_unit':line.price,
                        'product_uom_qty': line.qty,
                        'product_uom': line.product_uom.id,
                        'standard_price': line.price,
                        'location_id': self.customer.property_stock_supplier.id,
                        'location_id':location_obj.id,
                        # 'picking_type_id':request.picking_type_id.id,
                        'location_dest_id': request.picking_type_id.default_location_dest_id.id,
                        'warehouse_id':request.picking_type_id.warehouse_id.id,
                        'priority': '1',
                    }))
            picking = picking_obj.create({

                'partner_id': request.customer.id,
                'scheduled_date': datetime.today(),
                'scheduled_date':request.receiving_date,

                'origin': request.name,
                'move_type': 'direct',
                'company_id': self.env.user.company_id.id,
                'move_lines': move_lines,
                'picking_type_id':request.picking_type_id.id,
                'location_id':location_obj.id,
                # 'location_id': self.customer.property_stock_supplier.id,
                'location_dest_id': request.picking_type_id.default_location_dest_id.id,
                'trade_in_id': request.id,
                'hr_bu_id': request.hr_bu_id.id,
                'unit_or_part':request.unit_or_part,
                
            })
            # picking.action_confirm()
            self.stock_picking_id = picking.id



    def unlink(self):
        for line in self:
            if line.state not in ('draft', 'cancel'):
                raise UserError(_('You can not delete traded items. You must first cancel it.'))
        return super(trade_in, self).unlink()

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            seq_date = None
            if 'date_order' in vals:
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date_order']))
            vals['name'] = self.env['ir.sequence'].next_by_code('trade_in.trade_in', sequence_date=seq_date) or '/'
        return super(trade_in, self).create(vals)

    

class trade_line(models.Model):
    _name = 'trade.line'
    _description = "Trade line"

    product_id = fields.Many2one('product.product', string="Product")
    qty = fields.Float(string="Qty", required=True, default=1.0)
    # currency_id = fields.Many2one('res.currency', 'Currency', required=True,
    #                               default=lambda self: self.env.company.currency_id.id)
    # currency_rate = fields.Float(string="Currency Rate", related='currency_id.rate')
    price = fields.Float(string="Price", required=True)
    total = fields.Float(string="Total",compute='compute_total')
    trade_line = fields.Many2one('trade_in.trade_in')
    product_uom = fields.Many2one('uom.uom', string="Unit Of Measure", related="product_id.uom_id")
    serial_number = fields.Char(string="Machine Serial Number")
    working_condition =fields.Char(string="Working Condition")
    check_sheet_att =fields.Binary(string='Check Sheet Attach')
    file_name =fields.Char('File Name')
    inspection_date = fields.Datetime('Inspection Date', required=True, index=True, copy=False, default=fields.Datetime.now)
    currency_id = fields.Many2one(related='trade_line.currency_id',string='Currency')
    name =fields.Char('Description')

    
    @api.onchange('product_id')
    def onchange_bu_product(self):
        for line in self:
            line.name = line.product_id.name
        
        for rec in self.trade_line:
            return {'domain': {'product_id': [('business_id', '=', rec.hr_bu_id.id),('unit_or_part','=',rec.unit_or_part)]}}


    @api.depends('qty', 'price')
    def compute_total(self):
        for rec in self:
            rec.total = rec.qty * rec.price


class stock_picking(models.Model):
    _inherit = 'stock.picking'

    trade_in_id = fields.Many2one('trade_in.trade_in', string='Trade In Ref')

class AccountMoveline(models.Model):
    _inherit = 'account.move.line'

    trade_id = fields.Many2one('trade_in.trade_in')



