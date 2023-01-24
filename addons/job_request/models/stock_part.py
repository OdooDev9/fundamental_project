# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, SUPERUSER_ID, _
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.exceptions import UserError, ValidationError, Warning
import logging
_logger = logging.getLogger(__name__)

class Picking(models.Model):
    _inherit = 'stock.picking'

    def action_cancel_draft(self):
        if not len(self.ids):
            return False
        move_obj = self.env['stock.move']
        for (ids, name) in self.name_get():
            message = _("Picking '%s' has been set in draft state.") % name
            self.message_post(message)
        for pick in self:
            ids2 = [move.id for move in pick.move_lines]
            moves = move_obj.browse(ids2)
            moves.sudo().action_draft()
        return True

    # def button_validate(self):
    # 	self.ensure_one()
    # 	if not self.move_lines and not self.move_line_ids:
    # 		raise UserError(_('Please add some items to move.'))

    # 	# If no lots when needed, raise error
    # 	picking_type = self.picking_type_id
    # 	precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
    # 	no_quantities_done = all(float_is_zero(move_line.qty_done, precision_digits=precision_digits) for move_line in self.move_line_ids.filtered(lambda m: m.state not in ('done', 'cancel')))
    # 	no_reserved_quantities = all(float_is_zero(move_line.product_qty, precision_rounding=move_line.product_uom_id.rounding) for move_line in self.move_line_ids)
    # 	if no_reserved_quantities and no_quantities_done:
    # 		raise UserError(_('You cannot validate a transfer if no quantites are reserved nor done. To force the transfer, switch in edit more and encode the done quantities.'))

    # 	if picking_type.use_create_lots or picking_type.use_existing_lots:
    # 		lines_to_check = self.move_line_ids
    # 		if not no_quantities_done:
    # 			lines_to_check = lines_to_check.filtered(
    # 				lambda line: float_compare(line.qty_done, 0,
    # 										   precision_rounding=line.product_uom_id.rounding)
    # 			)

    # 		for line in lines_to_check:
    # 			product = line.product_id
    # 			if product and product.tracking != 'none':
    # 				if not line.lot_name and not line.lot_id:
    # 					raise UserError(_('You need to supply a Lot/Serial number for product %s.') % product.display_name)

    # 	# Propose to use the sms mechanism the first time a delivery
    # 	# picking is validated. Whatever the user's decision (use it or not),
    # 	# the method button_validate is called again (except if it's cancel),
    # 	# so the checks are made twice in that case, but the flow is not broken
    # 	sms_confirmation = self._check_sms_confirmation_popup()
    # 	if sms_confirmation:
    # 		return sms_confirmation
    # 	if no_quantities_done:
    # 		view = self.env.ref('stock.view_immediate_transfer')
    # 		wiz = self.env['stock.immediate.transfer'].create({'pick_ids': [(4, self.id)]})
    # 		return {
    # 			'name': _('Immediate Transfer?'),
    # 			'type': 'ir.actions.act_window',
    # 			'view_mode': 'form',
    # 			'res_model': 'stock.immediate.transfer',
    # 			'views': [(view.id, 'form')],
    # 			'view_id': view.id,
    # 			'target': 'new',
    # 			'res_id': wiz.id,
    # 			'context': self.env.context,
    # 		}

    # 	if self._get_overprocessed_stock_moves() and not self._context.get('skip_overprocessed_check'):
    # 		view = self.env.ref('stock.view_overprocessed_transfer')
    # 		wiz = self.env['stock.overprocessed.transfer'].create({'picking_id': self.id})
    # 		return {
    # 			'type': 'ir.actions.act_window',
    # 			'view_mode': 'form',
    # 			'res_model': 'stock.overprocessed.transfer',
    # 			'views': [(view.id, 'form')],
    # 			'view_id': view.id,
    # 			'target': 'new',
    # 			'res_id': wiz.id,
    # 			'context': self.env.context,
    # 		}

    # 	# Check backorder should check for other barcodes
    # 	if self._check_backorder():
    # 		return self.action_generate_backorder_wizard()
    # 	self.action_done()
    # 	return
        
class StockMove(models.Model):
    _inherit = "stock.move"
    unbuild_line_id = fields.Many2one('job.request.unbuild.line', 'Unbuild line', index=True)
    damage_line_id = fields.Many2one('damage.component.line', 'Damage line', index=True)
    
    
    def _account_entry_move(self, qty, description, svl_id, cost):
        """ Accounting Valuation Entries """
        self.ensure_one()
        am_vals = []
        if self.product_id.type != 'product':
            # no stock valuation for consumable products
            return am_vals
        if self.restrict_partner_id:
            # if the move isn't owned by the company, we don't make any valuation
            return am_vals

        company_from = self._is_out() and self.mapped('move_line_ids.location_id.company_id') or False
        company_to = self._is_in() and self.mapped('move_line_ids.location_dest_id.company_id') or False

        journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation()
        # Create Journal Entry for products arriving in the company; in case of routes making the link between several
        # warehouse of the same company, the transit location belongs to this company, so we don't need to create accounting entries
        if self._is_in():
            if self.picking_id and self.picking_id.purchase_id:
                po = self.picking_id.purchase_id
                po_line = self.purchase_line_id
                if po.discount_view == 'doc_discount':
                    cost = qty * (po_line.price_unit - (po_line.price_unit * po.discount_value/100)) if po.discount_type == 'percentage' else qty * (po_line.price_unit - po.discount_value)
                if po.discount_view == 'line_discount':
                    cost = qty * (po_line.price_unit * po_line.discount_value/100) if po.discount_type == 'percentage' else qty * (po_line.price_unit - po_line.discount_value)

            if self._is_returned(valued_type='in'):
                am_vals.append(self.with_company(company_to)._prepare_account_move_vals(acc_dest, acc_valuation, journal_id, qty, description, svl_id, cost))
            elif self.picking_id.reman_in_out == True:
                am_vals.append(self.with_company(company_to)._prepare_account_move_vals(acc_src, acc_valuation, journal_id, qty,
                                                                             description, svl_id, 0))

            else:
                am_vals.append(self.with_company(company_to)._prepare_account_move_vals(acc_src, acc_valuation, journal_id, qty, description, svl_id, cost))

        # Create Journal Entry for products leaving the company
        if self._is_out():
            cost = -1 * cost
            if self._is_returned(valued_type='out'):
                am_vals.append(self.with_company(company_from)._prepare_account_move_vals(acc_valuation, acc_src, journal_id, qty, description, svl_id, cost))
            elif self.picking_id.reman_in_out == True:
                am_vals.append(self.with_company(company_from)._prepare_account_move_vals(acc_valuation, acc_dest, journal_id, qty, description, svl_id, 0))

            else:
                am_vals.append(self.with_company(company_from)._prepare_account_move_vals(acc_valuation, acc_dest, journal_id, qty, description, svl_id, cost))
                
        if self.company_id.anglo_saxon_accounting:
            # Creates an account entry from stock_input to stock_output on a dropship move. https://github.com/odoo/odoo/issues/12687
            if self._is_dropshipped():
                if cost > 0:
                    am_vals.append(self.with_company(self.company_id)._prepare_account_move_vals(acc_src, acc_valuation, journal_id, qty, description, svl_id, cost))
                else:
                    cost = -1 * cost
                    am_vals.append(self.with_company(self.company_id)._prepare_account_move_vals(acc_valuation, acc_dest, journal_id, qty, description, svl_id, cost))
            elif self._is_dropshipped_returned():
                if cost > 0:
                    am_vals.append(self.with_company(self.company_id)._prepare_account_move_vals(acc_valuation, acc_src, journal_id, qty, description, svl_id, cost))
                else:
                    cost = -1 * cost
                    am_vals.append(self.with_company(self.company_id)._prepare_account_move_vals(acc_dest, acc_valuation, journal_id, qty, description, svl_id, cost))

        return am_vals
    def action_cancel_quant_create(self):
        quant_obj = self.env['stock.quant']
        for move in self:
            price_unit = move.get_price_unit()
            location = move.location_id
            rounding = move.product_id.uom_id.rounding
            vals = {
                'product_id': move.product_id.id,
                'location_id': location.id,
                'qty': float_round(move.product_uom_qty, precision_rounding=rounding),
                'cost': price_unit,
                'in_date': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                'company_id': move.company_id.id,
            }
            quant_obj.sudo().create(vals)
            return
        
    def action_draft(self):
        res = self.write({'state': 'draft'})
        return res
    
    def _do_unreserve(self):
        for move in self:
            move.move_line_ids.unlink()
            if move.procure_method == 'make_to_order' and not move.move_orig_ids:
                move.state = 'waiting'
            elif move.move_orig_ids and not all(orig.state in ('done', 'cancel') for orig in move.move_orig_ids):
                move.state = 'waiting'
            else:
                move.state = 'confirmed'
        return True

    def _action_cancel(self):
        for move in self:
            move._do_unreserve()
            siblings_states = (move.move_dest_ids.mapped('move_orig_ids') - move).mapped('state')
            if move.propagate_cancel:
                # only cancel the next move if all my siblings are also cancelled
                if all(state == 'cancel' for state in siblings_states):
                    move.move_dest_ids._action_cancel()
            else:
                if all(state in ('done', 'cancel') for state in siblings_states):
                    move.move_dest_ids.write({'procure_method': 'make_to_stock'})
                    move.move_dest_ids.write({'move_orig_ids': [(3, move.id, 0)]})
        
            if move.picking_id.state == 'done' or 'confirmed':
                pack_op = self.env['stock.move'].sudo().search([('picking_id','=',move.picking_id.id),('product_id','=',move.product_id.id)])
                #outgoing
                for pack_op_id in pack_op:
                    if move.picking_id.picking_type_id.code in ['outgoing','internal']:
                        for move_id in pack_op:
                            for line in move_id.move_line_ids:
                                if line.lot_id:
                                    lot_outgoing_quant = self.env['stock.quant'].sudo().search([('product_id','=',move.product_id.id),('location_id','=',line.location_dest_id.id),('lot_id','=',line.lot_id.id)])
                                    lot_source_quant = self.env['stock.quant'].sudo().search([('product_id','=',move.product_id.id),('location_id','=',line.location_id.id),('lot_id','=',line.lot_id.id)])
                                    if lot_outgoing_quant.product_id.tracking == 'lot'or lot_source_quant.product_id.tracking == 'lot':
                                        if lot_outgoing_quant:
                                            for lot in lot_outgoing_quant:
                                                old_qty = lot.quantity
                                                lot.quantity = old_qty - move.product_uom_qty
                                        if lot_source_quant:
                                            for lot in lot_source_quant:
                                                old_qty = lot.quantity
                                                lot.quantity = old_qty + move.product_uom_qty
                                        else:
                                            vals = { 'product_id' :move.product_id.id,
                                                    'location_id':move.location_id.id,
                                                    'lot_id':line.lot_id.id,
                                                    'quantity':move.product_uom_qty,
                                                }
                                            self.env['stock.quant'].create(vals)
                                    else:
                                        if lot_outgoing_quant:
                                            for lot in lot_outgoing_quant:
                                                old_qty = lot.quantity
                                                lot.unlink()
                                                vals = { 'product_id' :move.product_id.id,
                                                        'location_id':move.location_id.id,
                                                        'quantity': old_qty,
                                                        'lot_id':line.lot_id.id,
                                                    }
                                                test = self.env['stock.quant'].create(vals)
                                            
                                else:
                                    if pack_op_id.location_dest_id.usage == 'customer':
                                        outgoing_quant = self.env['stock.quant'].sudo().search([('product_id','=',move.product_id.id),('location_id','=',pack_op_id.location_dest_id.id)])
                                        stock_quant = self.env['stock.quant'].sudo().search([('product_id','=',move.product_id.id),('location_id','=',pack_op_id.location_id.id)])
                                        if outgoing_quant:
                                            old_qty = outgoing_quant[0].quantity
                                            outgoing_quant[0].quantity = old_qty - move.product_uom_qty
                                        if stock_quant:
                                            old_qty = stock_quant[0].quantity
                                            stock_quant[0].quantity = old_qty + move.product_uom_qty
                                    else:
                                        outgoing_quant = self.env['stock.quant'].sudo().search([('product_id','=',move.product_id.id),('location_id','=',pack_op_id.location_id.id)])
                                        if outgoing_quant:
                                            old_qty = outgoing_quant[0].quantity
                                            outgoing_quant[0].quantity = old_qty + move.product_uom_qty
                                        outgoing_customer_quant = self.env['stock.quant'].sudo().search([('product_id','=',move.product_id.id),('location_id','=',pack_op_id.location_dest_id.id)])
                                        if outgoing_customer_quant:
                                            old_qty = outgoing_quant[0].quantity
                                            outgoing_quant[0].quantity = old_qty - move.product_uom_qty

                    if move.picking_id.picking_type_id.code == 'incoming':
                        incoming_quant = self.env['stock.quant'].sudo().search([('product_id','=',move.product_id.id),('location_id','=',pack_op_id.location_dest_id.id)])
                        if incoming_quant:
                            old_qty = incoming_quant[0].quantity
                            incoming_quant[0].quantity = old_qty - move.product_uom_qty
                        incoming_customer_quant = self.env['stock.quant'].sudo().search([('product_id','=',move.product_id.id),('location_id','=',pack_op_id.location_id.id)])
                        if incoming_customer_quant:
                            old_qty = incoming_customer_quant[0].quantity
                            incoming_customer_quant[0].quantity = old_qty + move.product_uom_qty
                    
            self.write({'state': 'cancel', 'move_orig_ids': [(5, 0, 0)]})        
        return True

class stock_move_line(models.Model):
    _inherit = "stock.move.line"
    
    def unlink(self):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for ml in self:
            # Unlinking a move line should unreserve.
            if ml.product_id.type == 'product' and not ml.location_id.should_bypass_reservation() and not float_is_zero(ml.product_qty, precision_digits=precision):

                quant = self.env['stock.quant']._update_reserved_quantity(ml.product_id, ml.location_id, -ml.product_qty, lot_id=ml.lot_id,
                                                                   package_id=ml.package_id, owner_id=ml.owner_id, strict=True)
        return



class StockValuationLayer(models.Model):
    """Stock Valuation Layer"""

    _inherit = 'stock.valuation.layer'

    def create(self,vals):

     
        check_list = isinstance(vals, list)
        if check_list and len(vals) > 0:           
            stock_move_id = self.env['stock.move'].search([('id', '=',vals[0].get('stock_move_id'))])
            # stock_move_id = self.env['stock.move'].search([('id', '=', int(vals[0].get('stock_move_id')))])
            if stock_move_id.picking_id.reman_in_out == True and vals:
                vals[0]['unit_cost'] = 0
                vals[0]['value'] = vals[0].get('quantity') * 0
        return super(StockValuationLayer,self).create(vals)
    
    # def _validate_accounting_entries(self):
    #     am_vals = []
    #     for svl in self:
    #         if not svl.product_id.valuation == 'real_time':
    #             continue
    #         if svl.currency_id.is_zero(svl.value):
    #             continue
    #         if svl.stock_move_id.picking_id.reman_in_out == True:
    #             am_vals += svl.stock_move_id._account_entry_move(svl.quantity, svl.description, svl.id,0)
    #         else:
    #             am_vals += svl.stock_move_id._account_entry_move(svl.quantity, svl.description, svl.id, svl.value)
    #     if am_vals:
    #         account_moves = self.env['account.move'].sudo().create(am_vals)
    #         account_moves._post()
    #     for svl in self:
    #         # Eventually reconcile together the invoice and valuation accounting entries on the stock interim accounts
    #         if svl.company_id.anglo_saxon_accounting:
    #             svl.stock_move_id._get_related_invoices()._stock_account_anglo_saxon_reconcile_valuation(product=svl.product_id)
