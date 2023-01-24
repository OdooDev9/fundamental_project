# -*- coding: utf-8 -*-
{
    'name': "landed_costs",

    'summary': """
        To Be Able to create landed cost bills""",

    'description': """
        Easy to use and able to create bill from landed costs
    """,

    'author': "UMG Odoo Dept.",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'purchase',
    'version': '0.0.1',

    # any module necessary for this one to work correctly
    'depends': ['stock_landed_costs', 'account'],

    # always loaded
    'data': [
        'security/security.xml',
        'views/landed_cost_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
