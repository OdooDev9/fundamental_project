from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class PartOrderMultiInvoice(models.TransientModel):
	_name = "part.order.multi.invoice"
	_description = "Part order multi invoice"

	def create_invoices(self):

		part_order = self.env['part.order'].browse(self._context.get('active_ids',[]))

		inv_obj = self.env['account.move']
		
		count = len(part_order)
		counter = 0
		temp_list = []
		current_customer = -1
		first = True

		for i in range (count): 
			if not first :
				temp_list.append(current_customer)
			else:
				first = False

			current_customer = part_order[i].partner_id.id
			part_ids = []
			inv_line = []
			

			for part in part_order:

				if not part.is_delivered:
					raise UserError(_("Invoice %s is not delivered yet! Invoice cannot create before invoice created")%(part.name))
				
				if part.partner_id.id == current_customer :
					_logger.info(temp_list)
					if len(temp_list)>0:
						f = False
						for v in temp_list:
							if v == current_customer:
								f = True
								break
						if f:
							break

					part_ids.append(part.id)
					counter += 1
					for line in part.part_line:
						account_id = False
						if line.product_id.id:
							account_id = line.product_id.categ_id.property_account_income_categ_id.id
						if not account_id:
							raise UserError(
								_('There is no income account defined for this product: "%s". You may have to install a chart of account from Accounting app, settings menu.') % \
								(line.product_id.name,))
						name = _('Down Payment')
						inv_line.append((0, 0, {
							'name' : line.product_id.name or line.name or " ",
							'account_id': account_id,
							'price_unit': line.price_unit,
							'quantity': line.product_uom_qty,
							'part_ids': [(6, 0, [line.id])],
							'product_uom_id': line.product_id.uom_id.id,
							'product_id': line.product_id.id,
							'tax_ids': [(6, 0, line.tax_id.ids)],
						})) 
			for i in part_ids:
				p = self.env['part.order'].search([('id','=',i)],limit=1)
				if p.invoice_created:
					raise UserError(_("Invoice %s has been created! You cannot create twice")%(p.name))
					continue
				else:
					p.update({'invoice_created':True})

				invoice = inv_obj.create({
						'name': part.client_order_ref or part.name or " ",
						'invoice_origin': part.name or " ",
						'type': 'out_invoice',
						'part_id': i,
						'ref': False,
						'partner_id': current_customer,
						'invoice_line_ids': inv_line,
						'currency_id': part.pricelist_id.currency_id.id,
						'user_id':part.user_id.id,
						'from_part_order' :True,
				})	
		return True
