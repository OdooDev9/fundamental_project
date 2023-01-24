from odoo import fields, models,api

class ARRepossess(models.Model):
    _name = 'ar.repossess'
    _description = 'AR Repossess'
    _rec_name = 'invoice_id'


    invoice_id = fields.Many2one('account.move','Invoice No')
    partner_id = fields.Many2one('res.partner',string="Customer Name",related='invoice_id.partner_id')

    invoice_type = fields.Many2one('ar.assign.line',string="Invoice Type")
    
    selling_br_id = fields.Many2one('business.unit','Selling BR',related='invoice_id.hr_br_id')
    ar_action_type = fields.Many2one('ar.assign.line',string="AR Action Type")

    # cus_name = fields.Char('Customer Name')
    # invoice_type = fields.Char('Invoice Type')
    # invoice_no = fields.Char('Invoice NO')
    # selling_br = fields.Char('Selling BR')
    # ar_action_type = fields.Char('AR Action Type')
    # confirm = fields.Selection(selection = [('yes', 'Yes'), ('no', 'No')])
    reposess_status = fields.Char('Reposess Status')

    ar_repossess_line_ids = fields.One2many('ar.repossess.line','repossess_line_id')

class ARRepossessLine(models.Model):
    _name = 'ar.repossess.line'
    _description = 'AR Repossess Line'
    _rec_name = 'invoice_num'

    repossess_line_id = fields.Many2one('ar.repossess',string='Repossess')

    date = fields.Char(readonly=True)

    invoice_num = fields.Char('Invoice No.')
    invoice_type = fields.Char('Invoice Type')
    ar_action_type = fields.Char('AR Action Type')
    customer_name = fields.Char('Customer Name')

    action = fields.Selection([
        ('call','Call'),
        ('visit','Visit')
    ],string="Action")
    contact_type = fields.Selection(selection = [('on_target', 'On Target'), ('legal_team', 'Legal Team')], string = 'Contact Type')
    on_target_pic = fields.Char()
    on_target_feedback = fields.Selection(selection = [
        ('reposses_accept', 'Repossess Accept from Customer'), 
        ('machine_reposses', 'Machine Repossessed'), 
        ('machine_give_back', 'Machine Given Back to Customer'),
        ('ar_clear','AR Clearing')], string = 'On Target Feedback')
    pic_comment = fields.Text("On Target PIC Comment")
    reposess_plan_date = fields.Date("Reposses Plan Date")
    mc_reposess_date = fields.Date("MC Repossessed Date")
    mc_location = fields.Many2one('business.unit',string="Machine Location")
    # print(mc_location)
    mc_given_back_date = fields.Date("Machine Given Back Date")

    @api.onchange('invoice_num')
    def onchange_invoice_num(self):
        self.invoice_num = self.repossess_line_id.invoice_id

    @api.onchange('invoice_type')
    def onchange_invoice_type(self):
        self.invoice_type = self.repossess_line_id.invoice_type
    
    @api.onchange('ar_action_type')
    def onchange_ar_action_type(self):
        self.ar_action_type = self.repossess_line_id.ar_action_type

    @api.onchange('customer_name')
    def onchange_customer_name(self):
        self.customer_name = self.repossess_line_id.partner_id

    @api.onchange('on_target_feedback')
    def onchange_reposess_status(self):
        if self.on_target_feedback:
            print("hello***************************************************")
            self.repossess_line_id.reposess_status = dict(self._fields['on_target_feedback'].selection).get(self.on_target_feedback)
            print(self.repossess_line_id.reposess_status)
            print(self.on_target_feedback)
            print(dict(self._fields['on_target_feedback'].selection).get(self.on_target_feedback))
        
            # self.repossess_line_id.reposess_status = self.on_target_feedback.get()

            # dict(self._fields['your_field'].selection).get(self.your_field)