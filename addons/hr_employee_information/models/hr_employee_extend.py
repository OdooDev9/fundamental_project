# -*- coding: utf-8 -*-
from re import T
from odoo import models, fields, api
from datetime import timedelta, datetime
import logging
_logger = logging.getLogger(__name__)
from odoo.exceptions import ValidationError
from odoo.tools.translate import _
import calendar


class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    _description = 'Hr Employee Information'

    # name = fields.Char(compute="compute_employee_name")
    sir_id = fields.Many2one('sir.name', string='Sir Name', required=True)
    first_name = fields.Char('First Name', required=True)
    last_name = fields.Char('Last Name')
    sir_mm_id = fields.Char(related="sir_id.name_mm", string='Sir Name')
    first_name_mm = fields.Char('First Name', required=False)
    last_name_mm = fields.Char('Last Name')
    burmese_name = fields.Char('Burmese Name')

    # Address Start
    no = fields.Char('Number')
    street = fields.Char('Street')
    quarter = fields.Char('Quarter')
    township_id = fields.Many2one('hr.township', string='Township')
    city_id = fields.Many2one('hr.city', string='City')
    region_id = fields.Many2one('hr.region', string='Region')
    country_id = fields.Many2one('hr.country', string='Country')
    user_id = fields.Many2one(comodel_name='res.users', string="Related User", ondelete='cascade')
    # Address End

    # Address MM Start
    nomm = fields.Char('နံပါတ်')
    streetmm = fields.Char('လမ်း')
    quartermm = fields.Char('ရပ်ကွပ်')
    townshipmm = fields.Char(string='မြို့နယ်')
    citymm = fields.Char(string='မြို့တော်')
    regionmm = fields.Char(string='နေရာဒေသ')
    countrymm = fields.Char(string='နိုင်ငံ')
    # Address MM End

    # Permanant add Start
    permm_no = fields.Char('နံပါတ်')
    permm_street = fields.Char('လမ်း')
    permm_quarter = fields.Char('ရပ်ကွပ်')
    permm_township = fields.Char(string='မြို့နယ်')
    permm_city = fields.Char(string='မြို့တော်')
    permm_region = fields.Char(string='နေရာဒေသ')
    permm_country = fields.Char(string='နိုင်ငံ')
    # Permanant add End

    # Permanant MM Start
    per_no = fields.Char('Number')
    per_street = fields.Char('Street')
    per_quarter = fields.Char('Quarter')
    per_township_id = fields.Many2one('hr.township', string='Township')
    per_city_id = fields.Many2one('hr.city', string='City')
    per_region_id = fields.Many2one('hr.region', string='Region')
    per_country_id = fields.Many2one('hr.country', string='Country')
    # Permanant MM End

    real_dob = fields.Date('Real Date of Birth', tracking=True)
    nationality = fields.Selection([
        ('citizen', 'Citizen'),
        ('non_citizen', 'Non Citizen')], default='citizen', string='Nationality', required=True)
    nrc_no = fields.Many2one('nrc.no', string="NRC No")
    nrc_desc = fields.Many2one('nrc.description', string="NRC Description", domain="[('nrc_no_id','=',nrc_no)]")
    nrc_type = fields.Many2one('nrc.type', string="NRC Type")
    nrc_number = fields.Char('NRC Number')
    nrc_no_mm = fields.Char(related="nrc_no.nrc_no_mm", string="NRC နံပါတ်")
    nrc_desc_mm = fields.Char(related="nrc_desc.nrc_desc_mm", string="NRC မြို့နယ်")
    nrc_type_mm = fields.Char(related="nrc_type.nrc_type_mm", string="NRC ပုံစံ")
    nrc_number_mm = fields.Char(string='မှတ်ပုံတင်နံပါတ်')
    religion_id = fields.Many2one('hr.religion', string='Religion', tracking=True)
    race_id = fields.Many2one('hr.race', string='Race', tracking=True)
    blood_id = fields.Many2one('hr.blood.type', string='Blood Type', tracking=True)
    current_address_mm = fields.Text(string='လက်ရှိနေရပ်လိပ်စာ', tracking=True)
    parmenant_address_mm = fields.Text(string='အမြဲတမ်းနေရပ်လိပ်စာ', tracking=True)
    home_phone = fields.Char('Home Phone Number')
    driving_license = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No')], string='Have Driving License?', default='no', required=True)
    license_type = fields.Selection([
        ('black_b', 'Black B(ခ)'),
        ('black_c', 'Black C(ဂ)'),
        ('brown', 'Brown(ဃ)'),
        ('Red', 'Red(င)')], string='Choose License Type')
    license_no = fields.Char('Driving License Number')
    expire_license = fields.Date('License Expire')
    emp_id = fields.Char('Employee ID')
    old_id = fields.Char('Old Employee ID')
    password = fields.Char('Hi5 Password')
    disc_type = fields.Char('DISC Type')
    has_spouse = fields.Boolean('Spouse')
    has_father = fields.Boolean('Father')
    has_mother = fields.Boolean('Mother')
    relation_id = fields.Many2one('hr.family.relation', string='Relation')
    education_ids = fields.One2many('hr.education', 'employee_id', string='Education')
    family_ids = fields.One2many('hr.family', 'employee_id', string='Family')
    exp_ids = fields.One2many('hr.experience', 'employee_id', string='Working Experience')
    other_ids = fields.One2many('hr.other.qualification', 'employee_id', string='Other Quali')
    bank_ids = fields.One2many('hr.bank', 'employee_id', string='Bank')
    rank_id = fields.Many2one('hr.rank', string='Rank')
    trial_date_start = fields.Date(string='Joining Date')
    probation_period = fields.Integer('Probation Period')
    trial_date_end = fields.Date(string='Confirmation Date', compute='_compute_trial_date_end', store=True, copy=True)
    extend_date = fields.Date(string='Extend Date')
    age = fields.Integer('Age', compute="calculate_age")
    emp_active = fields.Boolean('Active Employee', default=True)
    state = fields.Selection([
        ('probation', 'Probation'),
        ('confirm', 'Confirmation'),
        ('promo', 'Confirm with Promo'),
        ('demo', 'Confirm with Demo'),
        ('increment', 'Increment'),
        ('extend', 'Extend'),
        ('reject', 'Reject')], string='Status', default='probation')
    employment_type = fields.Selection([
        ('regular', 'Regular'),
        ('part_time','Part Time'),
        ('permanent','Permanent'),
        ('daily', 'Daily Wages'),
        ('expatriate', 'Expatriate'),
        ('oversea', 'Oversea'),
        ('program', 'Program'),
        ('contract', 'Contract')], string='Employment Type',required=True)
    job_ids = fields.One2many('hr.job', 'employee_id', string='Concurrent Jobs')
    position_level_id = fields.Many2one('position.level', string='Position Level')
    company_id = fields.Many2one('res.company', string='Company')
    is_hold = fields.Boolean('Is Holding', default=False)
    job_function_id = fields.Many2one('job.function', string='Job Function')
    employee_status = fields.Selection([
        ('probation', 'Probation'),
        ('permanent', 'Permanent'),
        ('contract', 'Contract')], string='Employee Status')
    wage_type = fields.Selection([
        ('daily', 'Daily Salary'),
        ('hourly', 'Hourly Wages Salary'),
        ('monthly', 'Monthly Salary Structure')], string='Wage Type')
    report_id = fields.Many2one('hr.employee', string='Report To Person')
    is_shift = fields.Boolean('Work Shift Person', default=False)
    personal_email = fields.Char('Personal Mail')
    ssnid = fields.Char('SSB Number')
    has_internship = fields.Boolean('Internship')
    service_year = fields.Integer('Service', compute="calculate_service")
    service_month = fields.Integer('Month', compute="calculate_service")
    service_day = fields.Integer('Day', compute="calculate_service")
    jd_id = fields.Many2one('hr.job.description', string='Job Description')
    employer_no = fields.Char(related='company_id.vat', string='Employer Number')
    company_ids = fields.One2many('res.company', 'employee_id', string='Company')
    personal_phone = fields.Char('Phone')
    faceid = fields.Boolean('Face ID')
    haxid = fields.Char()

    old_name = fields.Char(string='Old Name')
    program_id = fields.Many2one('candidate.program', string='Program Name')
    batch_no = fields.Char(string='Batch No')
    allow_login = fields.Boolean(string='Allow Login')
    marital = fields.Selection(selection_add=[
        ('single', 'Single'),
        ('married', 'Married'),
        ('cohabitant', 'Legal Cohabitant'),
        ('widower', 'Widower'),
        ('divorced', 'Divorced'),
        ('other', 'Other')
    ], string='Marital Status', groups="hr.group_hr_user", default='single', tracking=True)
    passport_expire = fields.Date(string='Passport Expire')
    addr_current_eng = fields.Char(string='Current Address')
    addr_current_mm = fields.Char(string='လက်ရှိနေရပ်လိပ်စာ')
    addr_parmenant_eng = fields.Char(string='Parmenant Address')
    addr_parmenant_mm = fields.Char(string='အမြဲတမ်းနေရပ်လိပ်စာ')
    emp_rank = fields.Char(string='Rank')
    location_id = fields.Many2one('hr.location', store=True)
    tax_number = fields.Char()

    country_phone = fields.Many2one('hr.country', string='Country')
    country_code = fields.Char(related='country_phone.country_code')
    phone_no = fields.Char()

    language_ids = fields.One2many('hr.language.line', 'employee_id', string='Language')

    station_id = fields.Many2one('hr.station',string='Station')
    holding_id = fields.Many2one('business.unit',string='Holding Business')
    sub_id = fields.Many2one('business.unit',string='Sub Business')
    section_id = fields.Many2one('hr.section',string='Section')
    current_job_id = fields.One2many('employee.current.job','employee_id',string="Concurrent Jobs")
    
    #Nrc number to MM font
    @api.onchange('nrc_number')
    def _nrc_number_on_change(self):
        if self.nrc_number:
            numbers = {
                '1': '၁', '2': '၂',
                '3': '၃', '4': '၄',
                '5': '၅', '6': '၆',
                '7': '၇', '8': '၈',
                '9': '၉', '0': '၀'
            }
            tempo = ""
            for number in self.nrc_number:
                if number != ' ':
                    try:
                        tempo += numbers.get(number)
                    except Exception as e:
                        print(e)
                        raise ValidationError(_("NRC Number should not be Letter."))
            self.nrc_number_mm = tempo

    #Check digit count of Phone number
    @api.constrains('work_phone')
    def phone_validate(self):
        # Employee Phone limit validate
        if self.work_phone and (len(self.work_phone) > self.country_phone.limit or len(self.work_phone) < 6):
            raise ValidationError(_('Phone Limit Error'))

    #check employee is in BU/BR/DIV     
    @api.onchange('holding_id')
    def onchange_bu(self):
        self.is_hold = True

    #Compute Probation date end(or) Confirmation with Joined Date 
    @api.depends('trial_date_start')
    def _compute_trial_date_end(self):
        for rec in self:
            if rec.trial_date_start:
                trial_date_start = datetime.strptime(str(rec.trial_date_start), "%Y-%m-%d")
                if rec.probation_period > 0:
                    day = (rec.probation_period * 30) + 2
                    rec.trial_date_end = trial_date_start + timedelta(days=day)
                else:
                    rec.trial_date_end = trial_date_start + timedelta(days=92)
            else:
                rec.trial_date_end = False

    #Calculate Employee Age
    @api.depends('birthday')
    def calculate_age(self):
        for rec in self:
            if rec.birthday:
                birth = datetime.strptime(str(rec.birthday), "%Y-%m-%d")
                today = datetime.strptime(str(fields.Date.today()), "%Y-%m-%d")
                age = abs((today - birth).days)
                # print (age)
                year = round(float(age / 365.00), 2)
                rec.age = int(year)
            else:
                rec.age = 0

    #Compute Employee Service Year based on Joined Date
    @api.depends('trial_date_start')
    def calculate_service(self):
        for rec in self:
            if rec.trial_date_start:
                month = 0
                years = 0
                day = 0
                join_date = str(rec.trial_date_start)
                p_year = datetime.strptime(join_date, '%Y-%m-%d').strftime('%Y')
                p_month = datetime.strptime(join_date, '%Y-%m-%d').strftime('%m')
                p_day = datetime.strptime(join_date, '%Y-%m-%d').strftime('%d')
                # # datetime.strptime(join_date, '%Y-%m-%d').strftime('%m')
                today_year = datetime.today().strftime("%Y")
                today_month = datetime.today().strftime("%m")
                today_day = datetime.today().strftime("%d")
                years = int(today_year) - int(p_year)
                r = calendar.monthrange(int(today_year), int(today_month))[1]
                if today_month < p_month:
                    years -= 1
                    month = (int(today_month) + 12) - int(p_month)
                else:
                    month = int(today_month) - int(p_month)
                if today_day < p_day:
                    month -= 1
                    day = (int(today_day) + r) - int(p_day)
                else:
                    day = int(today_day) - int(p_day)
                service_day = day
                service_month = month
                service_year = years
                rec.service_year = int(service_year)
                rec.service_month = int(service_month)
                rec.service_day = int(service_day)
            else:
                rec.service_year = 0
                rec.service_month = 0
                rec.service_day = 0

    # def unlink(self):
    #     res = super(HrEmployee, self).unlink()
    #     if self.user_id:
    #         self.env['res.users'].search([('id', '=', self.user_id.id)]).unlink()
    #     return res

    #Extend Create Method
    @api.model
    def create(self, vals):
        if not vals.get('last_name'):
            vals['last_name'] = " "
        first_name = vals.get('first_name')
        last_name = vals.get('last_name')

        #Add Employee Name
        vals['name'] = str(first_name) + ' ' + str(last_name)

        #Generate Employee ID based on Employment Type
        if vals.get('employment_type') == 'regular':
            vals['emp_id'] = self.env['ir.sequence'].next_by_code('employee.regular')
        elif vals.get('employment_type') == 'daily':
            vals['emp_id'] = self.env['ir.sequence'].next_by_code('employee.daily.wadge')
        elif vals.get('employment_type') == 'expatriate':
            vals['emp_id'] = self.env['ir.sequence'].next_by_code('employee.expatriate')
        elif vals.get('employment_type') == 'oversea':
            vals['emp_id'] = self.env['ir.sequence'].next_by_code('employee.oversea')
        elif vals.get('employment_type') == 'program':
            vals['emp_id'] = self.env['ir.sequence'].next_by_code('employee.program')
        elif vals.get('employment_type') == 'contract':
            vals['emp_id'] = self.env['ir.sequence'].next_by_code('employee.contract')

        #Auto Generate User for Employee
        # user_name = vals['first_name'] + ' ' + vals['last_name']
        # user_demo = self.env['res.users'].create({
        #     'name': user_name,
        #     'email': vals['work_email'],
        #     'image_1920': False,
        #     'login': vals['emp_id'],
        #     'password': vals['password']
        # })

        # #Add user to Employee
        # vals['user_id'] = user_demo.id
        
        result = super(HrEmployee, self).create(vals)
        return result

    def write(self, vals):
        if 'address_home_id' in vals:
            account_id = vals.get('bank_account_id') or self.bank_account_id.id
            if account_id:
                self.env['res.partner.bank'].browse(account_id).partner_id = vals['address_home_id']
        if vals.get('user_id'):
            vals.update(self._sync_user(self.env['res.users'].browse(vals['user_id'])))
        sirname = self.sir_id.name
        res = super(HrEmployee, self).write(vals)
        if vals.get('department_id') or vals.get('user_id'):
            department_id = vals['department_id'] if vals.get('department_id') else self[:1].department_id.id
            self.env['mail.channel'].sudo().search([
                ('subscription_department_ids', 'in', department_id)
            ])._subscribe_users_automatically()

        return res

    def name_get(self):
        result = []
        for rec in self:
            sirname = rec.sir_id.name or ''
            first_name = rec.first_name or ''
            last_name = rec.last_name or ''
            name = str(sirname) + ' ' + str(first_name) + ' ' + str(last_name)
            result.append((rec.id, name))
        return result

    # @api.depends('sir_id','first_name','last_name')
    # def compute_employee_name(self):
    #     print("compute_employee_name.........is in..........")
    #     for rec in self:
    #         sirname = rec.sir_id.name or ''
    #         first_name = rec.first_name or ''
    #         last_name = rec.last_name or ''
    #         name = str(sirname) + ' ' + str(first_name) + ' ' + str(last_name)
    #         rec.name = name
