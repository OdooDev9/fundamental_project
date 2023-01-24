# -*- coding: utf-8 -*-
{
    'name': "Incentive",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "UMG Odoo Dept.",
    'website': "https://safecoms.odoo.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Sale',
    'version': '0.4',
    'license': 'LGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['base', 'sale', 'master_data_extension', 'account','product_configure','umg_customize_sale'],

    # always loaded
    'data': [
        'data/ir_sequence_data.xml',
        'security/ir.model.access.csv',
        'security/security.xml',
        'security/incentive_approval_user.xml',
        'wizard/sale_team_target_approval_wizard_view.xml',
        'wizard/personal_sale_target_approval_wizard_view.xml',
        'wizard/normal_incentive_approval_wizard_view.xml',
        'wizard/normal_incentive_define_wizard.xml',
        'wizard/incentive_paid_view.xml',
        'wizard/pooling_paid_view.xml',
        'wizard/retain_paid_view.xml',
        'wizard/target_area_sale_view.xml',
        'wizard/incentive_request_wizard.xml',
        'views/views.xml',
        'views/normal_incentive_view.xml',
        'wizard/area_incentive_wizard_view.xml',
        'views/templates.xml',
        'views/sale_order_type_view.xml',
        'views/incentive_calculation_rule.xml',
        'views/incentive_quaterly_bonus_view.xml',
        'views/area_incentive_view.xml',
        'views/incentive_request.xml',
       
        

    ],

    
    'installable':True,
    'auto_install':False,
    'application':True,
}
