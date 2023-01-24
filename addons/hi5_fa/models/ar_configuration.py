from odoo import models, fields, api

# Assign Team
class AssignTeam(models.Model):
    _name = 'assign.team'
    _inherit = ['mail.thread','mail.activity.mixin']
    _description = 'AR Assign Team'

    name = fields.Char('Description')
    employee_ids = fields.Many2many('hr.employee',string="PIC Name")
    business_ids = fields.Many2many('business.unit', 'assign_team_business_ref', 'bu_id', 'assign_id',
                                string='Business Unit', domain="[('business_type','=','bu')]")
    branch_ids = fields.Many2many('business.unit', 'assign_team_branch_ref', 'br_id', 'assign_id', string='Branches',
                                domain="[('business_type','=','br')]")
    over_due = fields.Boolean("OverDue", default=False)
    future_due = fields.Boolean("Future Due", default=False)
    current_due = fields.Boolean("Current Due", default=False)

    invoice_unit_ar = fields.Boolean("Unit AR", default=False)
    invoice_service_ar = fields.Boolean("Service AR", default=False)
    invoice_sparepart_ar = fields.Boolean("Sparepart AR", default=False)
    invoice_rental_ar = fields.Boolean("Rental AR", default=False)
    invoice_lubricant = fields.Boolean("Lubricant", default=False)

# Customer Reason
class CustomerReason(models.Model):
    _name = 'followup.customer'
    _inherit = ['mail.thread','mail.activity.mixin']
    _description = 'Customer Reason'

    name = fields.Char('Name',required=True)

# Ontarget Feedback
class OntergetFeedback(models.Model):
    _name = 'followup.ontarget.feedback'
    _inherit = ['mail.thread','mail.activity.mixin']
    _description = 'Ontarget Feedback'

    name = fields.Char('Name',required=True)

# BR Feedback
class BRFeedback(models.Model):
    _name = 'followup.br.feedback'
    _inherit = ['mail.thread','mail.activity.mixin']
    _description = 'BR Feedback'

    name = fields.Char('Name',required=True)

# AR Confirm Reason
class ARConfirmReason(models.Model):
    _name = 'ar.confirm.reason'
    _inherit = ['mail.thread','mail.activity.mixin']
    _description = 'AR Confirm Reason'

    name = fields.Char('Name',required=True)

# Remind Customer Feedback
class RemindCustomerFeedback(models.Model):
    _name = 'remind.customer.feedback'
    _inherit = ['mail.thread','mail.activity.mixin']
    _description = 'Customer Feedback'

    name = fields.Char('Name',required=True)

# Repossess Ontarget Feedback
class OntergetFeedback(models.Model):
    _name = 'repossess.ontarget.feedback'
    _inherit = ['mail.thread','mail.activity.mixin']
    _description = 'Repossess Onterget Feedback'

    name = fields.Char('Name',required=True)

# Customer recontract Action
class CustomerRecontractAction(models.Model):
    _name = 'customer.recontract.action'
    _inherit = ['mail.thread','mail.activity.mixin']
    _description = 'Customer recontract Action'

    name = fields.Char('Name',required=True)

# Legal Action
class LegalOntargetFeedback(models.Model):
    _name = 'legal.ontarget.feedback'
    _inherit = ['mail.thread','mail.activity.mixin']
    _description = 'Legal Ontarget Feedback'

    name = fields.Char('Name',required=True)