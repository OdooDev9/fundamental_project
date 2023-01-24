# -*- coding: utf-8 -*-
{
    'name': "HR Employee Information",

    'summary': """
        Employee Information Customize Module""",

    'description': """
        New attributes for employee profile
    """,

    'author': "UMG Odoo Dept",
    'website': "http://www.yourcompany.com",

    'category': 'HR',
    'version': '0.1.0',

    # any module necessary for this one to work correctly
    'depends': ['base','hr','master_data_extension'],

    # always loaded
    'data': [
        # 'data/employee_sequence.xml',
        'security/ir.model.access.csv',
        'views/hr_employee_views.xml',
        'views/hr_employee_changed_device.xml',
        'views/employee_master_data_views.xml',
        'views/master_data_menus.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'license': 'LGPL-3',
}
