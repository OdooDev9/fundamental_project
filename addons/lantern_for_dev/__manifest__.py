# -*- coding: utf-8 -*-
{
    'name': "Lantern For DEVs",

    'summary': """
    
        ***This modules is intended to support developer*** 
    """,

    'description': """
        ***This modules is intended to support developer*** 
    """,

    'author': "TRIO",
    'website': "",

    'category': 'Technical',
    'version': '0.1',
    'sequence': 1,
    # any module necessary for this one to work correctly
    'depends': ['base', 'web', 'web_enterprise'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
