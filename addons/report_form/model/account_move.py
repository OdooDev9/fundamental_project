from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    def _lot_serial_number(self):
        number = self.env['stock.production.lot'].search([('name', '=', self.name)])

    def get_line(self, flag=None):
        line_list = []
        for line in self.invoice_line_ids:
            if not flag and line.display_type not in ['line_note', 'line_section']:
                line_list.append(line)
            elif flag and line.display_type == flag:
                line_list.append(line)
        return line_list

    # def get_lot_serial(self, line_product):
    #     print("line_product", line_product)
    #
    #     for pick in self.sale_order_id.picking_ids:
    #         for line in pick.move_line_ids_without_package:
    #             if line.product_id.id == line_product.id:
    #                 return line.lot_id.name
    #     return "line_list"

    def tax_changes(self):
        product = self.env['product.product'].search([('list_price', '=', self.list_price)])
