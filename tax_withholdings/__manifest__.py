# -*- coding: utf-8 -*-
{
    'name': "Tax withholdings",

    'summary': """
        Allows you to configure, include in vendor invoices and 
        generate reports of VAT and ISLR tax withholdings""",

    'description': """
        Allows configuring, generating, printing withholding reports 
        and exporting the basis for submitting to SENIAT the 
        corresponding ISLR and VAT withholdings
    """,

    'author': "Techne Studio IT & Consulting",
    'website': "https://technestudioit.com/",

    'license': "OPL-1",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Accounting',
    'version': '2.3',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account', 'purchase'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'report/tax_withholding_reports.xml',
        'report/tax_withholding_templates.xml',
        'data/template_export_data.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
