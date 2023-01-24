from odoo import fields,models

class RecontractWizard(models.TransientModel):
    _name = 're.contract.wizard'

    name = fields.Text('Desc')
    installment_plan_id = fields.Many2one('installment.plan', string="Installment Plan")
    amount = fields.Float('Re-Contract Amount',readonly=True)
    order_id = fields.Many2one('sale.order')

    def recontract(self):
        res = self.env['re.installment.plan'].create({'note': self.name,
                                                      'partner_id': self.order_id.partner_id.id,
                                                      'order_id': self.order_id.id,
                                                      'installment_plan_id': self.installment_plan_id.id,
                                                      'hr_br_id': self.order_id.hr_br_id.id,
                                                      'hr_bu_id': self.order_id.hr_bu_id.id,
                                                      'tenure_amt': self.amount,
                                                      'currency_id': self.order_id.currency_id.id, })
        res._onchange_installment_plan_id()
        # res.action_confirm()(
        res.compute_installment()
        return res