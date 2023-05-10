from odoo import models,fields,api

class Course(models.Model):
    _name = 'course'

    title = fields.Char('Title',required=True)
    description = fields.Text('Description')