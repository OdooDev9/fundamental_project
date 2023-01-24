# -*- coding: utf-8 -*-
{
    'name': "Access Right(BU/BR/DIV)",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "UMG Odoo Dept.",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'master_data_extension', 'umg_customize_sale', 'account'],

    # always loaded
    'data': [
        'security/xml/origin_rules_by_bu_br.xml',
        # 'security/xml/origin_rules_by_jr.xml',
        'security/xml/rules.xml',
        'security/ir.model.access.csv',

        # VIEWS
        'views/account_journal_dashboard.xml',
        'views/account_payment_views.xml',
        'views/contact_views.xml',
        # 'views/views.xml',
        # 'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
