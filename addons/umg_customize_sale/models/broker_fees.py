from odoo import api, fields, models, SUPERUSER_ID, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import get_lang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare, float_round
import json


class BrokerFees(models.Model):
    _name = "broker.fees"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Broker Fees'

    name = fields.Char(string="Broker Fees", required=True, readonly=True, default='New', copy=False)
    partner_id = fields.Many2one('res.partner', string='Broker')
    payment_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed_amount', 'Fixed Amount'),
    ], default='fixed_amount', string='Payment')
    fixed_amount = fields.Float(
        string="Fixed Amount", help="Fixed amount.")
    fixed_percentage = fields.Float(string="Fixed Percentage(%)")
    product_id = fields.Many2one('product.product', string='Product', domain="[('detailed_type', '=', 'service')]")
    quote_name = fields.Many2one('sale.order', string="Sale Order")
    payment_amt = fields.Float(string="Payment Amount", readonly=True, digits=(12, 2))
    bill_count = fields.Integer(string="Bills", compute='_compute_invoice_count')
    hr_br_id = fields.Many2one('business.unit', string='Branch',domain="[('business_type','=','br')]")
    hr_bu_id = fields.Many2one('business.unit', string='Business Unit',domain="[('business_type','=','bu')]")
    # state = fields.Selection([
    #     ('new', 'To Approve'),
    #     ('approved', 'Approved'),
    #     ('cancel', 'Cancel'),
    # ], string='Status', readonly=True, default='new')
    state = fields.Selection([
        ('new', 'To Approve'),
        ('br_sale_admin', 'BR Sales Admin'),
        ('br_finance_a', 'BR F & A'),
        ('br_boh', 'BR BOH'),
        ('bu_sale_admin', 'BU Sales Admin'),
        ('bu_s_and_mhead', 'S & M Head'),
        ('approve_f_and_ahead', 'BU F & A Head'),
        ('approve_gm_agm', 'BU GM/AGM'),
        ('approve_coo', 'COO'),
        ('approve_cfd_ar_pic', 'CFD AR PIC'),
        ('approve_cfd_ar_dh', 'FCD AR DH'),
        ('approve_cfd_agm', 'CFD AGM'),
    ], string='Status', readonly=True, default='new')
    phone_no = fields.Char(string="Kpay or Mobile Banking")
    invoice_name = fields.Many2one('account.move', string="Sale Invoice")
    bfoker_type = fields.Selection([
        ('upon_delivery', 'Upon Delivery'),
        ('ar', 'AR Finished'),
    ], default='upon_delivery', string='Type')
    attachment_id = fields.Many2many('ir.attachment','broker_ir_attachment_rel','broker_fees_id','attachment',string="Attachment")
    payment_id = fields.Many2one('account.payment',string="Payment ID")
    br_user_approve = fields.Boolean(compute='compute_br_user_approve',string="Br")
    bu_user_approve = fields.Boolean(compute='compute_bu_user_approve',string="Bu")
    cfd_user_approve = fields.Boolean(compute='compute_cfd_user_approve',string="cfd")
    broker_bill = fields.Boolean(string='Broker Bill')
    br = fields.Boolean(compute='compute_br',string="Br Sale")
    bu = fields.Boolean(compute='compute_bu',string="Bu Sale")

    def compute_br(self):
        for rec in self:
            if rec.hr_br_id.id:
                rec.br = True
            else:
                rec.br = False

    def compute_bu(self):
        for rec in self:
            if rec.hr_br_id.id:
                rec.bu = False
            else:
                rec.bu = True

    def compute_br_user_approve(self):
        for rec in self:
            if rec.hr_br_id.id == self.env.user.current_bu_br_id.id and self.env.user.user_type_id == 'br':
                rec.br_user_approve = True
            else:
                rec.br_user_approve = False

    def compute_bu_user_approve(self):
        for rec in self:
            if rec.hr_bu_id.id == self.env.user.current_bu_br_id.id and self.env.user.user_type_id == 'bu':
                rec.bu_user_approve = True
            else:
                rec.bu_user_approve = False

    def compute_cfd_user_approve(self):
        for rec in self:
            if self.env.user.user_type_id == 'cfd':
                rec.cfd_user_approve = True
            else:
                rec.cfd_user_approve = False

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'broker.fees') or 'New'
        result = super(BrokerFees, self).create(vals)
        return result

    def _compute_invoice_count(self):

        # """This compute function used to count the number of bill for the brokers"""
        for broker_line in self:
            move_ids = broker_line.env['account.move'].search([('broker_fees_id', '=', broker_line.id),('move_type','=','in_invoice')])
            if move_ids:
                self.bill_count = len(move_ids)
            else:
                self.bill_count = 0

    def create_bill(self):
        """This is the function for creating vendor bill
                from the broker fees form"""
        for broker_line in self:
            current_user = self.env.uid
            invoice_line_list = []
            invoice_line_list.append({
                'product_id': broker_line.product_id.id,
                'price_unit': broker_line.payment_amt

            })
            invoice = broker_line.env['account.move'].create({
                'move_type': 'in_invoice',
                'invoice_origin': broker_line.name,
                'invoice_user_id': current_user,
                'partner_id': broker_line.partner_id.id,
                # 'currency_id': broker_line.env.user.company_id.currency_id.id,
                # 'journal_id': int(vendor_journal_id),
                # 'payment_reference': broker_line.name,
                'broker_fees_id': broker_line.id,
                'invoice_line_ids': invoice_line_list,
                'hr_br_id': broker_line.hr_br_id.id,
                'hr_bu_id': broker_line.hr_bu_id.id,
                'broker_bill': True
            })
            broker_line.write({'broker_bill': 'True'})
        return invoice

    def action_open_bill(self):

        return {
            'name': 'Bills',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'domain': [('broker_fees_id', '=', self.id),('move_type','=','in_invoice')],
            'context': {'create': False},
            'target': 'current'
        }

    def unlink(self):
        for result in self:
            if result.state not in ['new','cancel']:
                raise UserError(_('Cannot delete a broker fees which is in state \'%s\'.') % (result.state,))
            t_name = 'broker.fees'
            sql = "DELETE FROM ir_attachment where res_model=%s and id in (%s) "
            self.env.cr.execute(sql,(t_name,result.id))
            result.invoice_name.write({'broker_fees_id': result.id,
                                  'broker_button': False})
        res = super(BrokerFees, self).unlink()
        return res

    def br_sale_admin(self):
        # print('-------------------BR Sale Admin')
        self.state='br_sale_admin'

    def br_finance_a(self):
        # print('-------------------BR F & A')
        self.state='br_finance_a'

    def br_boh(self):
        # print('-------------------BR BOH')
        self.state='br_boh'

    def bu_sale_admin(self):
        # print('-------------------BU Sale Admin')
        self.state='bu_sale_admin'

    def bu_s_and_mhead(self):
        # print('-------------------BU S & M Head')
        self.state='bu_s_and_mhead'

    def approve_f_and_ahead(self):
        # print('-------------------F & A Head')
        self.state='approve_f_and_ahead'


    def approve_gm_agm(self):
        self.state='approve_gm_agm'

    def approve_coo(self):
        # print('-------------------COO')
        self.state='approve_coo'

    def approve_cfd_ar_pic(self):
        #print('-------------------CFD AR PIC')
        self.state='approve_cfd_ar_pic'

    def approve_cfd_ar_dh(self):
        # print('-------------------CFD AR DH')
        self.state='approve_cfd_ar_dh'

    def approve_cfd_agm(self):
        # print('-------------------CFD AGM')
        self.state='approve_cfd_agm'



