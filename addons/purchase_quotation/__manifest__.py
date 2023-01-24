# -*- coding: utf-8 -*-
{
    'name': "Purchase Order Extend",

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
    'version': '1.1.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'sale', 'purchase', 'master_data_extension','purchase_customize'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/purchase_order_view.xml',
        'views/purchase_quotation_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [

    ],
    'license': 'LGPL-3',

}
