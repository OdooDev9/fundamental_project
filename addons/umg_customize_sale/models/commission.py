from dataclasses import field
from multiprocessing import set_forkserver_preload
from re import T
from odoo import models, fields,api, _
from  datetime import datetime, date
from odoo.exceptions import UserError

class ProductTemplateInherited(models.Model):
    _inherit = 'product.template'
    _description = 'Add Commission In Product'

    commission = fields.Float('Commission')

class ProductInherited(models.Model):
    _inherit = 'product.product'
    _description = 'Add Commission In Product'

    commission = fields.Float('Commission', related="product_tmpl_id.commission")

class ProductCategoryInherited(models.Model):
    _inherit = 'product.category'
    _description = 'Product Category'

    commission = fields.Float('Commission')

# class AccountMove(models.Model):
#     _inherit = 'account.move'
#     _description = 'AccountMove'

#     def action_view_commission(self):
#         action = self.env.ref('umg_customize_sale.sale_commission_action').read()[0]
#         _ids = []
#         for com in self.env['sale.commission'].search([]):
#             if self.id in com.move_ids.ids:
#                 _ids.append(com.id)
#         action['domain'] = [('id', 'in', _ids)]
#         return action
class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    _description = 'Account Move Line'

    commission_id = fields.Many2one('sale.commission')

class SaleCommission(models.Model):
    _name = 'sale.commission'
    _description = 'Sale Commission'
    _order = 'date desc'

    def action_move_items(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_account_moves_all_a")
        # action['domain'] = [('commission_id', '=', self.id),('account_id.bu_br_id','=',self.env.user.current_bu_br_id.id)]
        if self.env.user.user_type_id != 'cfd':
            action['domain'] = [('commission_id', '=', self.id), ('account_id.bu_br_id','=',self.env.user.current_bu_br_id.id)]
        else:
            action['domain'] = [('commission_id', '=', self.id)]
        return action

    name = fields.Char('Name')
    branch_id = fields.Many2one('business.unit', 'Branch',domain="[('business_type','=','br')]")
    business_id = fields.Many2one('business.unit', 'Business Unit',domain="[('business_type','=','bu')]")
    amount = fields.Float('Amount')
    date = fields.Date('Date')
    currency_id = fields.Many2one('res.currency', 'Currency')
    invoice_id =fields.Many2one('account.move', 'Account Move')
    # move_ids = fields.Many2many('account.move', 'Account Moves', compute='get_moves')
    order_id = fields.Many2one('sale.order', 'Sale Order')
    state = fields.Selection([('draft','Draft'),('paid','Paid')], default='draft')
    deduct_amount = fields.Float('Deduct Amount',tracking=True)
    commission_amount = fields.Float('Commission Amount',compute="_compute_commission_amount")

    @api.depends('amount','deduct_amount')
    def _compute_commission_amount(self):
        for rec in self:
            rec.commission_amount = rec.amount - rec.deduct_amount


    def unlink(self):
        for rec in self:
            if rec.state == 'paid':
                raise UserError(_('You cannot Delete this record'))
        return super(SaleCommission, self).unlink()

    def create_br_entry(self):
        res = []
        amount = self.currency_id._convert(self.commission_amount,
                                           self.env.user.company_id.currency_id,
                                           self.env.user.company_id,
                                           datetime.today(),
                                           )
        move_line = {'name': self.name,
                     'partner_id': self.business_id.partner_id.id,
                     'account_id': self.branch_id.commission_account_id.id,
                     'business_id': self.branch_id.id,
                     'date': date.today(),
                     'amount_currency': - self.commission_amount,
                     'credit':amount,
                    #  'credit': self.commission_amount ,
                     'currency_id': self.currency_id.id,
                     'commission_id': self.id, }
        res.append(move_line)
        move_line = {'name': self.name,
                     'partner_id': self.business_id.partner_id.id,
                     'account_id': self.branch_id.aff_account_receivable_id.id,
                     'business_id': self.branch_id.id,
                     'date': date.today(),
                     'amount_currency': self.commission_amount,
                     'debit':amount,
                    #  'debit': self.commission_amount,
                     'currency_id': self.currency_id.id,
                     'commission_id': self.id, }
        res.append(move_line)
        journal_id = self.env['account.journal'].search([('type','=','general'),('bu_br_id','=',self.branch_id.id)])
        if not journal_id:
            raise UserError(_("Account Missing Error!. Your haven't set Miscellaneous Journal for current %s." % self.branch_id.name))
        line_ids = [(0, 0, l) for l in res]
        move_vals = {
            'journal_id':journal_id[0].id,
            'ref': self.name,
            'hr_br_id':self.branch_id.id,
            'date': self.date,
            'line_ids': line_ids,
            'hr_bu_id':self.business_id.id,
        }
        move_id = self.env['account.move'].create(move_vals)
        
        return move_id.post()
    
    def create_bu_entry(self):
        amount = self.currency_id._convert(self.commission_amount,
                                           self.env.user.company_id.currency_id,
                                           self.env.user.company_id,
                                           datetime.today(),
                                           )
        res = []
        move_line = {'name': self.name,
                     'partner_id': self.branch_id.partner_id.id,
                     'account_id': self.business_id.commission_account_id.id,
                     'business_id': self.business_id.id,
                     'date': date.today(),
                      'amount_currency': self.commission_amount,
                      'debit':amount,
                    #  'debit': self.commission_amount ,
                     'currency_id': self.currency_id.id,
                     'commission_id': self.id, }
        res.append(move_line)
        move_line = {'name': self.name,
                     'partner_id': self.branch_id.partner_id.id,
                     'account_id': self.business_id.aff_account_payable_id.id,
                     'business_id': self.business_id.id,
                     'date': date.today(),
                     'amount_currency': - self.commission_amount,
                     'credit': amount,
                    #  'credit': self.commission_amount,
                     'currency_id': self.currency_id.id,
                     'commission_id': self.id, }
        res.append(move_line)
        journal_id = self.env['account.journal'].search([('type','=','general'),('bu_br_id','=',self.business_id.id)])
        if not journal_id:
            raise UserError(_("Account Missing Error!. Your haven't set Miscellaneous Journal for current %s." % self.business_id.name))
        line_ids = [(0, 0, l) for l in res]
        move_vals = {
            'journal_id':journal_id[0].id,
            'ref': self.name,
            'hr_br_id':self.branch_id.id,
            'date': self.date,
            'line_ids': line_ids,
            'hr_bu_id':self.business_id.id,
        }
        move_id = self.env['account.move'].create(move_vals)
        return move_id.post()

    def action_paid(self):
        self.create_br_entry()
        self.create_bu_entry()
        return self.write({'state':'paid'})

    # SLO
    def multi_commission_paid(self, obj=None):
        active_ids = self._context.get('active_ids') if not obj else obj.ids
        commission_ids = self.env['sale.commission'].browse(active_ids)
        for record in commission_ids:
            record.action_paid()
        return True

    # def get_moves(self):
    #     for rec in self:
    #         if rec.order_id:
    #             print (rec.order_id.invoice_ids, 'invoice_ids')
    #             rec.move_ids = rec.order_id.invoice_ids

# class SaleOrder(models.Model):
#     _inherit = 'sale.order'
#     _description = 'Sale Order'

#     def compute_commission(self):
#         for rec in self:
#             amount = 0.0
#             for line in rec.order_line:
#                 commission = line.product_id.commission if line.product_id.commission > 0.0 else line.product_id.categ_id.commission
#                 amount += (line.price_unit * line.product_uom_qty) * (commission/100)
#             if amount > 0.0 and rec.hr_br_id:
#                 commission_id = self.env['sale.commission'].search([('order_id', '=', rec.id)])
#                 if not commission_id:
#                     self.env['sale.commission'].create({'order_id': rec.id,
#                                                         'business_id': rec.hr_bu_id.id,
#                                                         'branch_id': rec.hr_br_id.id,
#                                                         'date': datetime.today().date(),
#                                                         'currency_id': rec.currency_id.id,
#                                                         'amount': amount - rec.br_discount_amount,
#                                                         'name': 'commission for ' + str(rec.hr_br_id.name),})
#                 else:
#                     commission_id.write({'order_id': rec.id,
#                                          'business_id': rec.hr_bu_id.id,
#                                          'branch_id': rec.hr_br_id.id,
#                                          'date': datetime.today().date(),
#                                          'currency_id': rec.currency_id.id,
#                                          'amount': amount - rec.br_discount_amount,
#                                          'name': 'commission for ' + str(rec.hr_br_id.name),
#                                          })