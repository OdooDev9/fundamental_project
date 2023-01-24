# -*- coding: utf-8 -*-
{
    'name': "Stock Journal On GI & GR",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "UMG Odoo Dept.",
    'website': "https://www.safecoms.odoo.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['stock','product','stock_account','account','master_data_extension','product_configure'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/bu_br_security.xml',
        'wizard/lot_serial_transfer_wizard.xml',
        'views/views.xml',
        'views/templates.xml',
        #'views/account_move.xml',
        'views/stock_quant_view.xml',
        # 'views/stock_return_picking_view.xml',
        
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
