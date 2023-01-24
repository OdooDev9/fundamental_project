# import functools
# import logging
# from odoo.addons.restful.common import invalid_response
# from odoo.http import request

# _logger = logging.getLogger(__name__)

# def validate_token(func):
#     """."""

#     @functools.wraps(func)
#     def wrap(self, *args, **kwargs):
#         """."""
#         access_token = request.httprequest.headers.get("access_token")
#         if not access_token:
#             return invalid_response("access_token_not_found", "missing access token in request header", 401)
#         access_token_data = (
#             request.env["api.access_token"].sudo().search([("token", "=", access_token)], order="id DESC", limit=1)
#         )

#         if access_token_data.find_one_or_create_token(user_id=access_token_data.user_id.id) != access_token:
#             return invalid_response("access_token", "token seems to have expired or invalid", 401)

#         request.session.uid = access_token_data.user_id.id
#         request.uid = access_token_data.user_id.id
#         return func(self, *args, **kwargs)

#     return wrap
