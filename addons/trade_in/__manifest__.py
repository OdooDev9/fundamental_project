# -*- coding: utf-8 -*-
{
    'name': "Trade In",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "UMG Odoo Dept.",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','master_data_extension','stock','job_request','product_configure'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/trade_in_security.xml',
        'data/trade_in.xml',
        'data/trade_in_location_data.xml',
        'wizard/cancel_reason_wizard.xml',
        'views/views.xml',
        'views/templates.xml',
        'views/stock_location_view.xml',
        'views/trade_in_view.xml',
       
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'license': 'LGPL-3',
}
