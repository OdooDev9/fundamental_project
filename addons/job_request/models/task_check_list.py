from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)

class  TaskChecklist(models.Model):
	_name = 'task.checklist'
	_description = "Task Checklist"

	name = fields.Char(String="Name",required=True,store=True,copy=False)
	description = fields.Char(String="Description",required=True,store=True,copy=False)
	finished = fields.Boolean(string="Finished",default=False,store=True,copy=False)

	images = fields.Binary("Image",attachment=True,store=True)
	# checklist_template_id = fields.Many2one('checklist.template')
	

class ChecklistTemplate(models.Model):
	_name = 'checklist.template'
	_description = "Checklist template"


	name = fields.Char(String="Name",required=True)
	checklists = fields.Many2many('task.checklist','checklist_template_id',string='Checklists')

class ChecklistTemplate2(models.Model):
	_name = 'checklist.template2'
	_description = 'Checklist template2'

	name = fields.Char(String="Name",required=True)
	checklists = fields.Many2many('checklist',string='Check lists')


class ChecklistLine(models.Model):
	_name = 'checklist.line'
	_description = "Checklist Line"

	finished = fields.Boolean(string="Finished",default=False)
	checklist_id = fields.Many2one('task.checklist',"CheckList")
	template_id = fields.Many2one('job.checklist.templates')
	job_request_id = fields.Many2one('job.request',string="Job Request")

class JobChecklistTemplates(models.Model):
	_name = 'job.checklist.templates'
	_description = 'Job Checklist templates'

	name = fields.Char(String="Name",store=True,copy=False)
	checklists = fields.Many2many('task.checklist',String="Check Lists")
	checklist_progress = fields.Float(string="Progress",default=0.0)

class JobChecklist(models.Model):
	_name = 'job.checklist'
	_description = 'Job Checklist'


	template_id = fields.Many2one('checklist.template',string="Template Id")
	template_name = fields.Char('Template Name')
	show_tmp_name = fields.Boolean(' ',default=False)

	next_line = fields.Char(' ',readonly=True,default=' ')
	show_next_line = fields.Boolean('',default=False)

	name = fields.Char(' ')
	finished = fields.Boolean(' ',default=False)
	description = fields.Char(' ')

	images = fields.Binary("Images",attachment=True)

class ChecklistJob(models.Model):
	_name = 'checklist.job'
	_description = 'Checklist Job'

	title = fields.Char('Title')

	template_id = fields.Many2one('checklist.template2',string="Template ID")
	template_name = fields.Char('Template Name')

	show_tmp_name = fields.Boolean(' ',default=False)

	next_line = fields.Char(' ',readonly=True,default=' ')
	show_next_line = fields.Boolean('',default=False)

	base_checklist_ids = fields.Many2many('base.checklist')

	which1 = fields.Integer(' ',defualt=0)
	text_box1 = fields.Char(' ')
	check_box1 = fields.Boolean(' ',default=False)
	image1 = fields.Binary(' ',attachment=True)
	radio_selection1 = fields.Selection([],string=' ')

	field_name1 = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='Yes/No')

	which2 = fields.Integer(' ',defualt=0)
	text_box2 = fields.Char(' ')
	check_box2 = fields.Boolean(' ',default=False)
	image2 = fields.Binary(' ',attachment=True)

	which3 = fields.Integer(' ',defualt=0)
	text_box3 = fields.Char(' ')
	check_box3 = fields.Boolean(' ',default=False)
	image3 = fields.Binary(' ',attachment=True)

	which4 = fields.Integer(' ',defualt=0)
	text_box4 = fields.Char(' ')
	check_box4 = fields.Boolean(' ',default=False)
	image4 = fields.Binary(' ',attachment=True)

	which5 = fields.Integer(' ',defualt=0)
	text_box5 = fields.Char(' ')
	check_box5 = fields.Boolean(' ',default=False)
	image5 = fields.Binary(' ',attachment=True)

	which6 = fields.Integer(' ',defualt=0)
	text_box6 = fields.Char(' ')
	check_box6 = fields.Boolean(' ',default=False)
	image6 = fields.Binary(' ',attachment=True)

	which7 = fields.Integer(' ',defualt=0)
	text_box7 = fields.Char(' ')
	check_box7 = fields.Boolean(' ',default=False)
	image7 = fields.Binary(' ',attachment=True)

	which8 = fields.Integer(' ',defualt=0)
	text_box8 = fields.Char(' ')
	check_box8 = fields.Boolean(' ',default=False)
	image8 = fields.Binary(' ',attachment=True)

	which9 = fields.Integer(' ',defualt=0)
	text_box9 = fields.Char(' ')
	check_box9 = fields.Boolean(' ',default=False)
	image9 = fields.Binary(' ',attachment=True)

	which10 = fields.Integer(' ',defualt=0)
	text_box10 = fields.Char(' ')
	check_box10 = fields.Boolean(' ',default=False)
	image10 = fields.Binary(' ',attachment=True)

class Checklist(models.Model):
	_name = 'checklist'
	_description = 'checklist'

	title = fields.Char('Title')

	template_id = fields.Many2one('checklist.template2',string="Template ID")
	template_name = fields.Char('Template Name')

	show_tmp_name = fields.Boolean(' ',default=False)

	next_line = fields.Char(' ',readonly=True,default=' ')
	show_next_line = fields.Boolean('',default=False)

	base_checklist_ids = fields.Many2many('base.checklist')

	which1 = fields.Integer(' ',defualt=0)
	text_box1 = fields.Char(' ')
	check_box1 = fields.Boolean(' ',default=False)
	image1 = fields.Binary(' ',attachment=True)
	radio_ids_1 = fields.Many2many('radiobutton')
	radio_selection1 = fields.Selection([(' ',' ')],string=' ')

	which2 = fields.Integer(' ',defualt=0)
	text_box2 = fields.Char(' ')
	check_box2 = fields.Boolean(' ',default=False)
	image2 = fields.Binary(' ',attachment=True)

	which3 = fields.Integer(' ',defualt=0)
	text_box3 = fields.Char(' ')
	check_box3 = fields.Boolean(' ',default=False)
	image3 = fields.Binary(' ',attachment=True)

	which4 = fields.Integer(' ',defualt=0)
	text_box4 = fields.Char(' ')
	check_box4 = fields.Boolean(' ',default=False)
	image4 = fields.Binary(' ',attachment=True)

	which5 = fields.Integer(' ',defualt=0)
	text_box5 = fields.Char(' ')
	check_box5 = fields.Boolean(' ',default=False)
	image5 = fields.Binary(' ',attachment=True)

	which6 = fields.Integer(' ',defualt=0)
	text_box6 = fields.Char(' ')
	check_box6 = fields.Boolean(' ',default=False)
	image6 = fields.Binary(' ',attachment=True)

	which7 = fields.Integer(' ',defualt=0)
	text_box7 = fields.Char(' ')
	check_box7 = fields.Boolean(' ',default=False)
	image7 = fields.Binary(' ',attachment=True)

	which8 = fields.Integer(' ',defualt=0)
	text_box8 = fields.Char(' ')
	check_box8 = fields.Boolean(' ',default=False)
	image8 = fields.Binary(' ',attachment=True)

	which9 = fields.Integer(' ',defualt=0)
	text_box9 = fields.Char(' ')
	check_box9 = fields.Boolean(' ',default=False)
	image9 = fields.Binary(' ',attachment=True)

	which10 = fields.Integer(' ',defualt=0)
	text_box10 = fields.Char(' ')
	check_box10 = fields.Boolean(' ',default=False)
	image10 = fields.Binary(' ',attachment=True)


class BaseChecklist(models.Model):
	_name = 'base.checklist'
	_description = 'Base Checklist'

	selection = fields.Selection([('text_box','Text Box'),('check_box','Check Box'),('radio_button','Radio Button'
		),('image','Image')],string="View Type")

class RadioButton(models.Model):

	_name = 'radiobutton'
	_description = 'Radio Button'

	name = fields.Char(' ')