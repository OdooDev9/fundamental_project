# -*- coding: utf-8 -*-
from re import T
from odoo import models, fields, api
from datetime import timedelta, datetime
import logging
_logger = logging.getLogger(__name__)
from odoo.exceptions import ValidationError
from odoo.tools.translate import _
import calendar

class ResCompany(models.Model):
    _inherit = 'res.company'
    _description = 'Res Company'

    employee_id = fields.Many2one('hr.employee', string='Employee')

class JobCategory(models.Model):
    _name = 'job.category'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Res Company'

    name = fields.Char('Job Category Name')

class JobType(models.Model):
    _name = 'job.type'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Job Type'

    name = fields.Char('Type Name')

class MinAge(models.Model):
    _name = 'min.age'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Min Age'

    name = fields.Char('Minimun Age')

class MaxAge(models.Model):
    _name = 'max.age'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Max Age'

    name = fields.Char('Maximum Age')

class ServiceYear(models.Model):
    _name = 'service.year'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Service Year'

    name = fields.Char('Service Year')

class HrJob(models.Model):
    _inherit = 'hr.job'
    _description = 'Hr Job'

    employee_id = fields.Many2one('hr.employee', string='Employee')
    haxid = fields.Char()
    jd = fields.Text('Job Description')
    jr = fields.Text('Job Requirements')
    category_id = fields.Many2one('job.category', string='Job Category')
    education = fields.Char('Education')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('both', 'Male and Female')], string='Preferred Gender', required=True)
    job_type_id = fields.Many2one('job.type', string='Job Type')
    job_level = fields.Selection([
        ('fresher', 'Fresher'),
        ('experience', 'Experience')], string='Job Level')
    emp_level_id = fields.Many2one('position.level', string='Position Level')
    job_industry_id = fields.Many2one('job.industry', string='Job Industry')
    location_id = fields.Many2one('hr.location', string='Location(State)')
    holding_id = fields.Many2one('business.unit', string='Holding Business')
    sub_id = fields.Many2one('business.unit', string='Sub Business')
    salary_type = fields.Selection([
        ('daily', 'Daily'),
        ('monthly', 'Monthly')], string='Salary Type')
    maximun_salary = fields.Integer('Maximun Salary')
    is_max_sal = fields.Boolean('Is Max Salary', default=False)
    computer_skill = fields.Selection([
        ('basic', 'Basic'),
        ('intermidiate', 'Intermidiate'),
        ('advance', 'Advance')], string='Computer Skill Level')
    is_com_skill = fields.Boolean('Is Computer Skill', default=False)
    english_level = fields.Selection([
        ('basic', 'Basic'),
        ('intermidiate', 'Intermidiate'),
        ('advance', 'Advance')], string='English Level')
    is_eng_lvl = fields.Boolean('Is Eng Level', default=False)
    other_quali_id = fields.Many2one('job.other.quali', string='Other Qualification')
    min_age_id = fields.Many2one('min.age', string='Minimum Age')
    max_age_id = fields.Many2one('max.age', string='Maximun Age')
    service_id = fields.Many2one('service.year', string='Service Year')
    cv_screening_id = fields.Many2one(
        'survey.survey', "CV Screening Form",
        domain=[('category', '=', 'hr_recruitment')])
    position_level_id = fields.Many2one('position.level', string='Position Level')
    station_id = fields.Many2one('hr.station', string='Station')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    jd_id = fields.Many2one('hr.job.description', string='Job Description')

class HrBlood(models.Model):
    _name = 'hr.blood.type'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Hr blood type'

    name = fields.Char('Blood')
    haxid = fields.Char()

    _sql_constraints = [
        ('_unique', 'unique (name)', 'No duplication of Blood Type is allowed')
    ]

class NrcNo(models.Model):
    _name = 'nrc.no'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Nrc no'

    name = fields.Char(string='Name', required=True)
    nrc_no_mm = fields.Char(string='နာမည်', required=True)
    haxid = fields.Char()

    _sql_constraints = [
        ('_unique', 'unique (name)', 'No duplication of NRC Code is allowed')
    ]

class NrcDescription(models.Model):
    _name = 'nrc.description'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Nrc Description'

    name = fields.Char('Name', required=True)
    nrc_desc_mm = fields.Char()
    nrc_no_id = fields.Many2one('nrc.no', string='NRC No', required=True)
    haxid = fields.Char()

class NrcType(models.Model):
    _name = 'nrc.type'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Nrc Type'

    name = fields.Char('Name', required=True)
    nrc_type_mm = fields.Char('နာမည်', required=True)
    haxid = fields.Char()

    _sql_constraints = [
        ('_unique', 'unique (name)', 'No duplication of NRC Type is allowed')
    ]

class NrcNo(models.Model):
    _name = 'nrc.no.mm'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Nrc no mm'

    name = fields.Char('နာမည်', required=True)
    haxid = fields.Char()

class NrcDescription(models.Model):
    _name = 'nrc.description.mm'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Nrc description MM'

    name = fields.Char(string="နာမည်")
    nrc_no_id = fields.Many2one('nrc.no', string='NRC နာမည်', required=True)
    haxid = fields.Char()

class NrcType(models.Model):
    _name = 'nrc.type.mm'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Nrc Type MM'

    name = fields.Char('နာမည်', required=True)
    haxid = fields.Char()

class HrReligion(models.Model):
    _name = 'hr.religion'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Hr Religion'

    name = fields.Char('Name', required=True)
    haxid = fields.Char()

class HrRace(models.Model):
    _name = 'hr.race'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Hr Race'

    name = fields.Char('Name', required=True)
    haxid = fields.Char()

class HrEducation(models.Model):
    _name = 'hr.other.qualification'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Hr Other Qualification'

    name = fields.Char('Degree')
    institute = fields.Char('Institute', required=True)
    year = fields.Char('Graduation Year', required=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    major = fields.Char('Major(Functional/Technical)')
    quali_type_id = fields.Many2one('qualification.type', string='Qualification Type')
    city_id = fields.Many2one('hr.city', string='City')
    country_id = fields.Many2one('hr.country', string='Country')
    education_type = fields.Selection([
        ('school', 'School'),
        ('university', 'University')], string='Education Type', default='university', required=True)
    haxid = fields.Char()

class HrFamily(models.Model):
    _name = 'hr.family'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Hr Family'

    name = fields.Char('Name', required=True)
    burmese_name = fields.Char('အမည်', required=True)
    dob = fields.Date('Date of Birth', required=False)
    relation_id = fields.Many2one('hr.family.relation', string='Relation', required=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    haxid = fields.Char()

class HrFamilyRelation(models.Model):
    _name = 'hr.family.relation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Hr Family Relation'

    name = fields.Char('Name', required=True)
    haxid = fields.Char()

class HrExperience(models.Model):
    _name = 'hr.experience'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Hr Experience'

    name = fields.Char('Job Title')
    current_job = fields.Boolean('Current Job?')
    company = fields.Char('Company')
    from_period = fields.Date('Period From')
    to_period = fields.Date('Period To')
    start_position = fields.Char('Start Position')
    end_position = fields.Char('End Position')
    last_salary = fields.Integer('Last Salary')
    job_function_id = fields.Many2one('job.function', string='Job Function')
    position_level_id = fields.Many2one('position.level', string='Position Level')
    job_industry_id = fields.Many2one('job.industry', string='Job Industry')
    resign_reason = fields.Text('Reason for Leaving')
    city_id = fields.Many2one('hr.city', string='City')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    haxid = fields.Char()

class HrOtherQualification(models.Model):
    _name = 'hr.education'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Hr Education'
    _rec_name = 'employee_id'

    degree_id = fields.Many2one('education.degree', string='Degree')
    major_id = fields.Many2one('hr.major', string='Major', required=True)
    institute_id = fields.Many2one('hr.university', string='Institute', required=True)
    from_year = fields.Date('From Year')
    to_year = fields.Date('To Year')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    university_type = fields.Selection([
        ('student', 'Student'),
        ('graduated', 'Graduated')], string='University Type', default='graduated')
    current_year = fields.Selection([
        ('first_year', 'First Year'),
        ('second_year', 'Second Year'),
        ('third_year', 'Third Year'),
        ('fourth_year', 'Fourth Year'),
        ('fifth_year', 'Fifth Year'),
        ('final_year', 'Final Year'),
        ('honus', 'Honus'),
        ('master', 'Master'),
        ('phd', 'PHD')], string='Current Year')
    highest_year = fields.Selection([
        ('first_year', 'First Year'),
        ('second_year', 'Second Year'),
        ('third_year', 'Third Year'),
        ('fourth_year', 'Fourth Year'),
        ('fifth_year', 'Fifth Year'),
        ('final_year', 'Final Year')], string='Highest Year')
    education_type = fields.Selection([
        ('school', 'School'),
        ('university', 'University')], string='Education Type', default='university', required=True)

    school_type = fields.Selection([
        ('basic', 'Basic'),
        ('middle', 'Middle'),
        ('high', 'High')], string='School Type')
    school_name = fields.Char('School Name')
    school_from = fields.Date('From Year')
    school_to = fields.Date('To Year')
    city_id = fields.Many2one('hr.city', string='City')
    country_id = fields.Many2one('hr.country', string='Country')
    date = fields.Date('Date', default=fields.Date.today())
    haxid = fields.Char()

class HrBank(models.Model):
    _name = 'hr.bank'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Hr Bank'

    bank_id = fields.Many2one('res.bank', string="Bank Name")
    name = fields.Char('Bank Name')
    branch_name = fields.Char('Branch Name')
    branch_code = fields.Char('Branch Code')
    account_title = fields.Char('Account Title')
    smart_card = fields.Char('Smart Card Number')
    account_type = fields.Many2one('hr.bank.type', string='Account Type')
    smart_pay = fields.Char('Smart Pay Number')
    payment_method = fields.Selection([('card', 'Smart Card Number'),
                                       ('pay', 'Smart Pay Number')], string='Payment Method')
    active = fields.Boolean('Active', required=True, default=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    haxid = fields.Char()

class HrBankType(models.Model):
    _name = 'hr.bank.type'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Hr Bank Type'

    name = fields.Char('Account Type', required=True)
    haxid = fields.Char()

class HrSSB(models.Model):
    _name = 'hr.ssb'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Hr SSB'

    ssb_no = fields.Char('SSB No', required=True)
    emp_no = fields.Char('Employee No', required=True)
    attach_id = fields.Many2one('ir.attachment', string='Attachment File')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    haxid = fields.Char()

class HrRank(models.Model):
    _name = 'hr.rank'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Hr Rank'

    name = fields.Char('Rank', required=True)
    haxid = fields.Char()

class HrRankSalary(models.Model):
    _name = 'hr.rank.salary'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Hr Rank Salary'

    from_rank_id = fields.Many2one('hr.rank', string='From Rank')
    to_rank_id = fields.Many2one('hr.rank', string='To Rank')
    min_salary = fields.Integer('Minimum Salary')
    max_salary = fields.Integer('Maximum Salary')
    haxid = fields.Char()

class HrDepartment(models.Model):
    _inherit = 'hr.department'
    _description = 'Add Haxid'

    haxid = fields.Char()

class HrBusiness(models.Model):
    _inherit = 'business.unit'
    _order = "name desc"
    _description = 'Hr Business'

    haxid = fields.Char()

    def employee_get(self):
        emp_id = self.env.context.get('default_employee_name', False)
        if emp_id:
            return emp_id
        ids = self.env['hr.employee'].search([('user_id', '=', self.env.uid)])
        if ids:
            return ids[0]
        return False

class HrStation(models.Model):
    _name = 'hr.station'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "name desc"
    _description = 'Hr Station'

    def employee_get(self):
        emp_id = self.env.context.get('default_employee_name', False)
        if emp_id:
            return emp_id
        ids = self.env['hr.employee'].search([('user_id', '=', self.env.uid)])
        if ids:
            print('.................. id ',ids)
            return ids[0]
        return False

    name = fields.Char('Station Name')
    active = fields.Boolean('Active',default=True)
    latitude = fields.Char('Latitude')
    longitude = fields.Char('Longitube')
    area = fields.Char('Area')
    employee_id = fields.Many2one('hr.employee', default=employee_get,string='Record Updated By',tracking=True,store=True,readonly=True)
    updated_date = fields.Date('Record Updated On',default=fields.date.today(),tracking=True,store=True,readonly=True)
    type = fields.Char('Sation Type')
    parent_id = fields.Many2one('hr.station','Parent Station')
    currecyuse = fields.Char('Currency Use')
    currecysign = fields.Char('Currency Sign')
    no = fields.Char('Number')
    street = fields.Char('Street')
    quarter = fields.Char('Quarter')
    township_id = fields.Many2one('hr.township', string='Township')
    city_id = fields.Many2one('hr.city', string='City')
    region_id = fields.Many2one('hr.region', string='Region')
    country_id = fields.Many2one('hr.country', string='Country')
    country_code = fields.Char(related="country_id.country_code", string='Country Code')
    ph_no = fields.Char('Phone Number')
    fax = fields.Char('Fax Number')
    email = fields.Char('Email Address')
    website = fields.Char('Website')
    note = fields.Text('Additional Note')
    haxid = fields.Char()

    def employee_get(self):
        emp_id = self.env.context.get('default_employee_name', False)
        if emp_id:
            return emp_id
        ids = self.env['hr.employee'].search([('user_id', '=', self.env.uid)])
        if ids:
            return ids[0]
        return False

class ResUserInherited(models.Model):
    _inherit = 'res.users'
    _description = 'Users'

    haxid = fields.Char()

class ResUserInherited(models.Model):
    _inherit = 'res.partner'
    _description = 'Partner'

    haxid = fields.Char()

class PositionLevel(models.Model):
    _name = 'position.level'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'level desc'
    _description = 'Position Level'

    name = fields.Char('Position Level Name', required=True)
    level = fields.Integer('Level', required=True)
    active = fields.Boolean('Active', default=True)
    haxid = fields.Char()  # <--- Add WYM 6/1/2022

    _sql_constraints = [
        ('_unique', 'unique (name)', 'No duplication of Position Level is allowed')
    ]

class HrJobLevel(models.Model):
    _name = 'hr.job.level'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Hr Job Level'

    name = fields.Char('Job Level', required=True)
    haxid = fields.Char()

class QualificationType(models.Model):
    _name = 'qualification.type'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Qualification Type'

    name = fields.Char('Qualification Type', required=True)
    haxid = fields.Char()

class EducationType(models.Model):
    _name = 'education.type'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Education Type'

    name = fields.Char('Education Type', required=True)
    haxid = fields.Char()

class EducationDegree(models.Model):
    _name = 'education.degree'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Education Degree'

    name = fields.Char('Education Degree', required=True)
    haxid = fields.Char()


class HrMajor(models.Model):
    _name = 'hr.major'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Hr Major'

    name = fields.Char('Major Name', required=True)
    haxid = fields.Char()

class HrUniversity(models.Model):
    _name = 'hr.university'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Hr University'

    name = fields.Char('University Name', required=True)
    haxid = fields.Char()

class JobIndustry(models.Model):
    _name = 'job.industry'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Job Industry'

    name = fields.Char('Job Industry', required=True)
    haxid = fields.Char()

class JobFunction(models.Model):
    _name = 'job.function'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Job Function'

    name = fields.Char('Job Function', required=True)
    code = fields.Char('Code', required=True)
    haxid = fields.Char()

class HrRegion(models.Model):
    _inherit = 'hr.region'
    _description = 'Hr Region'

    haxid = fields.Char()


class HrCity(models.Model):
    _inherit = 'hr.city'

    haxid = fields.Char()

class HrTownship(models.Model):
    _inherit = 'hr.township'
  
    haxid = fields.Char()

class TownshipDistrict(models.Model):
    _inherit = 'hr.district'

    haxid = fields.Char()

# class HrCountry(models.Model):
#     _inherit = 'hr.country'
#
#     haxid = fields.Char()
#     limit = fields.Integer(required=True, help='For Number of Phone Number')

class CandidateProgram(models.Model):
    _name = 'candidate.program'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Candidate Program'
    _rec_name = 'code'

    name = fields.Char('Program Name')
    code = fields.Char('Code')
    haxid = fields.Char()

    @api.model_create_multi
    def create(self, vals_list):
        res = super(CandidateProgram, self).create(vals_list)
        for r in res:
            self.env['ir.sequence'].sudo().create({
                'name': r.code,
                'code': r.code,
                'prefix': r.code,
                'padding': 5,
                'number_increment': 1,
            })
        return res

class HrLocation(models.Model):
    _name = 'hr.location'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Hr Location'

    name = fields.Char('Location Name')
    haxid = fields.Char()
    parent_location_id = fields.Many2one('hr.location')
    active = fields.Boolean(default=True)

class ChiefNameCode(models.Model):
    _name = 'chief.name.code'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Chief Name Code'

    name = fields.Char('Execitive Officer Name', required=True)
    code = fields.Char('Execitive Officer Code', required=True)
    active = fields.Boolean('Active', default=True, required=True)
    remark = fields.Text('Remark')

    _sql_constraints = [
        ('_unique', 'unique (code)', 'No duplication of Executive Officer Code is allowed')
    ]

class BusinessType(models.Model):
    _name = 'business.type'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Business Type'

    name = fields.Char('Business Type Name', required=True)
    active = fields.Boolean('Active', required=True)

    _sql_constraints = [
        ('_unique', 'unique (name)', 'No duplication of Business Type is allowed')
    ]

class MasterCompetency(models.Model):
    _name = 'master.competency'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Master Competency'

    name = fields.Char('Competency Name')

class HrCompetency(models.Model):
    _name = 'hr.competency'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Hr Competency'

    def name_get(self):
        res = []
        for rec in self:
            name = rec.position_level_id.name
            res.append((rec.id, name))
        return res

    position_level_id = fields.Many2one('position.level', string='Position Level', required=True)
    line_ids = fields.One2many('hr.competency.line', 'competency_id', string='Competency Line')
    total_competencies = fields.Integer('Total Competencies', compute='get_total_compentnecy')
    jd_id = fields.Many2one('hr.job.description', string='JD')

    def get_total_compentnecy(self):
        for rec in self:
            rec.total_competencies = 0.0
            for line in rec.line_ids:
                rec.total_competencies += 1

    def unlink(self):
        def get_selection_label(self, object, field_name, field_value):
            return _(dict(self.env[object].fields_get(allfields=[field_name])[field_name]['selection'])[field_value])

        for rec in self:
            for rec_line in rec.line_ids:
                rec_line.unlink()
        return super(HrCompetency, self).unlink()

class HrCompetencyLine(models.Model):
    _name = 'hr.competency.line'
    _description = 'Hr Competency Line'

    master_competency_id = fields.Many2one('master.competency', string='Competency Name')
    active = fields.Boolean('Active', default=True)
    competency_id = fields.Many2one('hr.competency', string='Competency')

class HrLanguage(models.Model):
    _name = 'hr.language'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Hr Language'

    name = fields.Char('Language', required=True)

class HrLanguageLine(models.Model):
    _name = 'hr.language.line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Hr Language Line'

    language_id = fields.Many2one('hr.language', string='Language', required=True)
    speaking = fields.Selection([
        ('basic', 'Basic'),
        ('intermidiate', 'Intermidiate'),
        ('advance', 'Advance')], string='Speaking', required=True)
    listening = fields.Selection([
        ('basic', 'Basic'),
        ('intermidiate', 'Intermidiate'),
        ('advance', 'Advance')], string='Listening', required=True)
    reading = fields.Selection([
        ('basic', 'Basic'),
        ('intermidiate', 'Intermidiate'),
        ('advance', 'Advance')], string='Reading', required=True)
    writing = fields.Selection([
        ('basic', 'Basic'),
        ('intermidiate', 'Intermidiate'),
        ('advance', 'Advance')], string='Writing', required=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)

class HrJobDescripiton(models.Model):
    _name = 'hr.job.description'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Hr Job Description'

    name = fields.Char('Name')
    department_id = fields.Many2one('hr.department', string='Department')
    section_id = fields.Many2one('hr.section', string='Section', required=True)
    position_level_id = fields.Many2one('position.level', string='Position Level', required=True)
    line_ids = fields.One2many('job.description.line', 'jd_id', string='JD Line')
    competency_id = fields.Many2one('hr.competency', string='Competency')

    @api.onchange('position_level_id')
    def onchange_position_level(self):
        competency_obj = self.env['hr.competency']
        com_id = competency_obj.search([('position_level_id', '=', self.position_level_id.id)])
        for pl in com_id:
            self.competency_id = pl.id
            pl.write({'jd_id': self.ids})

class MainJob(models.Model):
    _name = 'main.job'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Main Job'

    name = fields.Char('Main Job')

class JobDescriptionLine(models.Model):
    _name = 'job.description.line'
    _description = 'Job Description Line'

    description = fields.Text('Description', required=True)
    main_job_id = fields.Many2one('main.job', string='Main Job', required=True)
    jd_id = fields.Many2one('hr.job.description', string='JD')

class SirName(models.Model):
    _name = 'sir.name'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Hr Department'

    name = fields.Char('Sir Name', required=True)
    name_mm = fields.Char('Sir Name (Myanmar)', required=True)
    haxid = fields.Char()

class EmployeeCurrentJob(models.Model):
    _name = 'employee.current.job'
    _description = 'Employee Current Job'

    employee_id  = fields.Many2one('hr.employee',string="Employee")
