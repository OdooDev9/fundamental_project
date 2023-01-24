import base64
import binascii
from odoo import http, _
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
import logging

from odoo.osv.expression import AND, OR


class PortalAccount(CustomerPortal):

	def _prepare_portal_layout_values(self):
		values = super(PortalAccount, self)._prepare_portal_layout_values()
		
		partner = request.env.user.partner_id

		if partner.is_employee:
			approve_count = request.env['sale.target'].sudo().search_count([('state', 'in', ['request_related_dh_approve','request_gm_approve','request_coo_approve','request_ceo_approve']),('approval_person','=',partner.id)])
			values.update({
					'sale_target_approval_count':approve_count,
				})

			personal_count = request.env['personal.sale.target'].sudo().search_count([('state','in',['request_incentive_approved']),('approval_person','=',partner.id)])

			values.update({
					'personal_sale_target_approval_count':personal_count,
				})

			normal_incentive_count = request.env['normal.incentive'].sudo().search_count([('state','in',['request_incentive_approved']),('approval_person','=',partner.id)])

			values.update({
					'normal_incentive_approval_count':normal_incentive_count,
				})

		return values

	def _sale_target_get_page_view_values(self, order, access_token, **kwargs):
	    #
	    def resize_to_48(b64source):
	        if not b64source:
	            b64source = base64.b64encode(Binary().placeholder())
	        return image_process(b64source, size=(48, 48))

	    values = {
	        'order': order,
	        'resize_to_48': resize_to_48,
	    }
	    return self._get_page_view_values(order, access_token, values, 'my_sale_target_history', True, **kwargs)

	def _personal_sale_target_get_page_view_values(self, order, access_token, **kwargs):
	    #
	    def resize_to_48(b64source):
	        if not b64source:
	            b64source = base64.b64encode(Binary().placeholder())
	        return image_process(b64source, size=(48, 48))

	    values = {
	        'order': order,
	        'resize_to_48': resize_to_48,
	    }
	    return self._get_page_view_values(order, access_token, values, 'my_personal_sale_target_history', True, **kwargs)

	def _normal_incentive_get_page_view_values(self, order, access_token, **kwargs):
	    #
	    def resize_to_48(b64source):
	        if not b64source:
	            b64source = base64.b64encode(Binary().placeholder())
	        return image_process(b64source, size=(48, 48))

	    values = {
	        'order': order,
	        'resize_to_48': resize_to_48,
	    }
	    return self._get_page_view_values(order, access_token, values, 'my_normal_incentive_history', True, **kwargs)


	@http.route(['/my/normal/incentive/approval','/my/normal/incentive/approval/page/<int:page>'],type='http',auth='user',website=True)
	def my_normal_incentive_approve(self,page=1,date_begin=None,date_end=None,sortby=None,search_in='name',search=None,**kw):

		values = self._prepare_portal_layout_values()

		logging.info(values)

		partner = request.env.user.partner_id

		NormalIncentive = request.env['normal.incentive'].sudo()

		domain = [
			('state', 'in', ['request_incentive_approved']),('approval_person','=',partner.id)
		]

		searchbar_sortings = {
			'name': {'label': _('Reference'), 'order': 'name desc'},
			'date': {'label': _('Incentive Date'), 'order': 'date desc'},
			'state': {'label': _('Status'), 'order': 'state'},
		}

		searchbar_inputs = {
			'name': {'input': 'name', 'label': _('Search with Name')},
		}

		if search and search_in:
			search_domain = []
			if search_in in ('name'):
				search_domain = OR([search_domain, [('name', 'ilike', search)]])
			domain += search_domain

		if not sortby:
			sortby = 'name'


		sort_order = searchbar_sortings[sortby]['order']

		logging.info("domain --------------")
		logging.info(domain)

		archive_groups = self._get_archive_groups('normal.incentive',domain)

		if date_begin and date_end:
			domain += [('create_date','>',date_begin),('create_date','<=',date_end)]

		

		normal_incentive_count = NormalIncentive.search_count(domain)


		pager = portal_pager(
			url="/my/normal/incentive/approval",
			url_args={'date_begin':date_begin,'date_end':date_end,'sortby':sortby},
			total=normal_incentive_count,
			page=page,
			step=self._items_per_page
			)



		incentives = NormalIncentive.search(domain,order=sort_order,limit=self._items_per_page,offset=pager['offset'])
		request.session['my_normal_incentive_history'] = incentives.ids[:100]

		values.update({
			'date': date_begin,
			'incentives': incentives,
			'page_name': 'normal_incentive_approve',
			'pager': pager,
			'archive_groups': archive_groups,
			'default_url': '/my/normal/incentive/approval',
			'searchbar_sortings': searchbar_sortings,
			'sortby': sortby,
			'searchbar_inputs': searchbar_inputs,
			'search_in':search_in,
			'search':search,
		})
		return request.render("sale_incentive.portal_my_normal_incentive_approval", values)

	@http.route(['/my/personal/sale/target/approval','/my/personal/sale/target/approval/page/<int:page>'],type='http',auth='user',website=True)
	def my_personal_sale_target_approve(self,page=1,date_begin=None,date_end=None,sortby=None,search_in='name',search=None,**kw):

		values = self._prepare_portal_layout_values()

		logging.info(values)

		partner = request.env.user.partner_id

		PersonalSaleTarget = request.env['personal.sale.target'].sudo()

		domain = [
			('state', 'in', ['request_incentive_approved']),('approval_person','=',partner.id)
		]

		searchbar_sortings = {
			'start_date': {'label': _('Start Date'), 'order': 'start_date desc'},
			'end_date': {'label': _('End Date'), 'order': 'end_date desc'},
			'name': {'label': _('Reference'), 'order': 'name desc'},
			'state': {'label': _('Status'), 'order': 'state'},
		}

		searchbar_inputs = {
			'name': {'input': 'name', 'label': _('Search with Name')},
		}

		if search and search_in:
			search_domain = []
			if search_in in ('name'):
				search_domain = OR([search_domain, [('name', 'ilike', search)]])
			domain += search_domain

		if not sortby:
			sortby = 'name'


		sort_order = searchbar_sortings[sortby]['order']

		logging.info("domain --------------")
		logging.info(domain)

		archive_groups = self._get_archive_groups('personal.sale.target',domain)

		if date_begin and date_end:
			domain += [('create_date','>',date_begin),('create_date','<=',date_end)]

		

		personal_sale_target_count = PersonalSaleTarget.search_count(domain)


		pager = portal_pager(
			url="/my/personal/sale/target/approval",
			url_args={'date_begin':date_begin,'date_end':date_end,'sortby':sortby},
			total=personal_sale_target_count,
			page=page,
			step=self._items_per_page
			)



		targets = PersonalSaleTarget.search(domain,order=sort_order,limit=self._items_per_page,offset=pager['offset'])
		request.session['my_personal_sale_target_history'] = targets.ids[:100]

		values.update({
			'date': date_begin,
			'targets': targets,
			'page_name': 'personal_sale_target_approve',
			'pager': pager,
			'archive_groups': archive_groups,
			'default_url': '/my/personal/sale/target/approval',
			'searchbar_sortings': searchbar_sortings,
			'sortby': sortby,
			'searchbar_inputs': searchbar_inputs,
			'search_in':search_in,
			'search':search,
		})
		return request.render("sale_incentive.portal_my_personal_sale_target_approval", values)

	@http.route(['/my/sale/target/approval','/my/sale/target/approval/page/<int:page>'],type='http',auth='user',website=True)
	def my_sale_target_approve(self,page=1,date_begin=None,date_end=None,sortby=None,search_in='name',search=None,**kw):

		values = self._prepare_portal_layout_values()

		logging.info(values)

		partner = request.env.user.partner_id

		SaleTeamTarget = request.env['sale.target'].sudo()

		domain = [
			('state', 'in', ['request_related_dh_approve','request_gm_approve','request_coo_approve','request_ceo_approve']),('approval_person','=',partner.id)
		]

		searchbar_sortings = {
			'start_date': {'label': _('Start Date'), 'order': 'start_date desc'},
			'end_date': {'label': _('End Date'), 'order': 'end_date desc'},
			'name': {'label': _('Reference'), 'order': 'name desc'},
			'state': {'label': _('Status'), 'order': 'state'},
		}

		searchbar_inputs = {
			'name': {'input': 'name', 'label': _('Search with Name')},
		}

		if search and search_in:
			search_domain = []
			if search_in in ('name'):
				search_domain = OR([search_domain, [('name', 'ilike', search)]])
			domain += search_domain

		if not sortby:
			sortby = 'start_date'


		sort_order = searchbar_sortings[sortby]['order']

		archive_groups = self._get_archive_groups('sale.target',domain)

		if date_begin and date_end:
			domain += [('create_date','>',date_begin),('create_date','<=',date_end)]

		sale_team_target_count = SaleTeamTarget.search_count(domain)


		pager = portal_pager(
			url="/my/sale/target/approval",
			url_args={'date_begin':date_begin,'date_end':date_end,'sortby':sortby},
			total=sale_team_target_count,
			page=page,
			step=self._items_per_page
			)



		targets = SaleTeamTarget.search(domain,order=sort_order,limit=self._items_per_page,offset=pager['offset'])
		request.session['my_sale_target_history'] = targets.ids[:100]

		values.update({
			'date': date_begin,
			'targets': targets,
			'page_name': 'sale_target_approve',
			'pager': pager,
			'archive_groups': archive_groups,
			'default_url': '/my/sale/target/approval',
			'searchbar_sortings': searchbar_sortings,
			'sortby': sortby,
			'searchbar_inputs': searchbar_inputs,
			'search_in':search_in,
			'search':search,
		})
		return request.render("sale_incentive.portal_my_sale_target_approval", values)

	@http.route(['/my/normal/incentive/approval/<int:incentive_id>'],type='http',auth='public',website=True)
	def normal_incentive_apporve(self,incentive_id,report_type=None,access_token=None,message=False,download=False,**kw):
		try:
			incentive_sudo = self._document_check_access('normal.incentive', incentive_id, access_token=access_token)
		except (AccessError, MissingError):
			return request.redirect('/my')

		logging.info(access_token)

		values = self._normal_incentive_get_page_view_values(incentive_sudo, access_token, **kw)

		
		return request.render("sale_incentive.portal_normal_incentive", values)

	@http.route(['/my/personal/sale/target/approval/<int:target_id>'],type='http',auth='public',website=True)
	def personal_sale_target_apporve(self,target_id,report_type=None,access_token=None,message=False,download=False,**kw):
		try:
			target_sudo = self._document_check_access('personal.sale.target', target_id, access_token=access_token)
		except (AccessError, MissingError):
			return request.redirect('/my')

		logging.info(access_token)

		values = self._personal_sale_target_get_page_view_values(target_sudo, access_token, **kw)

		
		return request.render("sale_incentive.portal_personal_sale_target", values)

	@http.route(['/my/sale/target/approval/<int:target_id>'],type='http',auth='public',website=True)
	def sale_team_target_apporve(self,target_id,report_type=None,access_token=None,message=False,download=False,**kw):
		try:
			target_sudo = self._document_check_access('sale.target', target_id, access_token=access_token)
		except (AccessError, MissingError):
			return request.redirect('/my')

		logging.info(access_token)

		values = self._sale_target_get_page_view_values(target_sudo, access_token, **kw)

		
		return request.render("sale_incentive.portal_sale_target", values)


	@http.route([
			'/sale/target/approve/<int:target_id>',
			'/sale/target/approve/<int:target_id>/<access_token>',
		],type='http',auth='public',website=True)
	def sale_target_approve(self,target_id,access_token=None,**kw):
		access_token = access_token or request.httprequest.args.get('access_token')
		try:
			target_sudo = request.env['sale.target'].sudo().search([('id','=',target_id)],limit=1)
		except (AccessError, MissingError):
			return {'error': _('Invalid Sale Target.')}

		try:
			if target_sudo.state == 'request_related_dh_approve':
				target_sudo.update({
						'state':'related_dh_approved',
					})
			elif target_sudo.state == 'request_gm_approve':
				target_sudo.update({
						'state':'gm_approved',
					})
			
			elif target_sudo.state == 'request_coo_approve':
				target_sudo.update({
						'state':'coo_approved',
					})

			elif target_sudo.state == 'request_ceo_approve':
				target_sudo.update({
						'state':'ceo_approved',
					})

				# for target in target_sudo.sale_team_target_ids:
				# 	target.update({
				# 			'state':'confirm',
				# 		})

			request.env.cr.commit()
			# body = "Your sale order has been approved"
			# order_sudo.with_context(mail_create_nosubscribe=True).message_post(body=body, message_type='comment', subtype='mt_note')
		except (TypeError, binascii.Error) as e:
			return {'error': _('Invalid data.')}
		return request.redirect('/my/home')


	@http.route(['/sale/target/reject'],type='http',auth='public',methods=['POST'],website=True,csrf=False)
	def reject_sale_target(self,**kw):
		target_id = kw['target_id']
		reason = kw['reason']

		try:
			target_sudo = request.env['sale.target'].sudo().search([('id','=',target_id)],limit=1)
		except (AccessError, MissingError):
			return {'error': _('Invalid Sale Target.')}

		try:
			target_sudo.write({
				'state': 'reject',
			})
			request.env.cr.commit()
			body = "Your sale target has been rejected with the following reason: <br/>" + reason
			target_sudo.with_context(mail_create_nosubscribe=True).message_post(body=body,message_type='comment',subtype='mt_note')

		except (TypeError, binascii.Error) as e:
			return {'error': _('Invalid data.')}
		return request.redirect('/my/home')

	@http.route([
			'/normal/incentive/approve/<int:incentive_id>',
			'/normal/incentive/approve/<int:incentive_id>/<access_token>',
		],type='http',auth='public',website=True)
	def normal_incentive_approve(self,incentive_id,access_token=None,**kw):
		access_token = access_token or request.httprequest.args.get('access_token')
		try:
			incentive_sudo = request.env['normal.incentive'].sudo().search([('id','=',incentive_id)],limit=1)
		except (AccessError, MissingError):
			return {'error': _('Invalid Normal Incentive.')}

		try:
			if incentive_sudo.state == 'request_incentive_approved':
				incentive_sudo.update({
						'state':'incentive_approved',
					})

			request.env.cr.commit()
			# body = "Your sale order has been approved"
			# order_sudo.with_context(mail_create_nosubscribe=True).message_post(body=body, message_type='comment', subtype='mt_note')
		except (TypeError, binascii.Error) as e:
			return {'error': _('Invalid data.')}
		return request.redirect('/my/home')

	@http.route([
			'/personal/sale/target/approve/<int:target_id>',
			'/personal/sale/target/approve/<int:target_id>/<access_token>',
		],type='http',auth='public',website=True)
	def personal_sale_target_approve(self,target_id,access_token=None,**kw):
		access_token = access_token or request.httprequest.args.get('access_token')
		try:
			target_sudo = request.env['personal.sale.target'].sudo().search([('id','=',target_id)],limit=1)
		except (AccessError, MissingError):
			return {'error': _('Invalid Personal Sale Target.')}

		try:
			if target_sudo.state == 'request_incentive_approved':
				target_sudo.update({
						'state':'incentive_approved',
					})

			request.env.cr.commit()
			# body = "Your sale order has been approved"
			# order_sudo.with_context(mail_create_nosubscribe=True).message_post(body=body, message_type='comment', subtype='mt_note')
		except (TypeError, binascii.Error) as e:
			return {'error': _('Invalid data.')}
		return request.redirect('/my/home')


	@http.route(['/personal/sale/target/reject'],type='http',auth='public',methods=['POST'],website=True,csrf=False)
	def reject_sale_target(self,**kw):
		target_id = kw['target_id']
		reason = kw['reason']

		try:
			target_sudo = request.env['personal.sale.target'].sudo().search([('id','=',target_id)],limit=1)
		except (AccessError, MissingError):
			return {'error': _('Invalid Sale Team Target.')}

		try:
			target_sudo.write({
				'state': 'reject',
			})
			request.env.cr.commit()
			body = "Your personal sale target has been rejected with the following reason: <br/>" + reason
			target_sudo.with_context(mail_create_nosubscribe=True).message_post(body=body,message_type='comment',subtype='mt_note')

		except (TypeError, binascii.Error) as e:
			return {'error': _('Invalid data.')}
		return request.redirect('/my/home')


	@http.route(['/normal/incentive/reject'],type='http',auth='public',methods=['POST'],website=True,csrf=False)
	def reject_normal_incentive(self,**kw):
		incentive_id = kw['incentive_id']
		reason = kw['reason']

		try:
			incentive_sudo = request.env['normal.incentive'].sudo().search([('id','=',incentive_id)],limit=1)
		except (AccessError, MissingError):
			return {'error': _('Invalid Normal Incentive.')}

		try:
			incentive_sudo.write({
				'state': 'reject',
			})
			request.env.cr.commit()
			body = "Your personal sale target has been rejected with the following reason: <br/>" + reason
			incentive_sudo.with_context(mail_create_nosubscribe=True).message_post(body=body,message_type='comment',subtype='mt_note')

		except (TypeError, binascii.Error) as e:
			return {'error': _('Invalid data.')}
		return request.redirect('/my/home')