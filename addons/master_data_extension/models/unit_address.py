from odoo import models, fields, api

# DIVISION
class HrRegion(models.Model):
    _name = 'hr.region'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description =  'Region'

    name = fields.Char('State/Region Name',required=True)
    types = fields.Selection([
                            ('state','State'),
                            ('region','Region')],string='Type')
    code = fields.Char('Code',required=True)

# CITY
class HrCity(models.Model):
    _name = 'hr.city'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'City'

    name = fields.Char('City Name',required=True)
    code = fields.Char('Code',required=True)
    region_id = fields.Many2one('hr.region',string='Region',required=True)

# TOWNSHIP
class HrTownship(models.Model):
    _name = 'hr.township'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Township'

    name = fields.Char('Township Name',required=True)
    code = fields.Char('Township Code',required=True)
    city_id = fields.Many2one('hr.city',string='City')
    district_id = fields.Many2one('hr.district',string='District')

# DISTRICT
class TownshipDistrict(models.Model):
    _name = 'hr.district'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'District'

    name = fields.Char('District Name',required=True)

# COUNTRY
class HrCountry(models.Model):
    _name = 'hr.country'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description ='Country'

    name = fields.Char('Country Name',required=True)
    country_code = fields.Char('Country Code',required=True)

# BUSINESS TYPE
class Floor(models.Model):
    _name = 'building.floor'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Floor'

    name =  fields.Char('Floor',required=True)

    _sql_constraints = [
    ('_unique', 'unique (name)', 'No duplication of Floor is allowed')
    ]

# INDUSTRY ZONE
class IndustryZone(models.Model):
    _name = 'industry.zone'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description ='Industry Zone'

    name = fields.Char('Industry Zone',required=True)

