# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class DeliveryCarrier(models.TransientModel):
    _name = 'job.order.delivery'
    _description = 'Delivery Carrier Selection Wizard'

    def _get_src_location(self):
        job = self.env['job.request'].browse(self.env.context.get('active_id'))
        location = self.env['stock.location'].search(
            [('hr_bu_id', '=', job.business_id.id), ('part_location', '=', True)], limit=1)
        return location.id

    def _get_dest_location(self):
        location_id = self.env['stock.location'].search([('usage', '=', 'customer')], limit=1).id
        return location_id

    currency_id = fields.Many2one('res.currency', string='Currency',default=lambda self: self.env.company.currency_id.id)
    job_id = fields.Many2one('job.request', required=True, ondelete="cascade")
    company_id = fields.Many2one('res.company', related='job_id.company_id')
    service_charge = fields.Float('Service Charge',digits='Product Price',required=True)
    name = fields.Char('Description')
    location_src_id = fields.Many2one('stock.location', 'Source Location', default=_get_src_location)
    location_dest_id = fields.Many2one('stock.location', 'Destination Location', default=_get_dest_location)

    def button_confirm(self):
        self._create_picking(self.job_id)
        if self.service_charge > 0.0:
            self.create_invoice()
        self.job_id.state = 'cancel'
        return True

    def get_move_lines(self,jobs):
        move_lines = []
        if jobs.state == 'unbuild':
            for unbuild in jobs.unbuild_ids:
                if unbuild.product_id.type in ['consu', 'product']:
                    move_lines.append((0, 0, {
                        'name': unbuild.product_id.name + '-' + jobs.name,
                        'company_id': jobs.company_id.id,
                        'product_id': unbuild.product_id.id,
                        'product_uom': unbuild.product_uom.id,
                        'product_uom_qty': unbuild.product_uom_qty,
                        'partner_id': jobs.partner_id.id,
                        'location_id': self.location_src_id.id,
                        'location_dest_id': self.location_dest_id.id,
                        'origin': jobs.name,
                        'warehouse_id': jobs.warehouse_id.id,
                        'priority': '1',
                    }))
        else:
            move_lines.append((0, 0, {
                'name': jobs.product_id.name + '-' + jobs.name,
                'company_id': jobs.company_id.id,
                'product_id': jobs.product_id.id,
                'product_uom': jobs.product_id.uom_id.id,
                'product_uom_qty': jobs.product_qty,
                'partner_id': jobs.partner_id.id,
                'location_id': self.location_src_id.id,
                'location_dest_id': self.location_dest_id.id,
                'origin': jobs.name,
                'warehouse_id': jobs.warehouse_id.id,
                'priority': '1',
                'price_unit':1,
            }))
        return move_lines

    def _create_picking(self, jobs):
        pick_obj = self.env['stock.picking']
        move_lines = self.get_move_lines(self.job_id)
        picking = pick_obj.create({
            'partner_id': jobs.partner_id.id,
            'origin': jobs.name,
            'move_type': 'direct',
            'company_id': jobs.company_id.id,
            'move_lines': move_lines,
            'picking_type_id': jobs.warehouse_id.out_type_id.id,
            'location_id': self.location_src_id.id,
            'location_dest_id': self.location_dest_id.id,
            'job_re_id': jobs.id,
            'hr_bu_id': jobs.create_uid.hr_bu_id.id,
        })
        picking.action_confirm()
        return picking

    def create_invoice(self):
        invoice_vals = self._prepare_invoice_values(self.job_id, self.name, self.service_charge)

        invoice = self.env['account.move'].with_company(self.env.user.company_id) \
            .sudo().create(invoice_vals).with_user(self.env.uid)
        self.job_id.service_charge = self.service_charge
        return invoice

    def _prepare_invoice_values(self, order, name, amount):
        invoice_vals = {
            'ref': order.name,
            'move_type': 'out_invoice',
            'invoice_origin': order.name,
            'invoice_user_id': self.env.uid,
            'partner_id': order.partner_id.id,
            'currency_id': self.currency_id.id,
            'hr_bu_id': order.business_id.id,
            'job_re_id': order.id,
            'invoice_line_ids': [(0, 0, {
                'name': name,
                'price_unit': amount,
                'quantity': 1.0,
            })],
        }

        return invoice_vals
