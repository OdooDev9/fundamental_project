from odoo import api, fields, models
from odoo.exceptions import ValidationError

class RejectProcessWizard(models.TransientModel):
    _name = "budget.reject"
    _description = "Reject Wizard Budget(Monthly,Weekly),Claim, Clearance"

    reject_reason = fields.Text(string='Reason')
    origin_rec_id = fields.Integer()
    reject_user_id = fields.Many2one("res.users","Rejected By", default=lambda self:self.env.user)
    model_name = fields.Char("Res Model Name")

    def action_process(self):
        process_record_id = self.env[self.model_name].search([('id','=',self.origin_rec_id)])
        process_record_id.state = 'rejected'
        process_record_id.reject_reason = self.reject_reason
        process_record_id.reject_user_id = self.reject_user_id.id
        process_record_id.btn_f_n_a = False
        process_record_id.btn_gm = False
        process_record_id.btn_coo = False
        process_record_id.btn_pic = False
        process_record_id.btn_cfd = False
        process_record_id.btn_boh = False
        if self.model_name != 'monthly.budget.request':
            process_record_id.btn_cmc = False
            process_record_id.btn_cfo = False
            process_record_id.btn_ceo = False
            process_record_id.btn_ccd = False
