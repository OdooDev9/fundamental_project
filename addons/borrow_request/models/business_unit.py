from pkg_resources import require
from odoo import models, fields, api

class BusinessUnit(models.Model):
    _inherit = 'business.unit'

    @api.model
    def create(self, vals):
        """Create Method to add the HR Branch."""
      
        res = super(BusinessUnit, self).create(vals)
       
        dest_location_id = self.env['stock.location'].search([('hr_bu_id', '=', res.id), ('is_borrow', '=', True)],limit=1)
        if not dest_location_id:
            parent_id = self.env['stock.location'].search([('hr_bu_id', '=', res.id), ('usage', '=', 'internal')])[
                0].location_id
            self.env['stock.location'].create({'name': 'Borrow Location',
                                               'hr_bu_id': res.id,
                                               'usage': 'internal',
                                               'location_id': parent_id.id,
                                               'is_borrow': True,})
        return res
