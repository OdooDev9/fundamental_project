from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError, ValidationError
import logging

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    branch_id = fields.Many2one('business.unit',string="Branch Name",domain="[('business_type','=','br')]")


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_view_incentives(self):
        action = self.env.ref('sale_incentive.normal_incentive_action').read()[0]
        action['domain'] = [('sale_order_id', '=', self.sale_order_id.id)]
        return action

    area_sale_manager_id = fields.Many2one('res.partner', string="Area Sale Manager")

    sale_order_id = fields.Many2one('sale.order', string="Sale Order ID")
    is_gov_tender = fields.Boolean(string="Is for Government Tender Sales", default=False)
    incentive_count = fields.Integer(compute='get_incentive_count')

    def _compute_amount(self):
        res = super(AccountMove, self)._compute_amount()
        for move in self:
            if move.payment_state == 'paid':
                incentive_id = self.env['normal.incentive.main'].search(
                    [('invoice_id', '=', move.id)])
                if incentive_id.incentive_definition_id.payment_rule == 'payment':
                    incentive_id.ready_request_payment = True


                # def_id = self.env['normal.incentive.definition'].search(
                #     [('is_active', '=', True), ('sale', '=', 'product'), ('business_id', '=', move.hr_bu_id.id),('is_gov_tender', '=', move.is_gov_tender),('state','=','finance_head')])

                # if def_id:
                #     if def_id.payment_rule in ['payment','both']:
                #         move.compute_incentive()

        return res

    def get_incentive_count(self):
        for rec in self:
            rec.incentive_count = len(self.env['normal.incentive'].search([('sale_order_id','=',rec.sale_order_id.id)]))

    def action_reverse(self):
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_view_account_move_reversal")

        if self.is_invoice():
            action['name'] = _('Credit Note')

        # normal_incentive_obj = self.env['normal.incentive.main'].search([('invoice_id','=',self.id),('state','=','draft')])
        # normal_incentive_obj.unlink()
        normal_incentive_obj = self.env['normal.incentive.main'].search([('invoice_id','=',self.id),('state','=','incentive_approved')])
        for incen in normal_incentive_obj:

            move_line_obj = self.env['account.move.line'].search([('incentive_id','=',incen.id)])
            for move_line in move_line_obj:
                move_obj = self.env['account.move'].search([('line_ids','in',move_line.id)])
                move_obj.button_cancel()
        normal_incentive_obj.unlink()
        incentive_item_obj = self.env['normal.incentive'].search([('invoice_id','=',self.id),('state','=','draft')])
        incentive_item_obj.unlink()
        comission_obj = self.env['sale.commission'].search([('invoice_id','=',self.id),('state','=','draft')])
        comission_obj.unlink()
        return action
    
    def button_draft(self):
        AccountMoveLine = self.env['account.move.line']
        excluded_move_ids = []

        if self._context.get('suspense_moves_mode'):
            excluded_move_ids = AccountMoveLine.search(AccountMoveLine._get_suspense_moves_domain() + [('move_id', 'in', self.ids)]).mapped('move_id').ids

        for move in self:
            if move in move.line_ids.mapped('full_reconcile_id.exchange_move_id'):
                raise UserError(_('You cannot reset to draft an exchange difference journal entry.'))
            if move.tax_cash_basis_rec_id or move.tax_cash_basis_origin_move_id:
                # If the reconciliation was undone, move.tax_cash_basis_rec_id will be empty;
                # but we still don't want to allow setting the caba entry to draft
                # (it'll have been reversed automatically, so no manual intervention is required),
                # so we also check tax_cash_basis_origin_move_id, which stays unchanged
                # (we need both, as tax_cash_basis_origin_move_id did not exist in older versions).
                raise UserError(_('You cannot reset to draft a tax cash basis journal entry.'))
            if move.restrict_mode_hash_table and move.state == 'posted' and move.id not in excluded_move_ids:
                raise UserError(_('You cannot modify a posted entry of this journal because it is in strict mode.'))
            # We remove all the analytics entries for this journal
            move.mapped('line_ids.analytic_line_ids').unlink()

        self.mapped('line_ids').remove_move_reconcile()
        self.write({'state': 'draft', 'is_move_sent': False})

        normal_incentive_obj = self.env['normal.incentive.main'].search([('invoice_id','=',move.id),('state','=','incentive_approved')])
        for incen in normal_incentive_obj:

            move_line_obj = self.env['account.move.line'].search([('incentive_id','=',incen.id)])
            for move_line in move_line_obj:
                move_obj = self.env['account.move'].search([('line_ids','in',move_line.id)])
                move_obj.button_cancel()
        normal_incentive_obj.unlink()
        incentive_item_obj = self.env['normal.incentive'].search([('invoice_id','=',move.id),('state','=','incentive_approved')])
        incentive_item_obj.unlink()
        comission_obj = self.env['sale.commission'].search([('invoice_id','=',move.id),('state','=','draft')])
        comission_obj.unlink()
    def action_post(self):
        if self.payment_id:
            self.payment_id.action_post()
        else:
            self._post(soft=False)

        if self.move_type == 'out_invoice':
            self.compute_commission()
            self.compute_incentive()
            # print(self.compute_commission)
            # def_id = self.env['normal.incentive.definition'].search([('is_active', '=', True), ('sale', '=', 'product'), ('business_id', '=', self.hr_bu_id.id), ('is_gov_tender', '=', self.is_gov_tender),('state','=','finance_head')])
            # # if not def_id:
            # #     self.compute_incentive()
            #     # raise UserError(_('Please define your incentive policy'))

            # if def_id:
            #     if def_id.payment_rule in ['invoice','both']:
                   

        return False
        


    def compute_incentive(self,incentive_id=None,deduct_amount=0.0):
        # res = super(AccountMove, self).write(vals)
        for rec in self:
            # if rec.state == 'posted' and rec.sale_order_id and rec.move_type == 'out_invoice':
            sale_order = rec.sale_order_id
            currency_id = rec.currency_id
            def_id = self.env['normal.incentive.definition'].search([('is_active', '=', True), ('sale', '=', 'product'), ('business_id', '=', rec.hr_bu_id.id), ('is_gov_tender', '=', rec.is_gov_tender),('state','=','finance_head')])
            # currency_id = def_id.currency_id
            if def_id:
                incentive_amount = saleperson_incentive_amount = bu_br_incentive_amount = 0.0
                retain_incentive_amount = manager_incentive_amount = gov_salesperson_percentage = gov_pooling_percentage = 0.0
                #by product
                if def_id.rates_definition == 'product' and def_id.calculation_type == 'fixed_amount':
                    incentive_amount = 0.0
                    saleperson_incentive_amount = 0.0
                    bu_br_incentive_amount = 0.0
                    gov_salesperson_percentage = 0.0
                    gov_pooling_percentage = 0.0
                   
                    all_incentive_rate = 0.0
                    all_pooling_rate =0.0
                    all_gov_saleperson_rate =0.0
                    all_gov_pooling_rate =0.0
                   

                    for line in rec.invoice_line_ids:      
                        amount_by_line,incentive_rate,pooling_rate,retain_rate,gov_salperson_rate,gov_pooling_rate = def_id._check_product_fixed_amount_agent_base(line)
                        
                        incentive_amount_by_line = amount_by_line
                        saleperson_incentive_amount += incentive_amount_by_line
                        bu_br_incentive_amount += incentive_amount_by_line
                        gov_salesperson_percentage += incentive_amount_by_line
                        gov_pooling_percentage += incentive_amount_by_line
                        
                       

                        
                    init_total = saleperson_incentive_amount + bu_br_incentive_amount + gov_salesperson_percentage + gov_pooling_percentage                   
                    all_incentive_rate = saleperson_incentive_amount/init_total * 100
                    all_pooling_rate = bu_br_incentive_amount/init_total * 100
                    all_gov_saleperson_rate = gov_salesperson_percentage/init_total * 100
                    all_gov_pooling_rate = gov_pooling_percentage/init_total * 100
                    
                    
                    if deduct_amount:
                        saleperson_incentive_amount = saleperson_incentive_amount - (deduct_amount * (all_incentive_rate/100))
                        bu_br_incentive_amount = bu_br_incentive_amount - (deduct_amount * (all_pooling_rate/100))
                        gov_salesperson_percentage = gov_salesperson_percentage - (deduct_amount * (all_gov_saleperson_rate/100))
                        gov_pooling_percentage = gov_pooling_percentage - (deduct_amount * (all_gov_pooling_rate/100))
                   
                       

                    # amount =0.0
                    # for rule in def_id.incentive_rule_ids:
                    #     for line in rec.invoice_line_ids:

                    #         if rule.product_id.id == line.product_id.id:
                    #             incentive_amount += rule.incentive_fixed_rate
                                
                elif def_id.rates_definition == 'product' and def_id.calculation_type == 'fixed_percent':
                    incentive_amount = 0.0
                    saleperson_incentive_amount = 0.0
                    bu_br_incentive_amount = 0.0
                    gov_salesperson_percentage = 0.0
                    gov_pooling_percentage = 0.0
                   
                    all_incentive_rate = 0.0
                    all_pooling_rate =0.0
                    all_gov_saleperson_rate =0.0
                    all_gov_pooling_rate =0.0
                    for line in rec.invoice_line_ids:      
                        amount_by_line,incentive_rate,pooling_rate,retain_rate,gov_salperson_rate,gov_pooling_rate = def_id._check_product_base(line)
                        incentive_amount_by_line = amount_by_line
                        saleperson_incentive_amount += incentive_amount_by_line
                        bu_br_incentive_amount += incentive_amount_by_line
                        gov_salesperson_percentage += incentive_amount_by_line
                        gov_pooling_percentage += incentive_amount_by_line
                       
                        
                        # all_incentive_rate = incentive_rate
                        
                        # pooling_amount = amount_by_line
                       
                        # incentive_amount = bu_br_incentive_amount
                        # all_pooling_rate = pooling_rate

                        
                    init_total = saleperson_incentive_amount + bu_br_incentive_amount + gov_salesperson_percentage + gov_pooling_percentage
                   
                    all_incentive_rate = saleperson_incentive_amount/init_total * 100
                    all_pooling_rate = bu_br_incentive_amount/init_total * 100
                    all_gov_saleperson_rate = gov_salesperson_percentage/init_total * 100
                    all_gov_pooling_rate = gov_pooling_percentage/init_total * 100

                    
                    
                    if deduct_amount:
                        saleperson_incentive_amount = saleperson_incentive_amount - (deduct_amount * (all_incentive_rate/100))
                        bu_br_incentive_amount = bu_br_incentive_amount - (deduct_amount * (all_pooling_rate/100))
                        gov_salesperson_percentage = gov_salesperson_percentage - (deduct_amount * (all_gov_saleperson_rate/100))
                        gov_pooling_percentage = gov_pooling_percentage - (deduct_amount * (all_gov_pooling_rate/100))
                   
                    # for rule in def_id.incentive_rule_ids:
                       
                       
                    #     for line in rec.invoice_line_ids:                            
                    #         if rule.product_id.id == line.product_id.id:
                                
                    #             incentive_amount += (line.quantity * line.price_unit) * (rule.incentive_percentage/100)
                                
                elif def_id.rates_definition == 'product' and def_id.calculation_type == 'fixed_percent_multi_agent':
                    incentive_amount = 0.0
                    saleperson_incentive_amount = 0.0
                    bu_br_incentive_amount = 0.0
                    retain_incentive_amount = 0.0
                    gov_salesperson_percentage = 0.0
                    gov_pooling_percentage = 0.0
                    mess = ""

                    # It should be the same percent  in all incentive  
                    all_incentive_rate = 0.0
                    all_pooling_rate = 0.0
                    all_retain_rate = 0.0
                    all_gov_saleperson_rate = 0.0
                    all_gov_pooling_rate = 0.0

                    for line in rec.invoice_line_ids:
                        amount_by_line,incentive_rate,pooling_rate,retain_rate,gov_salperson_rate,gov_pooling_rate = def_id._check_product_base(line)
                        # test_amount += amount_by_line

                        
                        incentive_amount_by_line = amount_by_line * (incentive_rate/100)
                        saleperson_incentive_amount += incentive_amount_by_line
                        all_incentive_rate = incentive_rate
                        
                        pooling_amount = amount_by_line * (pooling_rate/100)
                        bu_br_incentive_amount += pooling_amount
                        all_pooling_rate = pooling_rate

                        retain_amount = amount_by_line * (retain_rate/100)
                        retain_incentive_amount += retain_amount
                        all_retain_rate = retain_rate

                        gov_amount = amount_by_line * (gov_salperson_rate/100)
                        gov_salesperson_percentage += gov_amount
                        all_gov_saleperson_rate = gov_salperson_rate

                        gov_pooling_amount = amount_by_line * (gov_pooling_rate/100)
                        gov_pooling_percentage += gov_pooling_amount
                        all_gov_pooling_rate = gov_pooling_rate

                    init_total = saleperson_incentive_amount + bu_br_incentive_amount + retain_incentive_amount + gov_salesperson_percentage + gov_pooling_percentage
                    all_incentive_rate = saleperson_incentive_amount/init_total * 100
                    all_pooling_rate = bu_br_incentive_amount/init_total * 100
                    all_retain_rate = retain_incentive_amount/init_total * 100
                    all_gov_saleperson_rate = gov_salesperson_percentage/init_total * 100
                    all_gov_pooling_rate = gov_pooling_percentage/init_total * 100

                    if deduct_amount:
                        saleperson_incentive_amount = saleperson_incentive_amount - (deduct_amount * (all_incentive_rate/100))
                        bu_br_incentive_amount = bu_br_incentive_amount - (deduct_amount * (all_pooling_rate/100))
                        retain_incentive_amount = retain_incentive_amount - (deduct_amount * (all_retain_rate/100))
                        gov_salesperson_percentage = gov_salesperson_percentage -  (deduct_amount * (all_gov_saleperson_rate/100))
                        gov_pooling_percentage = gov_pooling_percentage -  (deduct_amount * (all_gov_pooling_rate/100))
                        mess += "deduct_amount %s \n amount_by_line %s \n incentive_amount_by_line %s \n pooling_amount %s \n retain_amount %s \n--------------\n" % (deduct_amount, incentive_amount_by_line, incentive_amount,pooling_amount,retain_amount)
                    mess += "-------------------------TOTAL--------------------------- \n saleperson_incentive_amount %s \n bu_br_incentive_amount %s \n retain_incentive_amount %s "% (saleperson_incentive_amount, bu_br_incentive_amount, retain_incentive_amount)
                    # raise UserError(_(mess))


                    # //Old Code
                
                    # for rule in def_id.incentive_rule_ids:
                    #     for line in rec.invoice_line_ids:                           
                    #     # for line in rec.sale_order_id.order_line:
                    #         if rule.product_id.id == line.product_id.id:
                    #             if def_id.payment_rule == 'both':
                    #                 temp = ((line.quantity * line.price_unit) * (rule.incentive_percentage/100))/2 - deduct_amount
                    #             else:
                    #                 temp = ((line.quantity * line.price_unit) * (rule.incentive_percentage/100)) - deduct_amount


                    #             if rule.salesperson_incentive_rate > 0.0:
                    #                 saleperson_incentive_amount += temp * (rule.salesperson_incentive_rate/100)
                    #                 all_salepeson_amount =saleperson_incentive_amount
                    #                 print(all_salepeson_amount,'Total...................')
                                    
                    #                 print(temp,'incentive rate')
                    #                 print((rule.salesperson_incentive_rate/100))
                    #             if rule.bu_br_rate > 0.0:
                    #                 bu_br_incentive_amount += temp * (rule.bu_br_rate/100)
                    #             if rule.retain_rate > 0.0:
                    #                 retain_incentive_amount += temp * (rule.retain_rate/100)
                    #             if rule.sales_manager_rate > 0.0:
                    #                 if def_id.payment_rule == 'both':
                    #                     manager_incentive_amount += (amount * (rule.sales_manager_rate/100))/2 - deduct_amount
                                       
                    #                 else:
                    #                     manager_incentive_amount += (amount * (rule.sales_manager_rate/100)) - deduct_amount

                    #             if def_id.is_gov_tender and rule.gov_salesperson_percentage > 0.0:
                                 
                    #                 gov_salesperson_percentage += (temp * (rule.gov_salesperson_percentage/100)) 
                                        
                    #             if def_id.is_gov_tender and rule.gov_pooling_percentage > 0.0:
                                   
                    #                 gov_pooling_percentage += (temp * (rule.gov_pooling_percentage/100))
                            

                elif def_id.rates_definition == 'product' and def_id.calculation_type == 'fixed_amount_multi_agent':
                    incentive_amount = 0.0
                    saleperson_incentive_amount = 0.0
                    bu_br_incentive_amount = 0.0
                    retain_incentive_amount = 0.0
                    gov_salesperson_percentage = 0.0
                    gov_pooling_percentage = 0.0
                 

                    # It should be the same percent  in all incentive  
                    all_incentive_rate = 0.0
                    all_pooling_rate = 0.0
                    all_retain_rate = 0.0
                    all_gov_saleperson_rate = 0.0
                    all_gov_pooling_rate = 0.0

                    for line in rec.invoice_line_ids:
                        amount_by_line,incentive_rate,pooling_rate,retain_rate,gov_salperson_rate,gov_pooling_rate = def_id._check_product_fixed_amount_agent_base(line)
                        # test_amount += amount_by_line

                        
                        incentive_amount_by_line = amount_by_line * (incentive_rate/100)
                        saleperson_incentive_amount += incentive_amount_by_line
                        all_incentive_rate = incentive_rate
                        
                        pooling_amount = amount_by_line * (pooling_rate/100)
                        bu_br_incentive_amount += pooling_amount
                        all_pooling_rate = pooling_rate

                        retain_amount = amount_by_line * (retain_rate/100)
                        retain_incentive_amount += retain_amount
                        all_retain_rate = retain_rate

                        gov_amount = amount_by_line * (gov_salperson_rate/100)
                        gov_salesperson_percentage += gov_amount
                        all_gov_saleperson_rate = gov_salperson_rate

                        gov_pooling_amount = amount_by_line * (gov_pooling_rate/100)
                        gov_pooling_percentage += gov_pooling_amount
                        all_gov_pooling_rate = gov_pooling_rate
                    
                    init_total = saleperson_incentive_amount + bu_br_incentive_amount + retain_incentive_amount + gov_salesperson_percentage + gov_pooling_percentage
                    all_incentive_rate = saleperson_incentive_amount/init_total * 100
                    all_pooling_rate = bu_br_incentive_amount/init_total * 100
                    all_retain_rate = retain_incentive_amount/init_total * 100
                    all_gov_saleperson_rate = gov_salesperson_percentage/init_total * 100
                    all_gov_pooling_rate = gov_pooling_percentage/init_total * 100

                    if deduct_amount:
                        saleperson_incentive_amount = saleperson_incentive_amount - (deduct_amount * (all_incentive_rate/100))
                        bu_br_incentive_amount = bu_br_incentive_amount - (deduct_amount * (all_pooling_rate/100))
                        retain_incentive_amount = retain_incentive_amount - (deduct_amount * (all_retain_rate/100))
                        gov_salesperson_percentage = gov_salesperson_percentage -  (deduct_amount * (all_gov_saleperson_rate/100))
                        gov_pooling_percentage = gov_pooling_percentage -  (deduct_amount * (all_gov_pooling_rate/100))
                    
                    # for rule in def_id.incentive_rule_ids:
                    #     # for line in rec.sale_order_id.order_line:
                    #     for line in rec.invoice_line_ids:
                    #         if rule.product_id.id == line.product_id.id:
                    #             if def_id.payment_rule == 'both':

                    #                 temp = (rule.incentive_fixed_rate)/2 - deduct_amount
                    #             else:
                    #                 temp = rule.incentive_fixed_rate - deduct_amount


                    #             if rule.salesperson_incentive_rate > 0.0:
                    #                 saleperson_incentive_amount += temp * (rule.salesperson_incentive_rate/100)
                    #             if rule.bu_br_rate > 0.0:
                    #                 bu_br_incentive_amount += temp * (rule.bu_br_rate/100)
                    #             if rule.retain_rate > 0.0:
                    #                 retain_incentive_amount += temp * (rule.retain_rate/100)
                    #             if rule.sales_manager_rate > 0.0:
                    #                 manager_incentive_amount += (temp * (rule.sales_manager_rate/100)) -deduct_amount
                                   
                    #             if def_id.is_gov_tender and rule.gov_salesperson_percentage > 0.0:
                                   
                    #                 gov_salesperson_percentage += (temp * (rule.gov_salesperson_percentage/100))

                    #             if def_id.is_gov_tender and rule.gov_pooling_percentage > 0.0:
                    #                 gov_pooling_percentage += temp * (rule.gov_pooling_percentage/100)
                #by category
                elif def_id.rates_definition == 'category' and def_id.calculation_type == 'fixed_amount':
                    incentive_amount = 0.0
                    saleperson_incentive_amount = 0.0
                    bu_br_incentive_amount = 0.0
                    gov_salesperson_percentage = 0.0
                    gov_pooling_percentage = 0.0
                   
                    all_incentive_rate = 0.0
                    all_pooling_rate =0.0
                    all_gov_saleperson_rate =0.0
                    all_gov_pooling_rate =0.0
                   

                    for line in rec.invoice_line_ids:      
                        amount_by_line,incentive_rate,pooling_rate,retain_rate,gov_salperson_rate,gov_pooling_rate = def_id._check_product_categ_amount_agent_base(line)
                        
                        incentive_amount_by_line = amount_by_line
                        saleperson_incentive_amount += incentive_amount_by_line
                        bu_br_incentive_amount += incentive_amount_by_line
                        gov_salesperson_percentage += incentive_amount_by_line
                        gov_pooling_percentage += incentive_amount_by_line
                        
                       

                        
                    init_total = saleperson_incentive_amount + bu_br_incentive_amount + gov_salesperson_percentage + gov_pooling_percentage                   
                    all_incentive_rate = saleperson_incentive_amount/init_total * 100
                    all_pooling_rate = bu_br_incentive_amount/init_total * 100
                    all_gov_saleperson_rate = gov_salesperson_percentage/init_total * 100
                    all_gov_pooling_rate = gov_pooling_percentage/init_total * 100
                    
                    
                    if deduct_amount:
                        saleperson_incentive_amount = saleperson_incentive_amount - (deduct_amount * (all_incentive_rate/100))
                        bu_br_incentive_amount = bu_br_incentive_amount - (deduct_amount * (all_pooling_rate/100))
                        gov_salesperson_percentage = gov_salesperson_percentage - (deduct_amount * (all_gov_saleperson_rate/100))
                        gov_pooling_percentage = gov_pooling_percentage - (deduct_amount * (all_gov_pooling_rate/100))

                    
                    # for rule in def_id.incentive_rule_ids:
                    #     for line in rec.invoice_line_ids:
                    #     # for line in rec.sale_order_id.order_line:
                    #         if rule.product_categ_id:
                    #             product_category_ids = self.env['product.category'].search([('id','child_of',rule.product_categ_id.ids)])
                    #             if rule.product_categ_id.id == line.product_id.categ_id.id | line.product_id.categ_id.id in product_category_ids.ids:
                    #                 incentive_amount += rule.incentive_fixed_rate
                                # category_ids = product_category_ids.ids
                                # if rule.product_categ_id not in category_ids:
                                #     category_ids.append(rule.product_categ_id.id)
                                #     print(category_ids,'xxxxxx')
                                # if line.product_id.categ_id.id in category_ids:
                                #     print( line.product_id,'conditionxxxxxx>>>>>>>')
                                #     incentive_amount += rule.incentive_fixed_rate
                                #     print(incentive_amount,'////////////////')
                                #     print(rule.incentive_fixed_rate,'xxxxxxxxxxxx')
                                    # if def_id.payment_rule == 'both':
                                    #     incentive_amount += rule.incentive_fixed_rate/2 - deduct_amount
                                    # else:
                                    #     incentive_amount += rule.incentive_fixed_rate - deduct_amount

                elif def_id.rates_definition == 'category' and def_id.calculation_type == 'fixed_percent':
                    incentive_amount = 0.0
                    saleperson_incentive_amount = 0.0
                    bu_br_incentive_amount = 0.0
                    gov_salesperson_percentage = 0.0
                    gov_pooling_percentage = 0.0
                   
                    all_incentive_rate = 0.0
                    all_pooling_rate =0.0
                    all_gov_saleperson_rate =0.0
                    all_gov_pooling_rate =0.0
                    for line in rec.invoice_line_ids:      
                        amount_by_line,incentive_rate,pooling_rate,retain_rate,gov_salperson_rate,gov_pooling_rate = def_id._check_product_categ_base(line)
                        incentive_amount_by_line = amount_by_line
                        saleperson_incentive_amount += incentive_amount_by_line
                        bu_br_incentive_amount += incentive_amount_by_line
                        gov_salesperson_percentage += incentive_amount_by_line
                        gov_pooling_percentage += incentive_amount_by_line
                        
                    init_total = saleperson_incentive_amount + bu_br_incentive_amount + gov_salesperson_percentage + gov_pooling_percentage
                    all_incentive_rate = saleperson_incentive_amount/init_total * 100
                    all_pooling_rate = bu_br_incentive_amount/init_total * 100
                    all_gov_saleperson_rate = gov_salesperson_percentage/init_total * 100
                    all_gov_pooling_rate = gov_pooling_percentage/init_total * 100

                    
                    
                    if deduct_amount:
                        saleperson_incentive_amount = saleperson_incentive_amount - (deduct_amount * (all_incentive_rate/100))
                        bu_br_incentive_amount = bu_br_incentive_amount - (deduct_amount * (all_pooling_rate/100))
                        gov_salesperson_percentage = gov_salesperson_percentage - (deduct_amount * (all_gov_saleperson_rate/100))
                        gov_pooling_percentage = gov_pooling_percentage - (deduct_amount * (all_gov_pooling_rate/100))
                   
                    # for rule in def_id.incentive_rule_ids:
                    #     for line in rec.invoice_line_ids:  
                    #         amount =  line.quantity * line.price_unit
                    #     # for line in rec.sale_order_id.order_line:
                    #         if rule.product_categ_id:
                    #             product_category_ids = self.env['product.category'].search([('id','child_of',rule.product_categ_id.ids)])
                    #             if rule.product_categ_id.id == line.product_id.categ_id.id | line.product_id.categ_id.id in product_category_ids.ids:
                    #                 incentive_amount += (amount * (rule.incentive_percentage/100))
                                # category_ids = product_category_ids.ids
                                # if rule.product_categ_id not in category_ids:
                                #     category_ids.append(rule.product_categ_id.id)
                                # if line.product_id.categ_id.id in category_ids:
                                #     amount += line.quantity * line.price_unit
                                #     if def_id.payment_rule == 'both':
                                #         incentive_amount += (amount * (rule.incentive_percentage/100))/2 - deduct_amount
                                #     else:
                                #         incentive_amount += (amount * (rule.incentive_percentage/100)) - deduct_amount

                elif def_id.rates_definition == 'category' and def_id.calculation_type == 'fixed_percent_multi_agent':
                    print("condition ==> ef_id.rates_definition == 'category' and def_id.calculation_type == 'fixed_percent_multi_agent'")
                    incentive_amount = 0.0
                    saleperson_incentive_amount = 0.0
                    bu_br_incentive_amount = 0.0
                    retain_incentive_amount = 0.0
                    gov_salesperson_percentage = 0.0
                    gov_pooling_percentage = 0.0
                    manager_incentive_amount = 0.0
                    mess = ""

                    # It should be the same percent  in all incentive  
                    all_incentive_rate = 0.0
                    all_pooling_rate = 0.0
                    all_retain_rate = 0.0
                    all_gov_saleperson_rate =0.0
                    all_gov_pooling_rate = 0.0


                    for line in rec.invoice_line_ids:
                        amount,amount_by_line,incentive_rate,pooling_rate,retain_rate,gov_saleperson_rate,gov_pooling_rate,manager_rate = def_id._check_product_categ_base(line)
                        # test_amount += amount_by_line

                        
                        incentive_amount_by_line = amount_by_line * (incentive_rate/100)
                        saleperson_incentive_amount += incentive_amount_by_line
                        all_incentive_rate = incentive_rate
                        
                        pooling_amount = amount_by_line * (pooling_rate/100)
                        bu_br_incentive_amount += pooling_amount
                        all_pooling_rate = pooling_rate

                        retain_amount = amount_by_line * (retain_rate/100)
                        retain_incentive_amount += retain_amount
                        all_retain_rate = retain_rate
                        # print("deduct_amount ====>", deduct_amount)
                        # print("line ==========+++>", amount_by_line)
                        # print("incentive_rate==>", incentive_rate)
                        # print("pooling_rate ==>", pooling_rate)
                        # print("retain_rate ==>", retain_rate)

                        gov_amount = amount_by_line * (gov_saleperson_rate/100)
                        gov_salesperson_percentage += gov_amount
                        all_gov_saleperson_rate = gov_saleperson_rate

                        gov_pooling_amount = amount_by_line * (gov_pooling_rate/100)
                        gov_pooling_percentage += gov_pooling_amount
                        all_gov_pooling_rate = gov_pooling_rate


                        manager_incentive_amount += amount * (manager_rate/100)
                    
                    init_total = saleperson_incentive_amount + bu_br_incentive_amount + retain_incentive_amount + gov_salesperson_percentage + gov_pooling_percentage
                    all_incentive_rate = saleperson_incentive_amount/init_total * 100
                    all_pooling_rate = bu_br_incentive_amount/init_total * 100
                    all_retain_rate = retain_incentive_amount/init_total * 100
                    all_gov_saleperson_rate = gov_salesperson_percentage/init_total * 100
                    all_gov_pooling_rate = gov_pooling_percentage/init_total * 100

                    if deduct_amount:
                        saleperson_incentive_amount = saleperson_incentive_amount - (deduct_amount * (all_incentive_rate/100))
                        bu_br_incentive_amount = bu_br_incentive_amount - (deduct_amount * (all_pooling_rate/100))
                        retain_incentive_amount = retain_incentive_amount - (deduct_amount * (all_retain_rate/100))
                        gov_salesperson_percentage = gov_salesperson_percentage -  (deduct_amount * (all_gov_saleperson_rate/100))
                        gov_pooling_percentage = gov_pooling_percentage -  (deduct_amount * (all_gov_pooling_rate/100))
                        manager_incentive_amount = manager_incentive_amount - deduct_amount
                        mess += "deduct_amount %s \n amount_by_line %s \n incentive_amount_by_line %s \n pooling_amount %s \n retain_amount %s \n--------------\n" % (deduct_amount, incentive_amount_by_line, incentive_amount,pooling_amount,retain_amount)
                    mess += "-------------------------TOTAL--------------------------- \n saleperson_incentive_amount %s \n bu_br_incentive_amount %s \n retain_incentive_amount %s "% (saleperson_incentive_amount, bu_br_incentive_amount, retain_incentive_amount)
                    # raise UserError(_(mess))

                                        

                elif def_id.rates_definition == 'category' and def_id.calculation_type == 'fixed_amount_multi_agent':
                    print("condition ==> ef_id.rates_definition == 'category' and def_id.calculation_type == 'fixed_percent_multi_agent'")
                    incentive_amount = 0.0
                    saleperson_incentive_amount = 0.0
                    bu_br_incentive_amount = 0.0
                    retain_incentive_amount = 0.0
                    gov_salesperson_percentage = 0.0
                    gov_pooling_percentage = 0.0
                    mess = ""

                    # It should be the same percent  in all incentive  
                    all_incentive_rate = 0.0
                    all_pooling_rate = 0.0
                    all_retain_rate = 0.0
                    all_gov_saleperson_rate =0.0
                    all_gov_pooling_rate = 0.0

                    for line in rec.invoice_line_ids:
                        amount_by_line,incentive_rate,pooling_rate,retain_rate,gov_saleperson_rate,gov_pooling_rate = def_id._check_product_categ_amount_agent_base(line)

                        
                        incentive_amount_by_line = amount_by_line * (incentive_rate/100)
                        saleperson_incentive_amount += incentive_amount_by_line
                        all_incentive_rate = incentive_rate
                        
                        pooling_amount = amount_by_line * (pooling_rate/100)
                        bu_br_incentive_amount += pooling_amount
                        all_pooling_rate = pooling_rate

                        retain_amount = amount_by_line * (retain_rate/100)
                        retain_incentive_amount += retain_amount
                        all_retain_rate = retain_rate

                        gov_amount = amount_by_line * (gov_saleperson_rate/100)
                        gov_salesperson_percentage += gov_amount
                        all_gov_saleperson_rate = gov_saleperson_rate

                        gov_pooling_amount = amount_by_line * (gov_pooling_rate/100)
                        gov_pooling_percentage += gov_pooling_amount
                        all_gov_pooling_rate = gov_pooling_rate
                    
                    init_total = saleperson_incentive_amount + bu_br_incentive_amount + retain_incentive_amount + gov_salesperson_percentage + gov_pooling_percentage
                    all_incentive_rate = saleperson_incentive_amount/init_total * 100
                    all_pooling_rate = bu_br_incentive_amount/init_total * 100
                    all_retain_rate = retain_incentive_amount/init_total * 100
                    all_gov_saleperson_rate = gov_salesperson_percentage/init_total * 100
                    all_gov_pooling_rate = gov_pooling_percentage/init_total * 100

                    if deduct_amount:
                        saleperson_incentive_amount = saleperson_incentive_amount - (deduct_amount * (all_incentive_rate/100))
                        bu_br_incentive_amount = bu_br_incentive_amount - (deduct_amount * (all_pooling_rate/100))
                        retain_incentive_amount = retain_incentive_amount - (deduct_amount * (all_retain_rate/100))
                        gov_salesperson_percentage = gov_salesperson_percentage -  (deduct_amount * (all_gov_saleperson_rate/100))
                        gov_pooling_percentage = gov_pooling_percentage -  (deduct_amount * (all_gov_pooling_rate/100))
                    # for rule in def_id.incentive_rule_ids:
                    #     for line in rec.invoice_line_ids:
                    #     # for line in rec.sale_order_id.order_line:
                    #         if rule.product_categ_id:
                    #             product_category_ids = self.env['product.category'].search([('id','child_of',rule.product_categ_id.ids)])
                    #             if rule.product_categ_id.id == line.product_id.categ_id.id | line.product_id.categ_id.id in product_category_ids.ids:
                    #             # category_ids = product_category_ids.ids
                    #             # if rule.product_categ_id not in category_ids:
                    #             #     category_ids.append(rule.product_categ_id.id)
                    #             # if line.product_id.categ_id.id in category_ids:
                    #                 if def_id.payment_rule == 'both':
                    #                     temp = (rule.incentive_fixed_rate)/2 - deduct_amount
                    #                 else:
                    #                     temp = rule.incentive_fixed_rate - deduct_amount

                    #                 if rule.salesperson_incentive_rate > 0.0:
                    #                     saleperson_incentive_amount += temp * (rule.salesperson_incentive_rate/100)
                    #                 if rule.bu_br_rate > 0.0:
                    #                     bu_br_incentive_amount += temp * (rule.bu_br_rate/100)
                    #                 if rule.retain_rate > 0.0:
                    #                     retain_incentive_amount += temp * (rule.retain_rate/100)
                    #                 if rule.sales_manager_rate > 0.0:
                    #                     if def_id.payment_rule == 'both':
                    #                         manager_incentive_amount += (temp * (rule.sales_manager_rate/100))/2 - deduct_amount
                    #                     else:
                    #                         manager_incentive_amount += temp * (rule.sales_manager_rate/100) - deduct_amount
                    #                 if def_id.is_gov_tender and rule.gov_salesperson_percentage > 0.0:
                    #                     gov_salesperson_percentage += (temp * (rule.gov_salesperson_percentage/100))

                    #                 if def_id.is_gov_tender and rule.gov_pooling_percentage > 0.0:
                    #                     gov_pooling_percentage += (temp * (rule.gov_pooling_percentage/100))

                # sale order type
                elif def_id.rates_definition == 'sale_order_type' and def_id.calculation_type == 'fixed_amount':
                    for rule in def_id.incentive_rule_ids.filtered(lambda x: x.unit_or_part == rec.unit_or_part):
                        incentive_amount = 0.0
                        saleperson_incentive_amount = 0.0
                        bu_br_incentive_amount = 0.0
                        gov_salesperson_percentage = 0.0
                        gov_pooling_percentage = 0.0
                    
                        all_incentive_rate = 0.0
                        all_pooling_rate =0.0
                        all_gov_saleperson_rate =0.0
                        all_gov_pooling_rate =0.0
                        if def_id.payment_rule == 'both':
                    
                            if def_id.salesperson_used:
                                saleperson_incentive_amount += rule.incentive_fixed_rate/2
                            if def_id.bu_br_used:
                                bu_br_incentive_amount += rule.incentive_fixed_rate/2
                            if def_id.government_salesperson_used:
                                gov_salesperson_percentage += rule.incentive_fixed_rate/2
                            if def_id.government_pooling_used:
                                gov_pooling_percentage += rule.incentive_fixed_rate/2
                        else:

                            if def_id.salesperson_used:
                                saleperson_incentive_amount += rule.incentive_fixed_rate
                            if def_id.bu_br_used:
                                bu_br_incentive_amount += rule.incentive_fixed_rate
                            if def_id.government_salesperson_used:
                                gov_salesperson_percentage += rule.incentive_fixed_rate
                            if def_id.government_pooling_used:
                                gov_pooling_percentage += rule.incentive_fixed_rate
                            
                    

                            
                        init_total = saleperson_incentive_amount + bu_br_incentive_amount + gov_salesperson_percentage + gov_pooling_percentage       
                                 
                        all_incentive_rate = saleperson_incentive_amount/init_total * 100
                        print(all_incentive_rate,'all incenitve rate')
                        all_pooling_rate = bu_br_incentive_amount/init_total * 100
                        all_gov_saleperson_rate = gov_salesperson_percentage/init_total * 100
                        all_gov_pooling_rate = gov_pooling_percentage/init_total * 100
                    
                    
                        if deduct_amount:
                            saleperson_incentive_amount = saleperson_incentive_amount - (deduct_amount * (all_incentive_rate/100))
                            bu_br_incentive_amount = bu_br_incentive_amount - (deduct_amount * (all_pooling_rate/100))
                            gov_salesperson_percentage = gov_salesperson_percentage - (deduct_amount * (all_gov_saleperson_rate/100))
                            gov_pooling_percentage = gov_pooling_percentage - (deduct_amount * (all_gov_pooling_rate/100))
                        # incentive_amount += rule.incentive_fixed_rate
                        # if def_id.payment_rule == 'both':
                        #     incentive_amount += (rule.incentive_fixed_rate)/2 - deduct_amount
                        # else:
                        #     incentive_amount += rule.incentive_fixed_rate - deduct_amount

                elif def_id.rates_definition == 'sale_order_type' and def_id.calculation_type == 'fixed_percent':
                    for rule in def_id.incentive_rule_ids.filtered(lambda x: x.unit_or_part == rec.unit_or_part):
                        amount =0.0
                        for line in rec.invoice_line_ids:
                            amount += (line.quantity * line.price_unit)
                            incentive_amount = 0.0
                            saleperson_incentive_amount = 0.0
                            bu_br_incentive_amount = 0.0
                            gov_salesperson_percentage = 0.0
                            gov_pooling_percentage = 0.0
                        
                            all_incentive_rate = 0.0
                            all_pooling_rate =0.0
                            all_gov_saleperson_rate =0.0
                            all_gov_pooling_rate =0.0
                            if def_id.payment_rule == 'both':
                        
                                if def_id.salesperson_used:
                                    saleperson_incentive_amount += ( amount * (rule.incentive_percentage/100))/2
                                  
                                if def_id.bu_br_used:
                                    bu_br_incentive_amount +=  (amount * (rule.incentive_percentage/100))/2
                                if def_id.government_salesperson_used:
                                    gov_salesperson_percentage +=  (amount * (rule.incentive_percentage/100))/2
                                if def_id.government_pooling_used:
                                    gov_pooling_percentage +=  (amount * (rule.incentive_percentage/100))/2
                            else:

                                if def_id.salesperson_used:
                                    saleperson_incentive_amount += (amount * (rule.incentive_percentage/100))
                                    print(saleperson_incentive_amount,'saleperson')
                                if def_id.bu_br_used:
                                    bu_br_incentive_amount += (amount * (rule.incentive_percentage/100))
                                if def_id.government_salesperson_used:
                                    gov_salesperson_percentage += (amount * (rule.incentive_percentage/100))
                                if def_id.government_pooling_used:
                                    gov_pooling_percentage += (amount * (rule.incentive_percentage/100))
                                
                        

                                
                            init_total = saleperson_incentive_amount + bu_br_incentive_amount + gov_salesperson_percentage + gov_pooling_percentage   
                            
                                    
                            all_incentive_rate = saleperson_incentive_amount/init_total * 100
                            print(all_incentive_rate,'all incenitve rate')
                            all_pooling_rate = bu_br_incentive_amount/init_total * 100
                            all_gov_saleperson_rate = gov_salesperson_percentage/init_total * 100
                            all_gov_pooling_rate = gov_pooling_percentage/init_total * 100
                        
                        
                            if deduct_amount:
                                saleperson_incentive_amount = saleperson_incentive_amount - (deduct_amount * (all_incentive_rate/100))
                                bu_br_incentive_amount = bu_br_incentive_amount - (deduct_amount * (all_pooling_rate/100))
                                gov_salesperson_percentage = gov_salesperson_percentage - (deduct_amount * (all_gov_saleperson_rate/100))
                                gov_pooling_percentage = gov_pooling_percentage - (deduct_amount * (all_gov_pooling_rate/100))
                        # amount = 0.0
                        # for line in rec.invoice_line_ids:
                        #     amount += line.quantity * line.price_unit
                        #     incentive_amount = amount * (rule.incentive_percentage/100)
                            # if def_id.payment_rule == 'both':
                            #     incentive_amount = (amount * (rule.incentive_percentage/100))/2 - deduct_amount
                            # else:
                            #     incentive_amount = (amount * (rule.incentive_percentage/100)) - deduct_amount

                        # incentive_amount += rec.sale_order_id.amount_untaxed * (rule.incentive_percentage/100)
                
                elif def_id.rates_definition == 'sale_order_type' and def_id.calculation_type == 'fixed_percent_multi_agent':
                   
                    for rule in def_id.incentive_rule_ids.filtered(lambda x: x.unit_or_part == rec.unit_or_part):
                        total_amount =0.0                     
                        for line in rec.invoice_line_ids:    
                            total_amount += (line.quantity * line.price_unit)      
                            # amount += line.quantity * line.price_unit
                            
                            if deduct_amount:
                                amount = total_amount - deduct_amount
                           
                             
                            else:
                                amount = total_amount
                                
                            if def_id.payment_rule == 'both':
                                temp = ((amount * (rule.incentive_percentage/100)))/2
                            else:
                                temp = (amount * (rule.incentive_percentage/100))

                        # temp = rec.sale_order_id.amount_untaxed * (rule.incentive_percentage/100)
                        if rule.salesperson_incentive_rate > 0.0:
                            saleperson_incentive_amount += temp * (rule.salesperson_incentive_rate/100)

                        if rule.bu_br_rate > 0.0:
                            bu_br_incentive_amount += temp * (rule.bu_br_rate/100)
                        if rule.retain_rate > 0.0:
                            retain_incentive_amount += temp * (rule.retain_rate/100)
                        if rule.sales_manager_rate > 0.0:
                            # amount = 0.0
                            # for line in rec.invoice_line_ids:
                            # amount += line.quantity * line.price_unit
                            if def_id.payment_rule == 'both':
                                manager_incentive_amount += (amount * (rule.sales_manager_rate/100))/2
                            
                            else:
                                manager_incentive_amount += amount * (rule.sales_manager_rate/100)
                                

                            # manager_incentive_amount += rec.sale_order_id.amount_untaxed * (rule.sales_manager_rate/100)
                        if def_id.is_gov_tender and rule.gov_salesperson_percentage > 0.0:
                           
                            gov_salesperson_percentage += (temp * (rule.gov_salesperson_percentage/100))

                        if def_id.is_gov_tender and rule.gov_pooling_percentage > 0.0:
                            
                            gov_pooling_percentage += (temp * (rule.gov_pooling_percentage/100))

                elif def_id.rates_definition == 'sale_order_type' and def_id.calculation_type == 'fixed_amount_multi_agent':
                    for rule in def_id.incentive_rule_ids.filtered(lambda x: x.unit_or_part == rec.unit_or_part):
                        
                        if def_id.payment_rule == 'both':

                            temp = (rule.incentive_fixed_rate)/2 - deduct_amount
                        else:
                            temp = rule.incentive_fixed_rate - deduct_amount

                        if rule.salesperson_incentive_rate > 0.0:
                            saleperson_incentive_amount += temp * (rule.salesperson_incentive_rate/100)
                        if rule.bu_br_rate > 0.0:
                            bu_br_incentive_amount += temp * (rule.bu_br_rate/100)
                        if rule.retain_rate > 0.0:
                            retain_incentive_amount += temp * (rule.retain_rate/100)
                        if rule.sales_manager_rate > 0.0:
                            if def_id.payment_rule == 'both':
                                manager_incentive_amount += (temp * (rule.sales_manager_rate/100))/2 - deduct_amount
                            else:
                                manager_incentive_amount += temp * (rule.sales_manager_rate/100) - deduct_amount

                        if def_id.is_gov_tender and rule.gov_salesperson_percentage > 0.0:
                            gov_salesperson_percentage += (temp * (rule.gov_salesperson_percentage/100))

                        if def_id.is_gov_tender and rule.gov_pooling_percentage > 0.0:
                            gov_pooling_percentage += temp * (rule.gov_pooling_percentage/100)
                else:
                    currency_id = rec.env.user.company_id.country_id.currency_id if rec.env.user.company_id.country_id else currency_id
                    for rule in def_id.incentive_rule_ids:
                        if rule.by_section_operator == '>=':
                            amount = 0.0
                            for line in rec.invoice_line_ids:
                                amount += line.quantity * line.price_unit
                            if amount >= rule.upper_range:
                            # if rec.sale_order_id.amount_untaxed >= rule.upper_range:
                                incentive_rate = rule.incentive_fixed_rate
                                if rule.salesperson_incentive_rate > 0.0:
                                    saleperson_incentive_amount += incentive_rate * (rule.salesperson_incentive_rate/100)
                                if rule.bu_br_rate > 0.0:
                                    bu_br_incentive_amount += incentive_rate * (rule.bu_br_rate/100)
                                if rule.retain_rate > 0.0:
                                    retain_incentive_amount += incentive_rate * (rule.retain_rate/100)
                                if rule.sales_manager_rate > 0.0:
                                    if def_id.payment_rule == 'both':
                                    
                                        manager_incentive_amount += (incentive_rate * (rule.sales_manager_rate/100))/2 - deduct_amount
                                    else:
                                        manager_incentive_amount += incentive_rate * (rule.sales_manager_rate/100) - deduct_amount

                                if def_id.is_gov_tender and rule.gov_salesperson_percentage > 0.0:
                                    gov_salesperson_percentage += incentive_rate * (rule.gov_salesperson_percentage/100)
                                if def_id.is_gov_tender and rule.gov_pooling_percentage > 0.0:
                                    gov_pooling_percentage += incentive_rate * (rule.gov_pooling_percentage/100)
                        elif rule.by_section_operator == '>':
                            amount = 0.0
                            for line in rec.invoice_line_ids:
                                amount += line.quantity * line.price_unit
                            if amount > rule.upper_range:

                            # if rec.sale_order_id.amount_untaxed > rule.upper_range:
                                incentive_rate = rule.incentive_fixed_rate
                                if rule.salesperson_incentive_rate > 0.0:
                                    saleperson_incentive_amount += incentive_rate * (rule.salesperson_incentive_rate/100)
                                if rule.bu_br_rate > 0.0:
                                    bu_br_incentive_amount += incentive_rate * (rule.bu_br_rate/100)
                                if rule.retain_rate > 0.0:
                                    retain_incentive_amount += incentive_rate * (rule.retain_rate/100)
                                if rule.sales_manager_rate > 0.0:
                                    if def_id.payment_rule == 'both':
                                        manager_incentive_amount += (incentive_rate * (rule.sales_manager_rate/100))/2 - deduct_amount
                                    else:
                                        manager_incentive_amount += incentive_rate * (rule.sales_manager_rate/100) - deduct_amount

                                if def_id.is_gov_tender and rule.gov_salesperson_percentage > 0.0:
                                    gov_salesperson_percentage += incentive_rate * (rule.gov_salesperson_percentage/100)
                                if def_id.is_gov_tender and rule.gov_pooling_percentage > 0.0:
                                    gov_pooling_percentage += incentive_rate * (rule.gov_pooling_percentage/100)
                        elif rule.by_section_operator == '<=':
                            amount = 0.0
                            for line in rec.invoice_line_ids:
                                amount += line.quantity * line.price_unit
                            if amount <= rule.lower_range:
                            # if rec.sale_order_id.amount_untaxed <= rule.lower_range:
                                incentive_rate = rule.incentive_fixed_rate
                                if rule.salesperson_incentive_rate > 0.0:
                                    saleperson_incentive_amount += incentive_rate * (rule.salesperson_incentive_rate/100)
                                if rule.bu_br_rate > 0.0:
                                    bu_br_incentive_amount += incentive_rate * (rule.bu_br_rate/100)
                                if rule.retain_rate > 0.0:
                                    retain_incentive_amount += incentive_rate * (rule.retain_rate/100)
                                if rule.sales_manager_rate > 0.0:
                                    if def_id.payment_rule == 'both':
                                        manager_incentive_amount += (incentive_rate * (rule.sales_manager_rate/100))/2 - deduct_amount
                                    else:
                                        manager_incentive_amount += incentive_rate * (rule.sales_manager_rate/100) - deduct_amount

                                if def_id.is_gov_tender and rule.gov_salesperson_percentage > 0.0:
                                    gov_salesperson_percentage += incentive_rate * (rule.gov_salesperson_percentage/100)
                                if def_id.is_gov_tender and rule.gov_pooling_percentage > 0.0:
                                    gov_pooling_percentage += incentive_rate * (rule.gov_pooling_percentage/100)
                        elif rule.by_section_operator == '<':
                            amount = 0.0
                            for line in rec.invoice_line_ids:
                                amount += line.quantity * line.price_unit
                            if amount < rule.lower_range:
                            # if rec.sale_order_id.amount_untaxed < rule.lower_range:
                                incentive_rate = rule.incentive_fixed_rate
                                if rule.salesperson_incentive_rate > 0.0:
                                    saleperson_incentive_amount += incentive_rate * (rule.salesperson_incentive_rate/100)
                                if rule.bu_br_rate > 0.0:
                                    bu_br_incentive_amount += incentive_rate * (rule.bu_br_rate/100)
                                if rule.retain_rate > 0.0:
                                    retain_incentive_amount += incentive_rate * (rule.retain_rate/100)
                                if rule.sales_manager_rate > 0.0:
                                    if def_id.payment_rule == 'both':
                                        manager_incentive_amount += (incentive_rate * (rule.sales_manager_rate/100))/2 - deduct_amount
                                    else:
                                        manager_incentive_amount += incentive_rate * (rule.sales_manager_rate/100) - deduct_amount

                                if def_id.is_gov_tender and rule.gov_salesperson_percentage > 0.0:
                                    gov_salesperson_percentage += incentive_rate * (rule.gov_salesperson_percentage/100)
                                if def_id.is_gov_tender and rule.gov_pooling_percentage > 0.0:
                                    gov_pooling_percentage += incentive_rate * (rule.gov_pooling_percentage/100)
                        elif rule.by_section_operator == 'between':
                            amount = 0.0
                            for line in rec.invoice_line_ids:
                                amount += line.quantity * line.price_unit
                            if amount >= rule.lower_range and rec.sale_order_id.amount_untaxed < rule.upper_range:

                            # if rec.sale_order_id.amount_untaxed >= rule.lower_range and rec.sale_order_id.amount_untaxed < rule.upper_range:
                                incentive_rate = rule.incentive_fixed_rate
                                if rule.salesperson_incentive_rate > 0.0:
                                    saleperson_incentive_amount += incentive_rate * (rule.salesperson_incentive_rate/100)
                                if rule.bu_br_rate > 0.0:
                                    bu_br_incentive_amount += incentive_rate * (rule.bu_br_rate/100)
                                if rule.retain_rate > 0.0:
                                    retain_incentive_amount += incentive_rate * (rule.retain_rate/100)
                                if rule.sales_manager_rate > 0.0:
                                    if def_id.payment_rule == 'both':
                                        manager_incentive_amount += (incentive_rate * (rule.sales_manager_rate/100))/2 - deduct_amount
                                    else:
                                        manager_incentive_amount += incentive_rate * (rule.sales_manager_rate/100) - deduct_amount

                                if def_id.is_gov_tender and rule.gov_salesperson_percentage > 0.0:
                                    gov_salesperson_percentage += incentive_rate * (rule.gov_salesperson_percentage/100)
                                if def_id.is_gov_tender and rule.gov_pooling_percentage > 0.0:
                                    gov_pooling_percentage += incentive_rate * (rule.gov_pooling_percentage/100)
                normal_incentive_obj = self.env['normal.incentive']
                # if not self.env['normal.incentive.main'].search([('sale_order_id', '=', sale_order.id)]):

               
                if not incentive_id:
                    parent_id = self.env['normal.incentive.main'].create({
                                    'sale_order_id': sale_order.id if sale_order else False,
                                    'invoice_id':rec.id,
                                    'incentive_definition_id': def_id.id,
                                    'business_id': def_id.business_id.id,
                                    'date': fields.Date.today(),
                                    'currency_id': currency_id.id,
                                    'branch_id': rec.hr_br_id.id,
                                    'invoice_amount':total_amount,
                                    'unit_or_part':rec.unit_or_part,
                                    })
                    if def_id.payment_rule == 'invoice':
                        parent_id['ready_request_payment'] = True
                    else:
                        parent_id['ready_request_payment'] = False

                    


                incentives = {'sale_order_id': sale_order.id if sale_order else False,
                            'invoice_id':rec.id,
                            'incentive_definition_id': def_id.id,
                            'business_id': def_id.business_id.id,
                            'date': fields.Date.today(),
                            'currency_id': currency_id.id,
                            'branch_id': rec.hr_br_id.id,
                            'parent_id': incentive_id.id if incentive_id else parent_id.id,
                            }

                if incentive_amount > 0.0:
                    if def_id.salesperson_used:
                        saleperson_amount =0.0
                        
                        if  def_id.payment_rule =='both':   
                            saleperson_amount = incentive_amount/2
                        else:
                            saleperson_amount = incentive_amount

                        # if not self.env['normal.incentive'].search([('sale_order_id', '=', sale_order.id), ('sale_person_type', '=', 'sale_person')]):
                        incentives['partner_id'] = rec.invoice_user_id.partner_id.id
                        incentives['incentive_amount'] = saleperson_amount         
                        

                        
                        incentives['sale_person_type'] = 'sale_person'
                        incentives['account_id'] = def_id.account_id.id
                        incentives['origin_incentive_amount'] = saleperson_amount
                       
                        if incentive_id and deduct_amount > 0.0:                     
                            incentive_line_obj = self.env['normal.incentive'].search([('parent_id','=',incentive_id.id),('sale_person_type','=','sale_person')])
                            incentive_line_obj.write({'incentive_amount':saleperson_amount})
                        else:
                            normal_incentive_obj.create(incentives)
                        # normal_incentive_obj.create(incentives)
                    if def_id.bu_br_used:
                        pooling_amount =0.0
                        if  def_id.payment_rule =='both':   
                            pooling_amount = incentive_amount/2
                        else:
                            pooling_amount = incentive_amount

                        # if not self.env['normal.incentive'].search(
                        #         [('sale_order_id', '=', sale_order.id), ('sale_person_type', '=', 'bu_br')]):
                        incentives['partner_id'] = rec.hr_br_id.partner_id.id
                        incentives['incentive_amount'] = pooling_amount
                        incentives['origin_incentive_amount'] = pooling_amount
                        incentives['sale_person_type'] = 'bu_br'
                        incentives['account_id'] = def_id.pooling_account_id.id
                       
                        if incentive_id and deduct_amount > 0.0:                     
                            incentive_line_obj = self.env['normal.incentive'].search([('parent_id','=',incentive_id.id),('sale_person_type','=','bu_br')])
                            incentive_line_obj.write({'incentive_amount':pooling_amount})
                        else:
                            normal_incentive_obj.create(incentives)
                        # normal_incentive_obj.create(incentives)
                    # Area Sale Manager
                    if def_id.area_sale_manager_used and rec.area_sale_manager_id:
                        # if not self.env['normal.incentive'].search(
                        #         [('sale_order_id', '=', sale_order.id), ('sale_person_type', '=', 'sale_manager')]):
                        incentives['partner_id'] = rec.area_sale_manager_id.id
                        # if def_id.payment_rule == 'both':
                        #     incentives['incentive_amount'] = incentive_amount/2
                        # else:
                        incentives['incentive_amount'] = incentive_amount

                        incentives['sale_person_type'] = 'sale_manager'
                        incentives['account_id'] = def_id.asm_account_id.id
                        incentives['origin_incentive_amount'] = incentive_amount
                        if incentive_id and deduct_amount > 0.0:                     
                            incentive_line_obj = self.env['normal.incentive'].search([('parent_id','=',incentive_id.id),('sale_person_type','=','sale_manager')])
                            incentive_line_obj.write({'incentive_amount':incentive_amount})
                        else:
                            normal_incentive_obj.create(incentives)
                        # normal_incentive_obj.create(incentives)
                    if def_id.government_salesperson_used:
                        gov_saleperson_amount =0.0
                        if  def_id.payment_rule =='both':   
                            gov_saleperson_amount = incentive_amount/2 - deduct_amount
                        else:
                            gov_saleperson_amount = incentive_amount - deduct_amount
                        # if not self.env['normal.incentive'].search(
                        #         [('sale_order_id', '=', sale_order.id), ('sale_person_type', '=', 'gov_salesperson')]):
                        incentives['partner_id'] = rec.invoice_user_id.partner_id.id
                        incentives['incentive_amount'] = gov_saleperson_amount

                        incentives['sale_person_type'] = 'gov_salesperson'
                        incentives['account_id'] = def_id.account_id.id
                        incentives['origin_incentive_amount'] = gov_saleperson_amount
                        
                        if incentive_id and deduct_amount > 0.0:
                                            
                            incentive_line_obj = self.env['normal.incentive'].search([('parent_id','=',incentive_id.id),('sale_person_type','=','gov_salesperson')])
                            incentive_line_obj.write({'incentive_amount':gov_saleperson_amount})
                        else:
                            normal_incentive_obj.create(incentives)
                      
                       
                    if def_id.government_pooling_used:
                        gov_pooling_amount =0.0
                        if  def_id.payment_rule =='both':   
                            gov_pooling_amount = incentive_amount/2 - deduct_amount
                        else:
                            gov_pooling_amount = incentive_amount - deduct_amount
                        # if not self.env['normal.incentive'].search(
                        #         [('sale_order_id', '=', sale_order.id), ('sale_person_type', '=', 'gov_pooling')]):
                        incentives['partner_id'] = rec.invoice_user_id.partner_id.id
                        incentives['incentive_amount'] = gov_pooling_amount
                        incentives['sale_person_type'] = 'gov_pooling'
                        incentives['account_id'] = def_id.pooling_account_id.id
                        incentives['origin_incentive_amount'] = gov_pooling_amount
                        if incentive_id and deduct_amount > 0.0:                        
                            incentive_line_obj = self.env['normal.incentive'].search([('parent_id','=',incentive_id.id),('sale_person_type','=','gov_pooling')])
                            incentive_line_obj.write({'incentive_amount':gov_pooling_amount})
                        
                        else:
                            normal_incentive_obj.create(incentives)
                       
                if saleperson_incentive_amount > 0.0 and def_id.salesperson_used:
                    # if not self.env['normal.incentive'].search([('sale_order_id', '=', sale_order.id), ('sale_person_type', '=', 'sale_person')]):
                    incentives['partner_id'] = rec.invoice_user_id.partner_id.id
                    
                    incentives['incentive_amount'] = saleperson_incentive_amount
                    incentives['sale_person_type'] = 'sale_person'
                    incentives['account_id'] = def_id.account_id.id
                    incentives['origin_incentive_amount'] = saleperson_incentive_amount
                    if incentive_id and deduct_amount > 0.0:                        
                        incentive_line_obj = self.env['normal.incentive'].search([('parent_id','=',incentive_id.id),('sale_person_type','=','sale_person')])
                        incentive_line_obj.write({'incentive_amount':saleperson_incentive_amount})
                       
                    else:
                                          
                        normal_incentive_obj.create(incentives)
                if bu_br_incentive_amount > 0.0 and def_id.bu_br_used:
                    # if not self.env['normal.incentive'].search([('sale_order_id', '=', sale_order.id), ('sale_person_type', '=', 'bu_br')]):
                    incentives['partner_id'] = rec.hr_br_id.partner_id.id
                    incentives['incentive_amount'] = bu_br_incentive_amount
                    incentives['sale_person_type'] = 'bu_br'
                    incentives['account_id'] = def_id.pooling_account_id.id
                    incentives['origin_incentive_amount'] =bu_br_incentive_amount
                    if incentive_id and deduct_amount > 0.0:                        
                        incentive_line_obj = self.env['normal.incentive'].search([('parent_id','=',incentive_id.id),('sale_person_type','=','bu_br')])
                        incentive_line_obj.write({'incentive_amount':bu_br_incentive_amount})
                    else:
                        normal_incentive_obj.create(incentives)
                if retain_incentive_amount > 0.0 and def_id.retain_for_salesperson_used:
                    # if not self.env['normal.incentive'].search([('sale_order_id', '=', sale_order.id), ('sale_person_type', '=', 'retain')]):
                    incentives['partner_id'] = rec.invoice_user_id.partner_id.id
                    incentives['incentive_amount'] = retain_incentive_amount
                    incentives['sale_person_type'] = 'retain'
                    incentives['account_id'] = def_id.retain_account_id.id
                    incentives['origin_incentive_amount'] =retain_incentive_amount
                    if incentive_id and deduct_amount > 0.0:                        
                        incentive_line_obj = self.env['normal.incentive'].search([('parent_id','=',incentive_id.id),('sale_person_type','=','retain')])
                        incentive_line_obj.write({'incentive_amount':retain_incentive_amount})
                    else:
                        normal_incentive_obj.create(incentives)
                if manager_incentive_amount > 0.0 and def_id.area_sale_manager_used and rec.area_sale_manager_id:
                    manager_id = self.env['normal.incentive.main'].create({
                                'sale_order_id': sale_order.id if sale_order else False,
                                'incentive_definition_id': def_id.id,
                                'business_id': def_id.business_id.id,
                                'date': fields.Date.today(),
                                'currency_id': currency_id.id,
                                'branch_id': rec.hr_br_id.id,
                                'invoice_id':rec.id,
                                'manager': True,
                                'invoice_amount':total_amount,
                                'unit_or_part':rec.unit_or_part,
                                })
                    # if not self.env['normal.incentive'].search([('sale_order_id', '=', sale_order.id), ('sale_person_type', '=', 'sale_manager')]):
                    incentives['partner_id'] = rec.area_sale_manager_id.id
                    incentives['incentive_amount'] = manager_incentive_amount
                  
                    incentives['sale_person_type'] = 'sale_manager'
                    incentives['account_id'] = def_id.asm_account_id.id
                    incentives['parent_id'] = manager_id.id
                    incentives['origin_incentive_amount'] =manager_incentive_amount
                    if incentive_id and deduct_amount > 0.0:                        
                        incentive_line_obj = self.env['normal.incentive'].search([('parent_id','=',incentive_id.id),('sale_person_type','=','sale_manager')])
                        incentive_line_obj.write({'incentive_amount':manager_incentive_amount})
                    else:
                        normal_incentive_obj.create(incentives)
                      
                    
                    if  not incentive_id and deduct_amount == 0.0:
                        manager_id.incentive_approved()
                if gov_salesperson_percentage > 0.0 and def_id.government_salesperson_used:
                    # if not self.env['normal.incentive'].search([('sale_order_id', '=', sale_order.id), ('sale_person_type', '=', 'gov_salesperson')]):
                    incentives['partner_id'] = rec.invoice_user_id.partner_id.id
                    incentives['incentive_amount'] = gov_salesperson_percentage

                    incentives['sale_person_type'] = 'gov_salesperson'
                    incentives['account_id'] = def_id.account_id.id
                    incentives['origin_incentive_amount'] = gov_salesperson_percentage
                    if incentive_id and deduct_amount > 0.0:                    
                        incentive_line_obj = self.env['normal.incentive'].search([('parent_id','=',incentive_id.id),('sale_person_type','=','gov_salesperson')])
                        incentive_line_obj.write({'incentive_amount':gov_salesperson_percentage})   
                    else:
                        normal_incentive_obj.create(incentives)
                if gov_pooling_percentage > 0.0 and def_id.government_pooling_used:
                    # if not self.env['normal.incentive'].search([('sale_order_id', '=', sale_order.id), ('sale_person_type', '=', 'gov_pooling')]):
                    incentives['partner_id'] = rec.invoice_user_id.partner_id.id
                    incentives['incentive_amount'] = gov_pooling_percentage
                    incentives['sale_person_type'] = 'gov_pooling'
                    incentives['account_id'] = def_id.pooling_account_id.id
                    incentives['origin_incentive_amount'] = gov_pooling_percentage
                    if incentive_id and deduct_amount > 0.0:                        
                        incentive_line_obj = self.env['normal.incentive'].search([('parent_id','=',incentive_id.id),('sale_person_type','=','gov_pooling')])
                        incentive_line_obj.write({'incentive_amount':gov_pooling_percentage})
                       
                       
                    else:
                        
                        normal_incentive_obj.create(incentives)
                        
                if not incentive_id and deduct_amount == 0.0:
                    parent_id.incentive_approved()

            # if rec.state == 'draft':
            #     print('///////////')
            #     normal_incentive_obj = self.env['normal.incentive.main'].search([('sale_order_id','=',rec.sale_order_id.id),('state','=','draft')])
            #     normal_incentive_obj.unlink()
            #     incentive_item_obj = self.env['normal.incentive'].search([('sale_order_id','=',rec.sale_order_id.id),('state','=','draft')])
            #     incentive_item_obj.unlink()


        # return res

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    area_sale_manager_id = fields.Many2one('res.partner',string="Area Sale Manager")

    def _action_confirm(self):
        result = super(SaleOrder, self)._action_confirm()
        for rec in self.picking_ids:
            rec.write({'hr_br_id':self.hr_br_id.id,
                        'hr_bu_id':self.hr_bu_id,
                        'unit_or_part':self.unit_or_part})



    def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        self.ensure_one()
        journal = self.env['account.move'].with_context(default_move_type='out_invoice')._get_default_journal()
        if not journal:
            raise UserError(_('Please define an accounting sales journal for the company %s (%s).', self.company_id.name, self.company_id.id))

        invoice_vals = {
            'ref': self.client_order_ref or '',
            'move_type': 'out_invoice',
            'narration': self.note,
            'currency_id': self.pricelist_id.currency_id.id,
            'campaign_id': self.campaign_id.id,
            'medium_id': self.medium_id.id,
            'source_id': self.source_id.id,
            'user_id': self.user_id.id,
            'invoice_user_id': self.user_id.id,
            'team_id': self.team_id.id,
            'partner_id': self.partner_invoice_id.id,
            'partner_shipping_id': self.partner_shipping_id.id,
            'fiscal_position_id': (self.fiscal_position_id or self.fiscal_position_id.get_fiscal_position(self.partner_invoice_id.id)).id,
            'partner_bank_id': self.company_id.partner_id.bank_ids[:1].id,
            'journal_id': journal.id,  # company comes from the journal
            'invoice_origin': self.name,
            'invoice_payment_term_id': self.payment_term_id.id,
            'payment_reference': self.reference,
            'transaction_ids': [(6, 0, self.transaction_ids.ids)],
            'invoice_line_ids': [],
            'company_id': self.company_id.id,
            'sale_order_id': self.id,
            'unit_or_part': self.unit_or_part,
            'is_gov_tender':self.is_gov_tender,
            'hr_br_id':self.hr_br_id.id,
            'hr_bu_id':self.hr_bu_id.id,
        }
        return invoice_vals

    def write(self,vals):

        res = super(SaleOrder, self).write(vals)

        if 'state' in vals and vals['state'] == 'sale':
            result = self
            sale_team_target_ids = self.env['sale.team.target'].search([('branch_id','=',self.hr_br_id.id),('state','=','confirm')])
            team_target = False

            for t in sale_team_target_ids:
                if result.date_order.date() >= t.start_date and result.date_order.date() <= t.end_date:
                    sale_ids = t.sale_order_ids.ids
                    sale_ids.append(result.id)
                    t.update({
                        'sale_order_ids':sale_ids,
                    })
        return res
