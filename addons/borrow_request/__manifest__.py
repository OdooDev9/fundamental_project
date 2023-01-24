# -*- coding: utf-8 -*-
{
    'name': "Borrow Request",

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
    'version': '0.2',
    'license': 'LGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'sale_management', 'stock', 'sale_stock', 'master_data_extension'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/hr_security.xml',
        'data/ir_sequence.xml',
        'data/mail_data.xml',
        'wizard/borrow_quotation_wizard.xml',
        'wizard/borrow_req_refuse.xml',
        'wizard/stock_return_picking.xml',
        'views/views.xml',
        'views/templates.xml',
        'views/borrow_request.xml',
        'views/stock_picking_view.xml',
        'views/sale_order_view.xml',

    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
