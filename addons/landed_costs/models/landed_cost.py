
from odoo import models, fields, api
from datetime import datetime


class LandedCosts(models.Model):
    _inherit = 'stock.landed.cost'
    _description = 'Landed Costs'

    from_bill = fields.Boolean(string="From Bill")


    def _default_account_journal_id(self):
        """Take the journal configured in the company, else fallback on the stock journal."""
        business_unit = self.env['business.unit'].search([('id','=',self.env.user.current_bu_br_id.id)])
        lc_journal = business_unit.landed_cost_journal_id.id
        return lc_journal


    def action_view_invoice(self):
        invoices = self.mapped('invoice_ids')
        action = self.env.ref('account.action_move_in_invoice_type').read()[0]
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = invoices.id
        else:
            action = {'type': 'ir.actions.act_window_close'}
        context = {
            'default_type': 'in_invoice'
        }
        action['context'] = context
        return action

    def _get_invoice_count(self):
        for line in self:
            line.invoice_count = len(line.invoice_ids)
    def _set_bu_domain(self):
        domain = [('id', 'in', [bu.id for bu in self.env.user.hr_bu_ids])]
        return domain

    invoice_ids = fields.Many2many('account.move', string="Invoices", readonly=True)
    invoice_count = fields.Integer(string="Bill Count", compute="_get_invoice_count", readonly=True)
    business_id = fields.Many2one('business.unit', 'Business Unit', default=lambda self: self.env.user.current_bu_br_id.id,domain=_set_bu_domain)
    visible = fields.Boolean(default=True)

    def create_bill(self):
        invoice_line_vals = []
        for line in self.cost_lines:
            invoice_line_vals.append(
                (0, 0, line._prepare_invoice_line()),
            )

        inv = self.env['account.move'].create({
            'date': datetime.today().date(),
            'invoice_date': datetime.today().date(),
            'invoice_origin': self.name or " ",
            'move_type': 'in_invoice',
            'ref': False,
            'invoice_line_ids': invoice_line_vals,
            'currency_id': self.currency_id.id,
            'hr_bu_id': self.business_id.id,
        })

        self.update({
            'invoice_ids': [inv.id],
            'visible': False,
        })

class LandedCostLine(models.Model):
    _inherit = 'stock.landed.cost.lines'
    _description = 'Stock landed Cost Line'

    def _prepare_invoice_line(self):
        inv_line = {'name': self.name,
                    'product_id': self.product_id.id,
                    'price_unit': self.price_unit,
                    'quantity': 1.0,
                    'product_uom_id': self.product_id.uom_id.id,
                    'account_id': self.account_id.id,
                    }
        return inv_line
    @api.onchange('product_id')
    def onchange_product_id(self):
        self.name = self.product_id.name or ''
        self.split_method = self.product_id.product_tmpl_id.split_method_landed_cost or self.split_method or 'equal'
        self.price_unit = self.product_id.standard_price or 0.0
        accounts_data = self.product_id.product_tmpl_id.get_product_accounts()
        self.account_id = accounts_data['stock_input']
        for rec in self.cost_id:
            return {'domain': {
                'product_id': [('business_id', '=', rec.business_id.id)]}}
