# -*- coding: utf-8 -*-
import base64
import os
from lxml import etree
from odoo import models, tools, fields, api, _
from odoo.exceptions import UserError, ValidationError


# BUSINESS SECTOR TYPE
class BusinessSectorType(models.Model):
    _name = 'business.sector.type'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Business Sector Type'

    name = fields.Char('Business Sector Type Name', required=True)


# BUSINESS UNIT
class BusinessUnit(models.Model):
    _name = 'business.unit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'BU/BR/DIV/CFD'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)
    company = fields.Many2one('res.company')
    number = fields.Char('Number')
    building_floor_id = fields.Many2one('building.floor', string='Floor')
    building = fields.Char('Building')
    street = fields.Char('Street')
    zone = fields.Many2one('industry.zone')
    road = fields.Char('Road')
    quarter = fields.Char('Quarter')
    township_id = fields.Many2one('hr.township', string='Township')
    city_id = fields.Many2one('hr.city', string='City')
    region_id = fields.Many2one('hr.region', string='Region')
    country_id = fields.Many2one('hr.country', string='Country')
    country_code = fields.Char(string="Country code", related='country_id.country_code', readonly=True)
    active = fields.Boolean(string='Active', default=True)
    phone = fields.Char('Phone')
    mobile = fields.Char('Mobile')
    business_type = fields.Selection([
        ('bu', 'BU'),
        ('br', 'BR'),
        ('div', 'DIV'),
        ('cfd', 'CFD'),
    ], string="Business Type", required=True, default="bu")
    partner_id = fields.Many2one('res.partner', string='Partner')

    sector_type_id = fields.Many2one('business.sector.type', string='Business Sector Type', )
    establish_date = fields.Date(string="Establish Date")
    parent_business_id = fields.Many2one('business.unit', string='Parent Business')

    # START: Account Journal
    # This Journal for Oversea PO process
    oversea_po_journal_id = fields.Many2one('account.journal', string='Oversea PO Journal', domain="[('bu_br_id', '=', id)]")
    #END: Account Journal

    # START: Chart Of Account
    account_code = fields.Char('Account Code')
    property_account_receivable_id = fields.Many2one('account.account', 'Account Receivable',
                                                     domain="[('internal_type', '=', 'receivable'),('bu_br_id', '=', id)]")
    property_account_payable_id = fields.Many2one('account.account', 'Account Payable',
                                                  domain="[('internal_type', '=', 'payable'),('bu_br_id', '=', id)]")
    aff_account_receivable_id = fields.Many2one('account.account', 'Aff: Receivable',
                                                domain="[('bu_br_id', '=', id),('name', 'ilike', 'aff')]")
    aff_account_payable_id = fields.Many2one('account.account', 'Aff: Payable',
                                             domain="[('bu_br_id', '=', id),('name', 'ilike', 'aff')]")
    cash_in_transit_id = fields.Many2one('account.account', 'Cash In Transit', domain="[('bu_br_id', '=', id)]")
    cash_on_hand_id = fields.Many2one('account.account', 'Cash On Hand', domain="[('bu_br_id', '=', id)]")
    incentive_account_id = fields.Many2one('account.account', 'Accrued Incentive', domain="[('bu_br_id', '=', id)]")
    pooling_account_id = fields.Many2one('account.account', 'Accrued Pooling', domain="[('bu_br_id', '=', id)]")
    asm_account_id = fields.Many2one('account.account', 'Accrued ASM', domain="[('bu_br_id', '=', id)]")
    commission_account_id = fields.Many2one('account.account', 'Commission Account', domain="[('bu_br_id', '=', id)]")

    # END: Chart Of Account
    commission_account_id = fields.Many2one('account.account','Commission Account', domain="[('bu_br_id', '=', id)]")

    # Job Order Account

    inventory_machine_account_id = fields.Many2one('account.account','Inventory(Customer Machine) Account', domain="[('bu_br_id', '=', id)]")
    processing_account_id = fields.Many2one('account.account', 'Processing Account', domain="[('bu_br_id', '=', id)]")

    #Exchange gain/loss
    currency_exchange_gain_account_id = fields.Many2one('account.account',"Exchange Gain Account", domain="[('bu_br_id','=', id),('user_type_id.name','=','Other Income')]")
    currency_exchange_loss_account_id = fields.Many2one('account.account',"Exchange Loss Account", domain="[('bu_br_id','=', id),('user_type_id.name','=','Expenses')]")

    #Budget
    budget_control_percent = fields.Integer('Extra Budget limited(%)')
    # Advance Account for Budget advance
    advance_account_id = fields.Many2one('account.account',"Budget Advance Account",domain="[('bu_br_id','=', id)]")
    
    # This account intended to use as payable account on Oversea Purchase Process
    po_property_account_payable_id = fields.Many2one('account.account', 'Account Payable', 
        domain="[('internal_type', '=', 'payable'),('bu_br_id', '=', id)]",
        help="This Account is intended to use as purchase payable account on oversea purchase process."
        )
    
    suspense_account_id = fields.Many2one('account.account', 'Suspense Account', domain="[('bu_br_id', '=', id)]")
    #END: Chart Of Account

    # Landed Cost Journal
    landed_cost_journal_id = fields.Many2one('account.journal',domain="[('type', '=', 'general'),('bu_br_id', '=', id)]",)

    broker_account_id = fields.Many2one('account.account','Broker Account', domain="[('bu_br_id', '=', id)]")

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(BusinessUnit, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                        submenu=submenu)
        account_config = self.env['ir.config_parameter'].sudo().get_param('master_data_extension.account_config')
        is_acc_auto = self.env['ir.config_parameter'].sudo().get_param('master_data_extension.is_acc_auto')
        if view_type == "form":
            doc = etree.XML(res['arch'])
            account_structure = doc.xpath("//notebook/page[@name='account_structure']")
            account_code = doc.xpath("//field[@name='account_code']")
            if account_structure:
                # To Showing account configuration notebook page
                account_structure[0].attrib['invisible'] = '0' if account_config else '1'
                # Account Auto Generate Option
                if is_acc_auto:
                    account_code[0].attrib['required'] = '1'
                    account_code[0].attrib['invisible'] = '0'
                else:
                    account_code[0].attrib['required'] = '0'
                    account_code[0].attrib['invisible'] = '1'

            # show or hide account structure base on res.config.setting
            xarch, xfields = self.env['ir.ui.view'].postprocess_and_fields(doc, model=self._name)

            res['arch'] = xarch
            res['fields'] = xfields
        return res

    # LOGO
    def _get_logo(self):
        return base64.b64encode(
            open(os.path.join(tools.config['root_path'], 'addons', 'base', 'static', 'img', 'res_company_logo.png'),
                 'rb').read())

    @api.depends('partner_id.image_1920')
    def _compute_logo_web(self):
        for business in self:
            business.logo_web = tools.image_process(business.partner_id.image_1920, size=(180, 0))

    # logo = fields.Binary(related='partner_id.image_1920', default=_get_logo, string="Company Logo", readonly=False)
    logo = fields.Binary('Image')
    logo_web = fields.Binary(compute='_compute_logo_web', store=True, attachment=False)

    # @api.constrains('account_code')
    # def _check_account_code(self):
    #     for unit in self:
    #         if self.env['business.unit'].search([('account_code', '=', unit.account_code)]):
    #             raise ValidationError(_('You cannot have a Business because your account code has been already used.(account code: %s)', unit.account_code))

    # Prepare default COA for BU or BR
    @api.model
    def _prepare_default_account_vals(self, res):
        # """
        #     FORMAT:[AccountName,UserTypeID,Reconcile]
        # """
        result = []
        default_acc = [
            ['Account Receivable', self.env.ref('account.data_account_type_receivable').id, True],
            ['Account Payable', self.env.ref('account.data_account_type_payable').id, True],
            ['Aff: Receivable', self.env.ref('account.data_account_type_receivable').id, True],
            ['Aff: Payable', self.env.ref('account.data_account_type_payable').id, True],
            ['Cash In Transit', self.env.ref('account.data_account_type_current_assets').id, False],
            # Current Assets Account
            ['Cash On Hand', self.env.ref('account.data_account_type_current_assets').id, False]
            # Current Assets Account
        ]
        code = int(res.account_code) + 1
        for acc in default_acc:
            val = {
                'name': acc[0], 'user_type_id': acc[1], 'reconcile': acc[2],
                'code': str(code), 'bu_br_id': res.id, 'company_id': self.env.user.company_id.id
            }
            code += 1
            result.append(val)
        return result

    # Auto create chart of account for current created BU or BR or DIV
    def create_coa(self, res):
        account = self.env['account.account']
        result = self._prepare_default_account_vals(res)
        for res in result:
            account.create(res)
        return True

    # Auto Warehouse and location for current created BU or BR or DIV
    def create_warehouse_and_location(self, res):
        business_unit = {'name': res.name, 'code': res.code, 'hr_bu_id': res.id}
        warehouse_id = self.env['stock.warehouse'].create(business_unit)
        warehouse_id.lot_stock_id.hr_bu_id = res.id

    @api.model
    def create(self, vals):
        """Create Method to add the HR Branch."""
        name = vals.get('name')
        code = vals.get('code')
        partner_id = self.env['res.partner'].create({'name': name, 'image_1920': vals.get('logo')})
        vals['partner_id'] = partner_id.id
        res = super(BusinessUnit, self).create(vals)

        # need to check
        self.env.user.hr_bu_ids = [(4, res.id)]

        # Auto create Warehouse and location
        if self.env['ir.config_parameter'].sudo().get_param('master_data_extension.is_inv_auto'):
            self.create_warehouse_and_location(res)

        # Auto create acc setup
        if self.env['ir.config_parameter'].sudo().get_param('master_data_extension.is_acc_auto'):
            print("============>",
                  self.env['ir.config_parameter'].sudo().get_param('master_data_extension.is_acc_auto'))
            self.create_coa(res)

        return res

    @api.onchange('city_id')
    def onchange_city_id(self):
        self.region_id = self.city_id.region_id.id

    @api.onchange('account_code')
    def account_code_onchange(self):
        if self.account_code:
            if len(self.account_code) < 6:
                raise UserError(_("Account Code must be at least 6 digits number."))
            try:
                int(self.account_code)
            except Exception as e:
                raise UserError(_("Data type of Account Code must be INTEGER."))

    # @api.model
    def create_account_action(self):
        """ create account for current Business"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create An Account From Current Account'),
            'res_model': 'account.account',
            'target': 'new',
            'view_mode': 'form',
            'context': {
                'default_bu_br_id': self.id,
            },
        }

    def create_journal_action(self):
        """ create journal for current Business"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Journal From Current Account'),
            'res_model': 'account.journal',
            'target': 'new',
            'view_mode': 'form',
            'context': {
                'default_bu_br_id': self.id,
            },
        }


# account.view_account_journal_form

class AccountAccount(models.Model):
    _inherit = 'account.journal'
    _description = 'Account Journal'

    bank_pooling_account = fields.Many2one('account.account', 'Bank Pooling Account',
                                           domain="[('deprecated', '=', False), ('company_id', '=', company_id),('bu_br_id', '=', bu_br_id),"
                                                  "'|', ('user_type_id', '=', default_account_type),"
                                                  "('user_type_id.type', 'not in', ('receivable', 'payable'))]")
