import base64
from io import BytesIO
import qrcode
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class HREmployee(models.Model):
    _inherit = "hr.employee"

    emp_qr_code = fields.Binary(string='QrCode', compute="_generate_qr")

    def _generate_qr(self):
        "method to generate QR code"
        for rec in self:
            if qrcode and base64:

                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=3,
                    border=4,
                )

                qr.add_data("Employee ID : ")
                qr.add_data(rec.emp_id)
                qr.add_data("\n")
                name = ""
                if rec.first_name:
                    name = rec.first_name
                if rec.last_name:
                    name += " " + rec.last_name
                qr.add_data("Name : ")
                qr.add_data(name)
                qr.add_data("\n")
                qr.add_data("Position : ")
                qr.add_data(rec.position_level_id.name)
                qr.add_data("\n")
                qr.add_data("BU/BR : ")
                qr.add_data(rec.holding_id.name)
                qr.add_data("\n")

                qr.make(fit=True)
                img = qr.make_image()
                temp = BytesIO()
                img.save(temp, format="PNG")
                qr_image = base64.b64encode(temp.getvalue())
                rec.update({'emp_qr_code': qr_image})
            else:
                raise UserError(_('Neccessary Requirements To Run This Operation Is Not Satisfied'))
    
    def write(self, vals):
        if vals.get("password"):
            self.user_id.password = vals.get("password")
        return super().write(vals)
