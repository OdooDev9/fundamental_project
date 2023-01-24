from odoo import _, api, fields, models

class  HTMLChecklistTemplate(models.Model):
	_name = 'html.checklist.template'
	_description = 'HTML Cheklist Template'

	name = fields.Char(string='Template Name',required=True)

	body_html = fields.Html('Body', translate=True, sanitize=False)


class  JobHTMLChecklistTemplate(models.Model):
	_name = 'job.html.checklist.template'
	_description = 'HTML Cheklist Template'

	template_id = fields.Many2one('html.checklist.template',string="Template_ID")

	name = fields.Char(string='Template Name',required=True)

	body_html = fields.Html('Body', translate=True, sanitize=False)
