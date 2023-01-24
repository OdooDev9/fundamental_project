from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class AccountMove(models.Model):
    _inherit = "sale.order"

    def get_line(self, flag=None):
        line_list = []
        for line in self.order_line:
            if not flag and line.display_type not in ['line_note', 'line_section']:
                line_list.append(line)
            elif flag and line.display_type == flag:
                line_list.append(line)
        return line_list






