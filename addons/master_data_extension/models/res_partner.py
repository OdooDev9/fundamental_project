from odoo import _, api, fields, models, tools

class ResPartnerInherit(models.Model):
    _inherit = "res.partner"
    city_id = fields.Many2one('hr.city', string="City")
    township_id = fields.Many2one('hr.township', string="TownShip", domain="[('city_id', '=', city_id)]")

    @api.model
    def default_get(self, default_fields):
        
        values = super().default_get(default_fields)
        
        """
        Override to remove auto getting 
        'property_account_payable_id', 'property_account_receivable_id' 
        from company"""
        if self.env.user.user_type_id != "cfd":
            business = self.env['business.unit'].browse(self.env.user.current_bu_br_id.id)
            values['property_account_receivable_id'] = business.property_account_receivable_id.id
            values['property_account_payable_id'] = business.property_account_payable_id.id
        
        return values

    def _display_address(self, without_company=False):

        '''
        The purpose of this function is to build and return an address formatted accordingly to the
        standards of the country where it belongs.
        :param address: browse record of the res.partner to format
        :returns: the address formatted in a display that fit its country habits (or the default ones
            if not country is specified)
        :rtype: string
        '''
        # get the information that will be injected into the display format
        # get the address format
        address_format = self._get_address_format()
        address_format = "%(street)s %(street2)s %(township_name)s %(city_id)s %(country_name)s"
        
        args = {
            'state_code': self.state_id.code or '',
            'state_name': self.state_id.name or '',
            'city_id': self.city_id.name or '',
            'township_name': self.township_id.name or '',
            'country_code': self.country_id.code or '',
            'country_name': self._get_country_name(),
            'company_name': self.commercial_company_name or '',
        }
        for field in self._formatting_address_fields():
            args[field] = getattr(self, field) or ''
        if without_company:
            args['company_name'] = ''
        elif self.commercial_company_name:
            address_format = '%(company_name)s\n' + address_format
        result = address_format % args
        return result
