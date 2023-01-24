# -*- coding: utf-8 -*-
{
    'name': "UMG Customization",

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
    'version': '0.3',
    'license': 'LGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['base','sale','sale_management','account','master_data_extension','stock','product','contacts','product_configure','account_extension'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/bu_br_security.xml',
        'security/sale_secuirty_rules.xml',
        'security/customer_security.xml',
        'data/ir_sequence.xml',
        'wizard/broker_fees_wizard_view.xml',
        'views/views.xml',
        'views/templates.xml',
        'views/broker_fees_view.xml',
        'views/sale_order_view.xml',
        'views/account_move.xml',
        'views/account_payment_view.xml',
        'views/add_brand.xml',
        'views/commission_view.xml',
        'views/product_pricelist_view.xml',
        'views/res_partner_view.xml',
        'views/brand_model_views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
