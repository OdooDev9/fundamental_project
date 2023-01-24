# -*- coding: utf-8 -*-
{
    'name': "Accounting (BU/BR)",

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
    'version': '1.0.0',
    'license': 'LGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['account', 'sale','purchase','master_data_extension'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        # 'security/security.xml',
        # 'security/origin_rules.xml',
        'views/account_payment_view.xml',
        'views/account_move_view.xml',
        'views/wizard/payment_transfer_views.xml',
        'views/partner_ledger_view.xml',
        # 'views/account_type_view.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
}
