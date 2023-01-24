# -*- coding: utf-8 -*-
{
    'name': "All Report Templates",
    'summary': """
        All report templates""",
    'description': """
        Templates for Sales,Purchase,Invoice and Inventory
    """,
    'author': "UMG",
    'website': "your company",
    'category': 'Report',
    'version': '0.1.1',
    'depends': [
        'sale',
        'purchase',
        'request_quotation',
        'web',
        'report_qweb_element_page_visibility',
    ],
    'data': [
        'report/report.xml',
        'report/sale_order_part_report.xml',
        'report/purchase_report.xml',
        'report/sale_invoice_part.xml',
        'report/sale_quotation.xml',
    ],
    'images': [
        'description/images.png',
    ],
    'license': 'LGPL-3',
}
