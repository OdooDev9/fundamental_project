from odoo import models, fields, api, _


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    hr_bu_id = fields.Many2one('business.unit', string='Business Unit/Branch',)

    @api.model
    def create(self, vals):
        """Overridden create to update the branch in location."""
        warehouse = super(StockWarehouse, self).create(vals)
        if warehouse and warehouse.hr_bu_id and \
                warehouse.view_location_id and \
                not warehouse.view_location_id.hr_bu_id:
            warehouse.view_location_id.write({
                'hr_bu_id': warehouse.hr_bu_id.id})
        return warehouse


    # @api.model
    # def create(self, vals):
    #     warehouse = super(StockWarehouse, self).create(vals)
    #     # print("warehouse=======>", warehouse)
    #     sub_location_ids = self.env['stock.location'].search([
    #         ('location_id','=',warehouse.view_location_id.id)
    #     ])
    #     # print("view_location_id==>",  warehouse.view_location_id)
    #     # print("sub_location_ids===>", sub_location_ids)
    #     if warehouse.view_location_id:
    #         warehouse.view_location_id.write({'business_unit_id':vals.get('business_unit_id') })
    #     if sub_location_ids:
    #         sub_location_ids.write({'business_unit_id':vals.get('business_unit_id')})
    #     # print("business_unit_id", vals.get('business_unit_id'))
    #     return warehouse

class StockLocation(models.Model):
    _inherit = 'stock.location'

    hr_bu_id = fields.Many2one('business.unit', string='Business Unit/Branch')
    

class operation_type(models.Model):
    _inherit = "stock.picking.type"
    hr_bu_id =fields.Many2one('business.unit',string='Business Unit/Branch',related='warehouse_id.hr_bu_id')



    

    
