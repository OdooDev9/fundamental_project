# -*- coding: utf-8 -*-
#################################################################################
# Author      : Kanak Infosystems LLP. (<http://kanakinfosystems.com/>)
# Copyright(c): 2012-Present Kanak Infosystems LLP.
# All Rights Reserved.
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <http://kanakinfosystems.com/license>
#################################################################################
{
    'name': 'Payment Installments',
    'version': '2.1',
    'category': 'Invoicing Management',
    'summary': 'An app which helps to make payments in installments',
    'description': """
This module provides to make payments in installments
=====================================================


    """,

    'author': "UMG Odoo Dept.",
    'website': 'http://www.umgroups.com',
    'license': 'LGPL-3',
    'depends': ['sale_management', 'account', 'master_data_extension', 'sale','umg_customize_sale','account_extension','sale_incentive','job_request'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'security/ir_sequence.xml',
        'data/data.xml',
        'wizard/create_part_payment.xml',
        'wizard/account_payment_register.xml',
        'wizard/modify_installment_view.xml',
        'wizard/installment_invoice_view.xml',
        'wizard/recontract_wizard_view.xml',
        'views/payment_installment_view.xml',
        'views/res_config_settings_views.xml',
        'views/account_payment_view.xml',
        'views/installment_plan_view.xml',
        'views/reinstallment_view.xml',
        'views/request_quotation.xml',
        'wizard/quotation_modify_installment.xml'
    ],
    'images': ['static/description/banner.jpg'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
