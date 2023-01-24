from odoo import api, fields, models, _

class AccountAccount(models.Model):
    _inherit = 'account.journal'
    _description = 'Account Journal'

    default_account_id = fields.Many2one(
        comodel_name='account.account', check_company=True, copy=False, ondelete='restrict',
        string='Default Account',
        domain="[('deprecated', '=', False), ('company_id', '=', company_id), ('bu_br_id', '=', bu_br_id),"
               "'|', ('user_type_id', '=', default_account_type), ('user_type_id', 'in', type_control_ids),"
               "('user_type_id.type', 'not in', ('receivable', 'payable'))]")
    suspense_account_id = fields.Many2one(
        comodel_name='account.account', check_company=True, ondelete='restrict', readonly=False, store=True,
        compute='_compute_suspense_account_id',
        help="Bank statements transactions will be posted on the suspense account until the final reconciliation "
             "allowing finding the right account.", string='Suspense Account',
        domain=lambda self: "[('deprecated', '=', False), ('company_id', '=', company_id), ('bu_br_id', '=', bu_br_id), \
                             ('user_type_id.type', 'not in', ('receivable', 'payable')), \
                             ('user_type_id', '=', %s)]" % self.env.ref('account.data_account_type_current_assets').id)

    profit_account_id = fields.Many2one(
        comodel_name='account.account', check_company=True,
        help="Used to register a profit when the ending balance of a cash register differs from what the system computes",
        string='Profit Account',
        domain=lambda self: "[('deprecated', '=', False), ('company_id', '=', company_id), ('bu_br_id', '=', bu_br_id),\
                             ('user_type_id.type', 'not in', ('receivable', 'payable')), \
                             ('user_type_id', 'in', %s)]" % [self.env.ref('account.data_account_type_revenue').id,
                                                             self.env.ref('account.data_account_type_other_income').id])
    loss_account_id = fields.Many2one(
        comodel_name='account.account', check_company=True,
        help="Used to register a loss when the ending balance of a cash register differs from what the system computes",
        string='Loss Account',
        domain=lambda self: "[('deprecated', '=', False), ('company_id', '=', company_id), ('bu_br_id', '=', bu_br_id),\
                             ('user_type_id.type', 'not in', ('receivable', 'payable')), \
                             ('user_type_id', '=', %s)]" % self.env.ref('account.data_account_type_expenses').id)
    code = fields.Char(string='Short Code', size=15, required=True, help="Shorter name used for display. The journal entries of this journal will also be named using this prefix by default.")
    # Bank journals fields
    bank_account_id = fields.Many2one('res.partner.bank',
        string="Bank Account",
        ondelete='restrict', copy=False,
        check_company=True,
        domain="[('bu_br_id', '=', bu_br_id), ('partner_id','=', company_partner_id), '|', ('company_id', '=', False), ('company_id', '=', company_id)]")
