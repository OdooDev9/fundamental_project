from odoo import fields, models,api

class LegalActivity(models.Model):
    _name = 'ar.legal.activity'
    _description = 'Legal Activity'
    _rec_name = 'invoice_id'

    # customer_name = fields.Char(string="Customer Name")
    # invoice_no = fields.Char(string= "Invoice No.")
    invoice_id = fields.Many2one('account.move','Invoice No')
    partner_id = fields.Many2one('res.partner',string="Customer Name",related='invoice_id.partner_id')

    invoice_type = fields.Many2one('ar.assign.line',string="Invoice Type")
    
    selling_br_id = fields.Many2one('business.unit','Selling BR',related='invoice_id.hr_br_id')

    # selling_br = fields.Char(string= "Selling BR")
    # ar_action_type = fields.Char(string= "AR Action Type")
    ar_action_type = fields.Many2one('ar.assign.line',string="AR Action Type")
    legal_status = fields.Text(string="Legal Status")
        
    legal_activity_line_ids = fields.One2many("ar.legal.activity.line","legal_activity_id")

    # @api.onchange('legal_activity_line_ids')
    # def onchange_legal_status(self):
    #     if self.legal_activity_line_ids.on_target_feedback:
    #         print("hello *******************************************************")
    #         self.legal_status = self.legal_activity_line_ids.on_target_feedback
    #     print("**************************")
    #     print(self.legal_activity_line_ids.on_target_feedback)
    #     print(self.legal_status)


class LegalActivityLine(models.Model):
    _name = 'ar.legal.activity.line'
    _description = 'Legal Activity Line'
    _rec_name = 'invoice_num'

    legal_activity_id = fields.Many2one("ar.legal.activity")

    date = fields.Date(string= "Date")

    invoice_num = fields.Char(string="Invoice No.")
    invoice_type = fields.Char(string="Invoice Type")
    ar_action_type = fields.Char(string="AR Action Type")
    partner_id = fields.Char(string="Customer Name")

    action = fields.Selection([
        ('call','Call'),
        ('visit','Visit')
    ],string="Action")
    contact_type = fields.Selection([   
        ('on_terget','On Target'),
        ('legal_team','Legal Team')
    ],string= "Contact Type")
    
    on_target_pic = fields.Char(string="On Target PIC")
    legal_team_pic = fields.Char(string="Legal Team PIC")
    # pic_name = fields.Char()
    on_target_feedback = fields.Selection([
        ('legal_notic','Legal Notic'),
        ('letter','UMG Letter'),
        ('news','Newspaper Announcement'),
        ('legal_action','Legal Action')
    ],string="Confirmation Type",required=True,default='legal_notic')
    notice_times = fields.Char(string="Notice Time")
    pic_comment = fields.Text(string="PIC Comment")
    # attachment= fields.Binary(string="Attachment")
    attachment_ids = fields.Many2many('ir.attachment',string="Attachment")
    
    action_date = fields.Date(string="Action Date")

   

    @api.onchange('invoice_num')
    def onchange_invoice_num(self):
        self.invoice_num = self.legal_activity_id.invoice_id

    @api.onchange('invoice_type')
    def onchange_invoice_type(self):
        self.invoice_type = self.legal_activity_id.invoice_type
    
    @api.onchange('ar_action_type')
    def onchange_ar_action_type(self):
        self.ar_action_type = self.legal_activity_id.ar_action_type

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        self.partner_id = self.legal_activity_id.partner_id

