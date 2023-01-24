# -*- coding: utf-8 -*-
{
    'name': "Request for Quotations",

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
    'depends': ['base','sale','sale_management','master_data_extension','sale_stock','product_configure','umg_customize_sale'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/hr_security.xml',
        'data/ir_sequest.xml',
        'views/views.xml',
        'views/templates.xml',
        'views/sale_order_view.xml',
        'views/request_quotation_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'license': 'LGPL-3',

}
