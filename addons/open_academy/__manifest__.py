{
    'name' : 'Open Academy',
    'version' : '0.1',
    'author' : 'UMG odoo dev',
    'license' : 'LGPL-3',
    'description' : """This module provides academic classes""",
    'category': 'Fundamental Project',
    'depand' : ['base'],
    'data' : [
        'security/ir.model.access.csv',
        'views/course.xml',
        'views/session.xml'
    ],
    'demo': [
        # 'demo/demo.xml',
    ],
    'installable':True
    
}