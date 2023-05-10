from odoo import models,fields

class Session(models.Model):
    _name = 'session'

    name = fields.Char('Name')
    start_date = fields.Date('Start Date')
    end_date = fields.Date('Duration')
    seat = fields.Integer('Number of Seat')