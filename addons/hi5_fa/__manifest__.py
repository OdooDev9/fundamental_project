{
    'name' : 'Hi5 AR',
    'version' : '0.1',
    
    'license' : 'LGPL-3',
    'description' : """AR_Assign""",

    'depends' : [
        'base','master_data_extension','hr','payment_installment_kanak','generate_financial_reports'
    ],
    'data' : [
        'security/ir.model.access.csv',
        'views/ar_assign_view.xml',
        'views/ar_configuration_view.xml',
        'views/legal_activity.xml',
        'views/ar_repossess_view.xml'
        # 'views/template.xml'
    ],
    # 'assets':{
    #     'web.assets_backend':[
    #         '/home/eisan/user/src/default/project/addons/hi5_fa/static/src/css/style.css'
    #         ]

    # }
    
}