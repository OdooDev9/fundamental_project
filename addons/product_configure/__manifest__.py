# -*- coding: utf-8 -*-
{
    'name': "Product Configure",

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
    'depends': ['base','product','master_data_extension'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'security/bu_br_security.xml',
        'views/views.xml',
        'views/templates.xml',
        'views/product_categ_view.xml',
        'views/product_view.xml',
        # 'views/stock_picking_view.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'license': 'LGPL-3',
}
