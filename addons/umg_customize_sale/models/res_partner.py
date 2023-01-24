from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import re


class ResPartnerInherit(models.Model):
    _inherit = "res.partner"

    @api.model
    def _get_hr_branch(self):
        if self.env.user.user_type_id == 'br':
            return self.env.user.current_bu_br_id

    @api.model
    def _get_hr_bu(self):
        if self.env.user.user_type_id == 'bu':
            return self.env.user.current_bu_br_id

    def _prepare_display_address(self, without_company=False):
        # get the information that will be injected into the display format
        # get the address format
        address_format = self._get_address_format()
        args = {
            'state_code': self.state_id.name or '',
            'state_name': self.state_id.name or '',
            'country_code': self.country_id.code or '',
            'country_name': self._get_country_name(),
            'company_name': self.commercial_company_name or '',
        }
        for field in self._formatting_address_fields():
            args[field] = getattr(self, field) or ''
        if without_company:
            args['company_name'] = ''
        elif self.commercial_company_name:
            address_format = '%(company_name)s\n' + address_format
        return address_format, args

    @api.model
    def _get_address_format(self):
        # When sending a letter, the fields 'street' and 'street2' should be on a single line to fit in the address area
        if self.env.context.get('snail.snailmail_layout') and self.street2:
            return "%(street)s, %(street2)s\n%(city)s %(state_name)s %(zip)s\n%(country_name)s"
        return super(ResPartnerInherit, self)._get_address_format()

    hr_bu_ids = fields.Many2many('business.unit', 'partner_business_ref', 'bu_id', 'partner_id',
                                 string='Allowed Business Unit', domain="[('business_type','=','bu')]",
                                 default=_get_hr_bu)
    hr_br_ids = fields.Many2many('business.unit', 'partner_branch_ref', 'br_id', 'parnter_id',
                                 string='Allowed Branches', domain="[('business_type','=','br')]",
                                 default=_get_hr_branch)

    customer = fields.Boolean(string='Is a Customer',
                              help="Check this box if this contact is a customer. It can be selected in sales orders.")

    # YZO Update label for supplier and add oversea_supplier
    supplier = fields.Boolean(string='Is a Local Vendor',
                              help="Check this box if this contact is a local vendor. It can be selected in purchase "
                                   "orders.")

    oversea_supplier = fields.Boolean(string='Is a Oversea Vendor',
                                      help="Check this box if this contact is a oversea vendor. It can be selected in "
                                           "oversea purchase orders.")

    broker = fields.Boolean(string='Is a Broker',
                            help="Check this box if this contact is a vendor.")
    vat = fields.Char(string='Registration No./License No.', index=True,
                      help="The Tax Identification Number. Complete it if the contact is subjected to government taxes. Used in some legal statements.")

    phone = fields.Char(size=13)

    nrc = fields.Selection([
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
        ('6', '6'),
        ('7', '7'),
        ('8', '8'),
        ('9', '9'),
        ('10', '10'),
        ('11', '11'),
        ('12', '12'),
        ('13', '13'),
        ('14', '14'),
    ], string="NRC")

    # nrc_state = fields.Many2one('nrc.state', string='', domain="[('state_number','=',nrc)]")

    nrc_national = fields.Selection([
        ('n', '(N)'),
        ('p', '(P)'),
        ('e', '(E)'),
        ('a', '(A)'),
        ('f', '(F)'),
        ('th', 'TH'),
        ('g', 'G'),
    ], string='')

    nrc_state = fields.Many2one('nrc.state', string='', domain="[('state_number','=',nrc)]")

    nrc_number = fields.Char(string="", size=6)

    edit_hr_br_ids = fields.Many2many('business.unit', 'edit_user_branch_ref', 'br_id', string='Branches',
                                      default=_get_hr_branch, domain="[('business_type','=','br')]")
    edit_hr_bu_ids = fields.Many2many('business.unit', 'edit_user_business_ref', string='Business Unit',
                                      default=_get_hr_bu, domain="[('business_type','=','bu')]")

    _sql_constraints = [
        ('phone_uniq', 'UNIQUE (phone)', 'You can not have two phone number with the same number !')
    ]
    no_have_company_registration = fields.Boolean(default=False)

    # YZO Add onchange of local_vendor and oversea vendor
    @api.onchange('supplier')
    def _onchange_local_vendor(self):
        if self.supplier:
            self.oversea_supplier = False

    @api.onchange('oversea_supplier')
    def _onchange_oversea_vendor(self):
        if self.oversea_supplier:
            self.supplier = False

    @api.constrains('phone', 'nrc_number', 'nrc_state', 'nrc_national', 'nrc')
    def _check_phone_number_and_nrc(self):
        for rec in self:
            if (rec.no_have_company_registration and rec.company_type == 'company') or (
                    (rec.nrc and rec.nrc_number and rec.nrc_state) and rec.company_type == 'person'):
                if rec.nrc_number and rec.nrc and rec.nrc_state and rec.nrc_national:
                    check_nrc_no = self.env['res.partner'].search(
                        [('nrc', '=', rec.nrc), ('nrc_state', '=', rec.nrc_state.id),
                         ('nrc_national', '=', rec.nrc_national),
                         ('nrc_number', '=', rec.nrc_number), ('id', '!=', rec.id)])
                    if check_nrc_no:
                        raise ValidationError(_('NRC for contact must be unique!'))
                if rec.phone:
                    check_phone_no = self.env['res.partner'].search(
                        [('phone', '=', rec.phone),('company_type','=',rec.company_type), ('id', '!=', rec.id)])
                    if check_phone_no:
                        raise ValidationError(_('Phone Number for contact must be unique!'))
            else:
                # company type
                if rec.company_type == 'company' and not rec.no_have_company_registration:
                    if rec.vat:
                        check_vat = self.env['res.partner'].search(
                            [('vat', '=', rec.vat), ('id', '!=', rec.id)])
                        if check_vat:
                            raise ValidationError(_('Registration, License Number must be unique.'))

    # @api.constrains('nrc_number', 'nrc_state', 'nrc_national', 'nrc')
    # def check_nrc_number(self):
    #     for rec in self:
    #         number = rec.nrc_number
    #         state = rec.nrc_state
    #         national = rec.nrc_national
    #         nrc = rec.nrc
    #         x = re.findall("[a-zA-Z!@#$%^&*()_+-]", str(number))
    #         if nrc is False and not state and national is False and number is False:
    #             pass
    #         elif nrc and state and national and number:
    #             pass
    #         else:
    #             raise ValidationError("Check Your NRC and Fill")
    #         if number:
    #             if len(number) < 6:
    #                 raise ValidationError("Enter valid 6 digits NRC number")
    #             elif x:
    #                 raise ValidationError("Contains Character Words")

    @api.onchange('hr_bu_ids')
    def onchange_bu(self):
        return {'domain': {'hr_bu_ids': [('id', 'in', [bu.id for bu in self.env.user.hr_bu_ids])]}}

    @api.onchange('hr_br_ids')
    def onchange_br(self):
        return {'domain': {'hr_br_ids': [('id', 'in', [br.id for br in self.env.user.hr_br_ids])]}}

    @api.onchange('nrc')
    def _onchange_nrc(self):
        self.nrc_state = False
    #
    # @api.model
    # def create(self, vals):
    #     res = super(ResPartnerInherit, self).create(vals)
    #     f = self.env['res.partner'].search(
    #         [('nrc', '=', res.nrc), ('nrc_state', '=', res.nrc_state.id), ('nrc_national', '=', res.nrc_national),
    #          ('nrc_number', '=', res.nrc_number), ('id', '!=', res.id)])
    #     if f:
    #         if res.nrc:
    #             raise ValidationError(_('NRC for contact must be unique!'))
    #     return res
    #
    # def write(self, vals):
    #     res = super(ResPartnerInherit, self).write(vals)
    #     if 'nrc' in vals or 'nrc_state' in vals or 'nrc_national' in vals or 'nrc_number' in vals:
    #         f = self.env['res.partner'].search([('nrc', '=', self.nrc), ('nrc_state', '=', self.nrc_state.id),
    #                                             ('nrc_national', '=', self.nrc_national),
    #                                             ('nrc_number', '=', self.nrc_number), ('id', '!=', self.id)])
    #         if f and self.nrc:
    #             raise ValidationError(_('NRC for contact must be unique!'))
    #     return res


class NRCState(models.Model):
    _name = 'nrc.state'
    _description = 'nrc.state'

    state_number = fields.Selection([
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
        ('6', '6'),
        ('7', '7'),
        ('8', '8'),
        ('9', '9'),
        ('10', '10'),
        ('11', '11'),
        ('12', '12'),
        ('13', '13'),
        ('14', '14'),
    ], string="State Number", required=True)

    name = fields.Char(string="State", required=True)
