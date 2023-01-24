from odoo import fields, models,api

class ARAssign(models.Model):
    _name = 'ar.assign'
    _description = 'AR Assign'
    # _rec_name = 'pic_name'

    # date_range = fields.Date("Date Range")
    pic_id = fields.Many2many('hr.employee',string="PIC Name")
    # business_id = fields.Many2many('business.unit',string="Business Unit")
    # branch_ids = fields.Many2many('business.unit',string="Branch")
    bu_ids = fields.Many2many('business.unit', 'assign_business_ref', 'bu_id', 'assign_id',
                                 string='Business Unit', domain="[('business_type','=','bu')]")
    br_ids = fields.Many2many('business.unit', 'assign_branch_ref', 'br_id', 'assign_id', string='Branches',
                                 domain="[('business_type','=','br')]")
    assign_bu = fields.Boolean("BU")
    assign_br = fields.Boolean("BR")
    assign_due_type = fields.Boolean("Due Type")

    invoice_unit_ar = fields.Boolean("Unit AR", default=False)
    invoice_service_ar = fields.Boolean("Service AR", default=False)
    invoice_sparepart_ar = fields.Boolean("Sparepart AR", default=False)
    invoice_rental_ar = fields.Boolean("Rental AR", default=False)
    invoice_lubricant = fields.Boolean("Lubricant", default=False)

    over_due = fields.Boolean("OverDue", default=False)
    future_due = fields.Boolean("Future Due", default=False)
    current_due = fields.Boolean("Current Due", default=False)

    # due_type = fields.Selection(selection=[
    #     ('over_due','Over Due'),
    #     ('future_due','Future due'),
    #     ('current_due','Current due'),
    #     ('all','All')
    # ], string="Due Type")

    date_from = fields.Date()
    date_to = fields.Date()
    report = fields.Selection(selection=[
        ('weekly','Weekly'),
        ('monthly','Monthly'),
        ('yearly','Yearly'),
        ('daily','Daily')
    ],string="Report")
    currency_id = fields.Many2one('res.currency',string="Currency")
    overdue_amount = fields.Monetary(compute='_compute_amount',string='Overdue Amount', store=True)#compute='_compute_amount',
    collected_amount = fields.Monetary(compute='_compute_amount',string='Collected Amount', store=True)
    currentdue_amount = fields.Monetary(compute='_compute_amount',string='Current Due Amount', store=True)
    total_ar_amount= fields.Monetary(compute='_compute_amount',string='Total AR Amount', store=True)


    ar_assing_line_ids = fields.One2many("ar.assign.line","assign_id")

    @api.depends('ar_assing_line_ids.due_amount', 'ar_assing_line_ids.collected_amount', 'ar_assing_line_ids.total_ar_amount')
    def _compute_amount(self):
        """
        Compute the amounts of the AR line.
        """
        print("compute amount===>>")

    def continue_btn(self):
        print("Continue button click")

    def assign_btn(self):
        print("assign button click")

    @api.onchange('invoice_unit_ar', 'invoice_service_ar', 'invoice_sparepart_ar', 'invoice_rental_ar','invoice_lubricant','current_due','future_due','over_due')
    def get_invoice_data(self):
        for rec in self:
            rec.ar_assing_line_ids = None
            search = [('move_type','=','out_invoice')]
            new_lines =self.env['ar.assign.line']
            unit_or_part = []
            due_type = []
            # print('Invoice unit AR--------------------->>>>>',rec.invoice_unit_ar)

            # AR
            if rec.invoice_unit_ar == True:
                unit_or_part.append('unit')
            if rec.invoice_service_ar == True:
                unit_or_part.append(False)
            if rec.invoice_sparepart_ar == True:
                unit_or_part.append('part')
           
            search.append(('unit_or_part','in',unit_or_part))

            
            if rec.invoice_unit_ar == False and rec.invoice_service_ar == False and rec.invoice_sparepart_ar == False:
                pass
            else:
                move_ids = self.env['account.move'].search(search)
                install,data = [],[]
                for move_id in move_ids:
                    # print('Move ID--------------------------->>>>')
                    # print('*'*10)
                    current_due = move_id.installment_ids.filtered(lambda x:x.state == 'current_due')
                    take_action = move_id.installment_ids.filtered(lambda x:x.state == 'take_action')
                    future_due = move_id.installment_ids.filtered(lambda x:x.state == 'draft')
                       
                    if rec.current_due == True:
                        if current_due:
                            install+= current_due
                    if rec.over_due == True:
                        if take_action:
                            install += take_action
                    if rec.future_due == True:
                        if future_due:
                            install +=future_due[1]
            
                for l in install:
                    data.append((0,0,{
                        'partner_id': l.invoice_id.partner_id.id,
                        'invoice_id': l.invoice_id.id,
                        'due_type': l.state,#line.state
                        'due_amount': l.amount,
                    }))

                self.ar_assing_line_ids = data

class ARAssingLine(models.Model):
    _name = 'ar.assign.line'
    _description = 'AR Assign Line'

    assign_id = fields.Many2one("ar.assign",string="List of Current Information")
    name = fields.Char('Description')
    customer_id = fields.Integer(string="ID")
    employee_id = fields.Many2one('hr.employee',string='Employee')
    invoice_id = fields.Many2one('account.move','Invoice No')
    installment_id = fields.Many2one('invoice.installment.line')
    partner_id = fields.Many2one('res.partner',string="Customer Name",related='invoice_id.partner_id')
    business_id = fields.Many2one('business.unit',string="BU/BR",related='invoice_id.hr_bu_id')
    due_amount = fields.Monetary(string="Due Amount")
    collected_amount = fields.Monetary(string="Collected Amount",related='installment_id.principal_paid')
    total_ar_amount = fields.Float(string="Total AR Amount")
    currency_id = fields.Many2one('res.currency',string="Currency",related='invoice_id.currency_id')
    due_date = fields.Date('Due Date',related='installment_id.payment_date')
    fine_amount = fields.Monetary('Fine Amount',related='installment_id.fine_amount')
    remaining_ar_balance = fields.Monetary(related='installment_id.ar_balance',string="Remaining AR Balanace")
    # invoice_type = fields.Char()
    selling_br_id = fields.Many2one('business.unit','Selling BR',related='invoice_id.hr_br_id')
    due_type = fields.Selection(selection=[
        ('take_action','Over Due'),
        ('draft','Future due'),
        ('current_due','Current due'),
        ('downpayment_due','Downpayment Due')
    ], string="Due Type")

    ar_action_type = fields.Selection([
        ('ar_followup','AR Follow Up'),
        ('ar_confirm','AR Confirm'),
        ('ar_remind','AR Remind')
    ],string="AR Action Type",compute='_compute_ar_action_type')

    invoice_type = fields.Selection([
        ('unit','Unit AR'),
        ('part','Sparepart AR'),
        ('service','Service AR')
    ], string="Invoice Type")
    ar_follow_up_line_ids = fields.One2many("ar.follow.up","assign_id",string="AR Followup" )
    ar_confirm_line_ids = fields.One2many("ar.confirm","assign_id",string="AR Confirm" )
    ar_remind_line_ids = fields.One2many("ar.remind","assign_id",string="AR Remind" )

    @api.depends('due_type')
    def _compute_ar_action_type(self):
        for rec in self:
            if rec.due_type == 'take_action':
                rec.ar_action_type = 'ar_followup'
            if rec.due_type == 'draft':
                rec.ar_action_type = 'ar_confirm'
            if rec.due_type == 'current_due':
                rec.ar_action_type = 'ar_remind'



# AR Follow UP Line Model
class ARFollowUpLine(models.Model):
    _name = 'ar.follow.up'
    _description = 'AR Follow UP'

    assign_id = fields.Many2one("ar.assign.line")

    date = fields.Date(string= "Date")
    action = fields.Selection([
        ('call','Call'),
        ('visit','Visit')
    ],string="Action")
    #  if contact type = related BR
    br_pic_id = fields.Many2one('business.unit',"BR PIC",domain="[('business_type','=','br')]")
    contact_type = fields.Selection([
        ('customer','Customer'),
        ('on_terget','On Target'),
        ('related_br','Related BR')
    ],string= "Contact Type")

    # if contact type = customer
    partner_id = fields.Many2one('res.partner','Partner')
    customer_phone = fields.Char(string= "Customer Phone",related='partner_id.phone')
    contact_action = fields.Selection([
        ('available','Available'),
        ('not_available','Not Available')
    ],string="Customer Feedback Type")

    # if call available
    fullowup_reason_id = fields.Many2one('followup.customer',string="Customer Reason")
    comment = fields.Text(string= "Comment")
    promised_payment_date = fields.Date(string= "Promised Payment Date")
    promised_payment_amt = fields.Float(string= "Promised Payment Amount")
    currency_id = fields.Many2one('res.currency','Currency')

    # if call not available
    contact_feedback_type = fields.Selection([
        ('power_off','Power Off'),
        ('wrong_no','Wrong Number'),
        ('no_answer','No Answer')
    ])

    # if contact type = On target
    on_target_pic = fields.Many2one('hr.employee',string="On Target PIC")
    followup_ontarget_fb = fields.Selection([
        ('contact','Contact Loss'),
        ('location','Loaction Loss'),
        ('negotiation','Negotiation State'),
        ('legal_notice','Legal Notice'),
        ('repossess','Legal Notice For Repossess'),
        ('cash_collected','Cash Collected')
        ],string="On Target Feedback")
    notic_time = fields.Char(string="Notice Time")
    notic_date = fields.Date(string="Notice Date")
    pic_comment = fields.Text(string="PIC Comment")
    attachment = fields.Binary(string="Attachment")

    #  if contact type = related BR
    # followup_br_id = fields.Many2one('followup.br.feedback','Negotiation State')
    br_feedback = fields.Selection([
        ('contact','Contact Loss'),
        ('location','Loaction Loss'),
        ('negotiation','Negotiation State'),
        ],string="BR Feedback")
    nego_payment_date = fields.Date(string="Negotiate Payment Date")
    nego_payment_amount = fields.Float(string="Negotiate Payment Amount")
    
class ARConfirmLine(models.Model):
    _name = 'ar.confirm'
    _description = 'AR Confirm'

    assign_id = fields.Many2one("ar.assign.line")

    date = fields.Date(string="Date")
    action = fields.Selection([
        ('call','Call'),
        ('visit','Visit')
    ])
    contact_type = fields.Selection([
        ('customer','Customer')
    ])
    confirmation_type = fields.Selection([
        ('statement','Statement Confirm'),
        ('balance','AR Balance Confirm')
    ])

    contact_action = fields.Selection([
        ('available','Available'),
        ('not_available','Not Available')
    ],string="Customer Feedback Type")

    # ar_confirm_reason_id = fields.Many2one('ar.confirm.reason',string="Customer Feedback")
    customer_feedback = fields.Selection([('confirm','Confirm'),('not_confirm','Not Confirm')],string="Confirmation Status")
    customer_reason = fields.Selection([
        ('fine_amt_issue','Fine Amount Issue'),
        ('payment_issue','Payment Issue')
    ],string="Reason")
    attachment = fields.Binary(string="Attachment")
    payment_collected_person = fields.Char(string="Payment Collected Person")
    comment = fields.Text(string="Comment")
    contact_feedback_type = fields.Selection([
        ('power_off','Power Off'),
        ('wrong_no','Wrong Number'),
        ('no_answer','No Answer')
    ],string="Contact Feedbacl Type")
    future_due_payment_term = fields.Integer(string="Futue Due Payment Term")
    boh_comment = fields.Text(string="BOH Comment")
    bu_fa_comment = fields.Text(string="Bu F&A Comment")
    bu_gm_comment = fields.Text(string="BU GM Comment")
    coo_comment =  fields.Text(string="COO Comment")
    coo_feedback = fields.Selection([
        ('ar_confirm','AR Confirmed with Customer'),
        ('legal_action','Legal Action to Employee')
    ],string="COO Feedback")

    state = fields.Selection([
        ('boh_approve',"BOH Approve"),
        ('bu_fa_approve',"BU FA DH Approve"),
        ('bu_gm_approve',"BU GM Approve"),
        ('coo_approve',"COO Approve")
    ],default="boh_approve",string="Status")

    def action_boh_approve(self):
        print("BOH approve button clicked")
        # for rec in self:
        #     rec.approve_states = 'boh_approve'
        #     rec.bu_fa_comment = 'invisible'
        #     rec.bu_gm_comment = 'invisible'
        #     rec.coo_comment = 'invisible'
    
    def action_bu_fa_approve(self):
        print("BU F&A approve button click")
        # self.boh_comment = 'invisible'
        # self.bu_gm_comment = 'invisible'
        # self.coo_comment = 'invisible'
    
    def action_bu_gm_approve(self):
        print("BU GM approve button click")
        # self.boh_approve = 'invisible'
        # self.bu_fa_comment = 'invisible'
        # self.coo_approve = 'invisible'

    def action_coo_approve(self):
        print("COO approve button clicked")
        # self.boh_comment = 'invisible'
        # self.bu_fa_comment = 'invisible'
        # self.bu_gm_comment = 'invisible'        

# class ARFollowUpLine(models.Model):
#     _inherit="ar.confirm"

class ARRemindLine(models.Model):
    _name = 'ar.remind'
    _description = 'AR Remind'

    assign_id = fields.Many2one("ar.assign.line")

    date = fields.Date(string="Date")
    action = fields.Selection([
        ('call','Call'),
        ('visit','Visit')
    ],string="Action")
    contact_type = fields.Selection([
        ('customer','Customer')
    ],string="Contact Type")
    customer_phone = fields.Char(string= "Customer Phone")
    remind_type = fields.Selection([
        ('before_due','Before Due Date'),
        ('after_due','After Due Date'),
        ('after_due_fine','After Due Date With Fine Info')
        ],string="Remind Type")
    contact_action = fields.Selection([
        ('available','Available'),
        ('not_available','Not Available')
    ],string="Customer Feedback Type")
    remind_customer_fb_id = fields.Many2one('remind.customer.feedback','Customer Feedback')
    comment = fields.Text(string="Comment")
    promised_payment_date = fields.Date(string="Promised Payment Date")
    promised_payment_amt = fields.Float(string="Promised Payment Amount")
    contact_feedback_type = fields.Selection([
        ('power_off','Power Off'),
        ('wrong_no','Wrong Number'),
        ('no_answer','No Answer')
    ],string="Contact Feedbacl Type")