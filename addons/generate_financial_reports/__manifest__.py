# -*- coding: utf-8 -*-
{
    'name': "Generate Financial Reports",

    'summary': """
        Intend To Generate Financial Reports
        - Profit and Loss
        - Balance Sheet
        - Executive Summary
        """,

    'description': """
    """,

    'author': "UMG Odoo Dept.",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'web_enterprise', 'account_reports', 'account_accountant', 'master_data_extension'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'security/financial_reports_rules.xml',
        'views/views.xml',
        'views/templates.xml',
        # 'data/account_financial_report_data.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
