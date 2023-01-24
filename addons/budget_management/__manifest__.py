# -*- coding: utf-8 -*-
{
    'name': "Budget Requisition",

    'summary': """
        Budget Requisition for BR/BU/DIV""",

    'description': """
        Long description of module's purpose
    """,

    'author': "UMG Odoo Dept.",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '1.0.0',
    'license': 'LGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['base', 'master_data_extension', 'account','hr','product_configure'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/bu_br_security.xml',
        'data/ir_sequence.xml',
        'wizard/advance_wizard_view.xml',
        'wizard/expense_wizard_view.xml',
        'wizard/weekly_approval_view.xml',
        'wizard/urgent_approve_view.xml',
        'wizard/reject_wizard_views.xml',
        'views/advance_view.xml',
        'views/expense_view.xml',
        'views/monthly_budget_view.xml',
        'views/weekly_budget_view.xml',
        'views/configuration_view.xml',
        'views/urgent_budget_view.xml',
        'views/menu_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
}
