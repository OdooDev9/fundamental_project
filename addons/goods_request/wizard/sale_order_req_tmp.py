from odoo import api, models, fields, _
from ast import literal_eval
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class sale_order_line_request_temp(models.TransientModel):
    _name = 'sale.order.line.request.temp'
    _description = 'sale order line request'

    sale_order_line = fields.Many2one('sale.order.line', string="Order Line")
    sale_order_line_number = fields.Char(string="Order Line Number")
    quote_request_id = fields.Many2one('sale.order.request.temp', string="quote references")
    product_id = fields.Many2one('product.product', string="Product")
    product_uom_qty = fields.Float(string="Quantity")
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure')
    unit_or_part = fields.Selection([('unit', 'Unit'), ('part', 'Spare Part')], string='Units or Parts', default='part')


class sale_order_request_temp(models.TransientModel):
    _name = 'sale.order.request.temp'
    _inherit = ['mail.thread', ]
    _description = 'sale order request'

    def set_br_domain(self):
        domain = [('id', 'in', [br.id for br in self.env.user.hr_br_ids])]
        return domain

    def set_bu_domain(self):
        domain = [('id', 'in', [bu.id for bu in self.env.user.hr_bu_ids])]
        return domain

    quote_name = fields.Many2one('sale.order', string="Sale Order")
    request_date = fields.Datetime(string='Request Date', required=True)
    custom_order_line = fields.One2many('sale.order.line.request.temp', 'quote_request_id', string="Order Lines")
    hr_br_id = fields.Many2one('business.unit', domain=set_br_domain)
    hr_bu_id = fields.Many2one('business.unit', domain=set_bu_domain)
    unit_or_part = fields.Selection([('unit', 'Unit'), ('part', 'Spare Part')], string='Units or Parts', default='part')

    @api.model
    def default_get(self, fields):
        res = super(sale_order_request_temp, self).default_get(fields)
        res.update({'quote_name': self.env.context.get('active_id')})
        sale_order = self.env['sale.order'].browse(self.env.context.get('active_id'))
        line = []
        if sale_order.order_line:
            for lines in sale_order.order_line:
                line.append((0, 0, {'product_id': lines.product_id.id,
                                    'sale_order_line': lines.id,
                                    'sale_order_line_number': str(lines.id),
                                    'product_uom_qty': lines.product_uom_qty,
                                    'product_uom': lines.product_uom.id,

                                    }))
        res.update({'hr_br_id': sale_order.hr_br_id, 'hr_bu_id': sale_order.hr_bu_id, 'custom_order_line': line,
                    'unit_or_part': sale_order.unit_or_part})
        return res

    def split_quotes(self):
        return self._create_request()

    def _create_request(self):
        request_obj = self.env['sale.order.request']

        for request in self:
            request_lines = []

            for line in request.custom_order_line:

                if line.sale_order_line.product_id.type in ['consu', 'product']:
                    request_lines.append((0, 0, {
                        'product_id': line.sale_order_line.product_id.id,
                        'product_uom': line.sale_order_line.product_id.uom_id.id,
                        'product_uom_qty': line.product_uom_qty,
                    }))

            # YZO update sequence code creation
            bu_br_code = self.env.user.current_bu_br_id.name
            gr_id = self.env['sale.order.request'].search([('name', 'like', bu_br_code)],
                                                          order="name desc", limit=1)
            number = bu_br_code + "-GR" + "-000001"
            digit = 0
            if gr_id:
                name = gr_id.name
                code = name.split('-')

                if digit == 0:
                    digit = int(code[2])
                    digit += 1
                    code = '%06d' % (int(digit))
                    number = bu_br_code + "-GR" + "-" + str(code)

            # number = self.env.user.current_bu_br_id.name + '-' + self.env['ir.sequence'].next_by_code(
            #     'sale.order.request') or _('New')
            request_new = request_obj.create({
                'name': number,
                'quote_name': request.quote_name.id,
                'custom_order_line': request_lines,
                'request_date': request.request_date,
                'hr_br_id': request.hr_br_id.id,
                'hr_bu_id': request.hr_bu_id.id,
                'unit_or_part': request.unit_or_part,

            })

            request.quote_name.write({'is_good_request': True})
