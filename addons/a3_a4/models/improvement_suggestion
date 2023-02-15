from odoo import models,fields,api

class ARAssign(models.Model):
    _name = 'improvement.suggestion'

    name = fields.Char(string='Doc No', required=True, copy=False,default=lambda self: ('New'))
    issue_date = fields.Date(string='Issue Date:[Date]')
    proposed_id = fields.Many2one('hr.employee',string='Proposed By')
    proposed_email = fields.Char(string='Proposed By Email')
    designation = fields.Char(string='Designation')
    div_bu_br = fields.Char(string='Division/Bu/Branch Name')
    dept_name = fields.Char(string='Department Name')
    facilitor_id = fields.Many2one('hr.employee',string='Facilitated By')
    facilitor_email = fields.Char(string='Facilitated By Email')
    dh_name = fields.Many2one('hr.employee',string='Department Head Name')
    dh_email = fields.Char(string='Department Head Email')
    improvment_theme = fields.Text('IMPROVEMENT THEME')
    cur_con_analyze = fields.Text('CURRENT CONDITION ANALYZE')
    improvement_suggestion = fields.Text('IMPR(OVEMENT SUGGESTION')
    safety_healthy = fields.Boolean(string='Safety/Healthy')
    quality = fields.Boolean(string='Quality (next process/customer satisfaction)')
    cost_budget = fields.Boolean(string='Cost/Budget')
    delivery = fields.Boolean(string='Delivery (next process/customer send on time)')
    morality = fields.Boolean(string='Morality/Good Habit')
    man_people = fields.Boolean(string='Man/People')
    machine = fields.Boolean(string='Machine/Equipment/Tools')
    method = fields.Boolean(string='Method/Process(SOP)')
    material = fields.Boolean(string='Material/Parts')
    environment = fields.Boolean(string='Environment')
    information = fields.Boolean(string='Information')
    sort = fields.Boolean(string='Sort (Separating needed & unneeded)')
    set_in_order = fields.Boolean(string='Set in Order (Keep well & easy to retrieval)')
    shine = fields.Boolean(string='Shine (Neat & Clean)')
    standardize = fields.Boolean(string='Standardize (Standard for 3S above)')
    sustain = fields.Boolean(string='Sustain (Do it & maintain with discipline)')
    improvement_scope = fields.Selection([
        ('individual', 'Individual Improvement'),
        ('departmental','Departmental Improvement'),
        ('whole_umg','The Whole UMG Improvement'),
        ('other','Other Improvement')
    ], string='Improvement Scope')
    before = fields.Image(string='Before Improvement')
    after = fields.Image(string='After Improvement')   
    deliverables = fields.Text(string='DELIVERABLES')
    next_improve_plan = fields.Text(string='NEXT IMPROVEMENT PLAN')
    create_by = fields.Many2one('res.user',string='Created By:')
    create_date = fields.Datetime('Create Date')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('add', 'Add'),
        ('approve', 'Approve'),
        ('close', 'Close')
    ], string='State')