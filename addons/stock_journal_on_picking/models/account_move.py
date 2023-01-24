from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"


    hr_br_id = fields.Many2one('business.unit', string='Branch',domain="[('business_type','=','br')]")
    hr_bu_id =fields.Many2one('business.unit',string='Business Unit',domain="[('business_type','=','bu')]")
    service_type = fields.Boolean(string="Service Type")
    br_discount_amount = fields.Float()
    discount_view = fields.Selection([('doc_discount', 'Document Discount'), ('line_discount', 'Line Discount')],
                                     string='Discount Type')
    discount_type = fields.Selection([('fixed', 'Fixed'), ('percentage', 'Percentage')], string='Discount Method')
    discount_value = fields.Float(string='Discount Value')
    br_discount = fields.Boolean(string="Branch Discount")
    unit_or_part = fields.Selection([('unit', 'Unit'), ('part', 'Spare Part')], string='Units or Parts')


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    hr_br_id = fields.Many2one('business.unit', string='Branch')
    hr_bu_id = fields.Many2one('business.unit',string='Business Unit')
    # discount_value = fields.Float(string='Discount Value')
    # br_dis_value = fields.Float(string="BR Discount Value")
    # discount_type = fields.Selection([('fixed', 'Fixed'), ('percentage', 'Percentage')], string='Discount Method')

    # @api.onchange('quantity', 'discount', 'price_unit', 'tax_ids', 'discount_value', 'br_dis_value')
    # def _onchange_price_subtotal(self):
    #     for line in self:
    #         if not line.move_id.is_invoice(include_receipts=True):
    #             continue

    #         line.update(line._get_price_total_and_subtotal())
    #         line.update(line._get_fields_onchange_subtotal())
    #         print (line)

    # @api.model
    # def _get_price_total_and_subtotal_model(self, price_unit, quantity, discount, currency, product, partner, taxes,
    #                                         move_type):
    #     ''' This method is used to compute 'price_total' & 'price_subtotal'.

    #     :param price_unit:  The current price unit.
    #     :param quantity:    The current quantity.
    #     :param discount:    The current discount.
    #     :param currency:    The line's currency.
    #     :param product:     The line's product.
    #     :param partner:     The line's partner.
    #     :param taxes:       The applied taxes.
    #     :param move_type:   The type of the move.
    #     :return:            A dictionary containing 'price_subtotal' & 'price_total'.
    #     '''
    #     res = {}

    #     # Compute 'price_subtotal'.
    #     line_discount_price_unit = price_unit * (1 - (discount / 100.0))
    #     subtotal = quantity * line_discount_price_unit
    #     bu_discount = (self.discount_value if self.discount_type == 'fixed' else price_unit * self.discount_value / 100) * quantity
    #     br_discount = (self.br_dis_value if self.discount_type == 'fixed' else price_unit * self.br_dis_value / 100) * quantity

    #     # Compute 'price_total'.
    #     if taxes:
    #         force_sign = -1 if move_type in ('out_invoice', 'in_refund', 'out_receipt') else 1
    #         taxes_res = taxes._origin.with_context(force_sign=force_sign).compute_all(line_discount_price_unit,
    #                                                                                   quantity=quantity,
    #                                                                                   currency=currency,
    #                                                                                   product=product, partner=partner,
    #                                                                                   is_refund=move_type in (
    #                                                                                       'out_refund', 'in_refund'))
    #         res['price_subtotal'] = taxes_res['total_excluded']
    #         res['price_total'] = taxes_res['total_included']
    #     else:
    #         res['price_total'] = res['price_subtotal'] = subtotal
    #     res['price_subtotal'] = res['price_subtotal'] - bu_discount - br_discount
    #     # In case of multi currency, round before it's use for computing debit credit
    #     if currency:
    #         res = {k: currency.round(v) for k, v in res.items()}
    #     return res
