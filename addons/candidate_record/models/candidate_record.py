from odoo import fields, models,api

class CandidateRecord(models.Model):
    _name = 'candidate.record'
    _description = 'Candidate Record!!!'

    name = fields.Char('Name')
    address = fields.Text('Address')
    age = fields.Integer('Age')
    gender = fields.Selection([
        ('male','Male'),
        ('female','Female'),
        ('other','Other')
    ],'Gender')
    education = fields.Text('Education')
    skills = fields.Text('Skills')
    full_time = fields.Boolean('Full Time')
    # not_full_time = fields.Boolean('Not')
    marital_status = fields.Selection([
        ('single','Single'),
        ('married','Married')
    ],'Marital Status')