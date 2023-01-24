from odoo import models
from odoo.http import request


class Http(models.AbstractModel):
    _inherit = 'ir.http'

    def webclient_rendering_context(self):
        """ Overrides community to prevent unnecessary load_menus request """
        custom_context = request.session.get_context()
        return {
            'session_info': self.session_info(),
        }

    def session_info(self):
        ICP = request.env['ir.config_parameter'].sudo()
        User = request.env['res.users']

        if User.has_group('base.group_system'):
            warn_enterprise = 'admin'
        elif User.has_group('base.group_user'):
            warn_enterprise = 'user'
        else:
            warn_enterprise = False

        result = super(Http, self).session_info()
        result['support_url'] = "https://www.odoo.com/help"
        # Block: Enterprise warning about database lifetime
        if warn_enterprise:
            result['warning'] = False
            result['expiration_date'] = False
            result['expiration_reason'] = False

        return result
