# -*- coding: utf-8 -*-
{
    'name': "UMG Purchase Customization",

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
    'license': 'LGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['base','purchase','purchase_stock','mail','master_data_extension','product_configure','account','stock','stock_journal_on_picking','umg_customize_sale'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'security/purchase_approval.xml',
        'data/mail_data.xml',
        'wizard/purchase_reject_wizard.xml',
        'wizard/purchase_holding_wizard.xml',
        'views/views.xml',
        'views/templates.xml',
        'views/purchase_view.xml',
        'views/account_move.xml',
        'views/account_payment.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
