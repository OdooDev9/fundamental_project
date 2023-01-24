import odoo
from odoo import http
from odoo.http import request
import json
from odoo_rest_framework import (
    response_json,
    read_serializer,
    login_required,
    report_domain_serialize
)


# sir name
class MasterDataController(http.Controller):
    @login_required('/api/sir-name/list', type='http', auth='public', csrf=False, cors='*', methods=['GET'])
    def sir_name_list(self, **kwargs: dict) -> json:
        try:
            fields = ['name','name_mm']
            sir_name_ids = read_serializer(
                request.env['sir.name'].search_read(report_domain_serialize(kwargs), fields=fields))
            return response_json(success=True, message=None, data=sir_name_ids)
        except Exception as e:
            return response_json(success=False, message=str(e))
