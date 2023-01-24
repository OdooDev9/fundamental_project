# -*- coding: utf-8 -*-
{
    'name': "Job Request",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "UMG Odoo Dept.",
    'website': "http://www.safecoms.co.th",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'product', 'stock', 'sales_team', 'account', 'purchase', 'mrp','master_data_extension', 'delivery', 'request_quotation', 'purchase_quotation','product_configure','umg_customize_sale','sale','stock_account'],

    #always loaded
    'data': [
        'security/job_request_security.xml',
        'security/ir.model.access.csv',

        'wizard/delivery_cost.xml',
        'wizard/job_request_wizard.xml',
        'wizard/part_order_multi_invoice.xml',
        'wizard/job_request_invoice.xml',
        'wizard/sale_replace_wizard_view.xml',
        'wizard/part_replace_wizard_view.xml',

        'data/ir_sequence_data.xml',
        'data/mail_template.xml',
        'data/part_sequence.xml',

        # 'views/account_invoice_report_view.xml',
        'views/job_request_view.xml',
        'views/part_product_view.xml',
        # 'views/part_report.xml',
        # 'views/part_report_templates.xml',
        # 'views/job_order_report.xml',
        'views/part_setting_view.xml',
        'views/part_view.xml',
        'views/html_checklist_template.xml',
        'views/part_menu_view.xml',
        'views/product_view.xml',
        # 'views/crm_lead.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'installable':True,
    'auto_install':False,
    'application':True,
    'license': 'LGPL-3',
}
