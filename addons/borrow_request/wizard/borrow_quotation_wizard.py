from odoo.exceptions import UserError, AccessError, ValidationError
from datetime import datetime
from dateutil import relativedelta
from itertools import groupby
from operator import itemgetter
from re import findall as regex_findall, split as regex_split
from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.exceptions import UserError


class BorrowQuotationTmp(models.TransientModel):
    _name = 'borrow.quotation.tmp'
    _inherit = ['mail.thread']
    _description = 'Request Sale Order'

    partner_id = fields.Many2one('res.partner', required=True, domain=[('customer', '=', True)])
    borrow_quot_line = fields.One2many('borrow.quotation.line.tmp', 'quote_request_id', string="Order Lines")
    borrow_request_id = fields.Many2one('borrow.request', string="Borrow Request")
    hr_bu_id = fields.Many2one('business.unit', string="Business Unit")
    hr_br_id = fields.Many2one('business.unit', string="Branch")
    user_id = fields.Many2one('res.users', 'Approval Person', copy=False)
    unit_or_part = fields.Selection([('unit', 'Unit'), ('part', 'Spare Part')], string='Units or Parts')

    @api.model
    def default_get(self, fields):
        res = super(BorrowQuotationTmp, self).default_get(fields)
        # res.update({'quote_name':self.env.context.get('active_id')})
        borrow_request_obj = self.env['borrow.request'].browse(self.env.context.get('active_id'))
        line = []
        if borrow_request_obj.custom_order_line:
            for lines in borrow_request_obj.custom_order_line:
                line.append((0, 0, {
                    'product_id': lines.product_id.id,
                    'product_uom_qty': lines.product_uom_qty,
                    'product_uom': lines.product_uom.id,
                }))
        res.update({
            'borrow_request_id': borrow_request_obj.id,
            'hr_bu_id': borrow_request_obj.hr_bu_id.id,
            'hr_br_id': borrow_request_obj.hr_br_id.id,
            'user_id': borrow_request_obj.user_id.id,
            'unit_or_part': borrow_request_obj.unit_or_part,
            'borrow_quot_line': line})
        return res

    def create_quotation(self):
        request_obj = self.env['sale.order']
        borrow_obj = self.env['borrow.request'].browse(self.env.context.get('active_id'))

        for request in self:
            request_lines = []
            # number = self.env['ir.sequence'].next_by_code('sale.order') or _('New')
            request_new = request_obj.create({

                # 'name' : number,
                'partner_id': self.partner_id.id,
                'is_borrow': True,
                'order_line': [(0, 0, {
                    'product_id': line.product_id.id,
                    'product_uom': line.product_id.uom_id.id,
                    'product_uom_qty': line.product_uom_qty,
                }) for line in request.borrow_quot_line],
                'borrow_request_id': request.borrow_request_id.id,
                'hr_bu_id': request.hr_bu_id.id,
                'hr_br_id':request.hr_br_id.id,
                'user_id': request.user_id.id,
                'warehouse_id': borrow_obj.to_location_id.warehouse_id.id,
                'unit_or_part': borrow_obj.unit_or_part,
            })
            self.borrow_request_id.write({'state': 'quotation'})
            # print('sale order in borrow====>>', request_new)
            # raise UserError('User Error=====================here show')
        return request_new


class BorrowQuotationLineTmp(models.TransientModel):
    _name = 'borrow.quotation.line.tmp'
    _description = 'Borrow Quotation Line'

    sale_order_line = fields.Many2one('sale.order.line', string="Order Line")
    sale_order_line_number = fields.Char(string="Order Line Number")
    quote_request_id = fields.Many2one('borrow.quotation.tmp', string="quote references")
    product_id = fields.Many2one('product.product', string="Product")
    product_uom_qty = fields.Float(string="Quantity")
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure')
