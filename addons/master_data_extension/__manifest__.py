# -*- coding: utf-8 -*-
{
    'name': "Business Unit Structure Master Data",

    'summary': """
        To import the Master Data""",

    'description': """
        Long description of module's purpose
    """,

    'author': "UMG Odoo Dept.",
    'website': "",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '1.0.0',
    'license': 'LGPL-3',
    

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'stock', 'account_accountant', 'web_group_expand'],

    # always loaded
    'data': [
        # SECURITY
       
        'security/bu_security.xml',
        'security/br_security.xml',
        'security/div_security.xml',
        'security/ir_rules.xml',
        'security/ir.model.access.csv',
        # INVENTORY
        'views/stock_warehouse.xml',
        'views/stock_location.xml',
        # ADDRESS CONFIGURATION
        'views/config/hr_country.xml',
        'views/config/hr_region.xml',
        'views/config/hr_district.xml',
        'views/config/hr_city.xml',
        'views/config/hr_township.xml',
        'views/config/industry_zone.xml',
        'views/config/building_floor.xml',
        'views/config/business_sector_type.xml',
        'views/res_partner.xml',

        # MENU & SETTING
        'views/master_menu.xml',
        # res 
        'views/res_users.xml',
        'views/res_company.xml',

        'views/setting/res_config_settings.xml',
        # ACCOUNTING
        'views/accounting/account_journal.xml',
        'views/accounting/accounting_views.xml',
        'views/accounting/account_account_type.xml',
        # BUSINESS UNIT
        'views/business_unit.xml',
        'views/setting/ir_module_upgrade.xml',
        
        # DATA create
        'data/business_unit.xml',
    ],
    # only loaded in demonstration mode
    # 'demo': [
    #     'demo/demo.xml',
    # ],
}
