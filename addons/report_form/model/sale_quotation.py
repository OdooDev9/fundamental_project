from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class RequestQuotation(models.Model):
    _inherit = "request.quotation"

    def count_fixed_amount(self, obj=None):
        active_ids = self._context.get('active_ids') if not obj else obj.ids
        advance_id = self.env['request.quotation'].browse(active_ids)
        total = 0
        print("This is advance_id>>>>>>>>>>>>>>>>>>>>>>>>>>", advance_id)
        for record in advance_id:
            total += record.discount_value
        return total

    def count_tax_usd_amount(self, obj=None):
        active_ids = self._context.get('active_ids') if not obj else obj.ids
        advance_id = self.env['request.quotation'].browse(active_ids)
        total = 0
        for record in advance_id:
            if record.pricelist_id.currency_id.name == 'USD':
                total += record.amount_tax
        return total

    def count_tax_mmk_amount(self, obj=None):
        active_ids = self._context.get('active_ids') if not obj else obj.ids
        advance_id = self.env['request.quotation'].browse(active_ids)
        total = 0
        for record in advance_id:
            if record.pricelist_id.currency_id.name == 'MMK':
                total += record.amount_tax
        return total
        
    def get_quotation_ref(self, obj=None):
        active_ids = self._context.get('active_ids') if not obj else obj.ids
        advance_id = self.env['request.quotation'].browse(active_ids)
        ref = []
        for record in advance_id:
            ref.append(record.name)
        return ref