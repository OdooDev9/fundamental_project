from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import get_lang
from odoo.osv import expression
from datetime import datetime
from odoo.tools import float_is_zero, float_compare, float_round


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    purchase_id = fields.Many2one('purchase.quotation', string='Purchase Quotation')

    @api.model
    def create(self, vals):
        company_id = vals.get('company_id', self.default_get(['company_id'])['company_id'])
        self_comp = self.with_company(company_id)
        bu_code = self.env['business.unit'].browse(vals.get('hr_bu_id')).code
        po = self.env['purchase.order'].search([])
        date = fields.Date.today()
        order_date = vals.get('date_order') or datetime.today()
        if type(order_date) != str:
            months = order_date.month
            years = order_date.year
        else:
            months = datetime.strptime(order_date, '%Y-%m-%d %H:%M:%S').month

            years = datetime.strptime(order_date, '%Y-%m-%d %H:%M:%S').year
        date_months = ("0" + str(months)) if months < 10 else months
        last_avg_number = 'New'
        po_id = None
        if len(po) != 0:
            # last_avg_number =self.env['sale.order'].search('name')
            date_start = datetime(int(years), int(months), 1)
            if months == 12:
                date_end = datetime(int(years) + 1, 1, 1)
            else:
                date_end = datetime(int(years), int(months) + 1, 1) - timedelta(days=1)
            last_avg_number = self.env['purchase.order'].search([])[0].name
            starting_date = date_start.replace(second=1)
            ending_date = date_end.replace(hour=23, minute=59, second=59)
            po_id = self.env['purchase.order'].search([('date_order', '>=', starting_date),
                                                       ('date_order', '<=', ending_date),
                                                       ('name', 'like', bu_code)], order="name desc",
                                                      limit=1)
        name = "PO" + "-" + str(bu_code) + "-" + str(years) + "-" + str(date_months) + "-00001"
        if last_avg_number == 'New':
            name = name
        digit = 0
        if po_id:
            name = po_id.name
            code = name.split('-')
            month = int(code[3])
            if month != int(months):
                name = "PO" + "-" + str(bu_code) + "-" + str(years) + "-" + str(date_months) + "-00001"
            elif digit == 0:
                digit = int(code[4])
                digit += 1
                code = '%05d' % (int(digit))
                name = "PO" + "-" + str(bu_code) + "-" + str(years) + "-" + str(date_months) + "-" + str(
                    code)
        if vals.get('name', 'New') == 'New':
            vals['name'] = name
        res = super(PurchaseOrder, self_comp).create(vals)
        return res
