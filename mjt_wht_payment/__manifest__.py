# -*- coding: utf-8 -*-
{
    'name': "Payment WHT",

    'summary': """
        Extend Payment usage""",

    'description': """
        Extend Payment usage
    """,

    'author': "MJT",
    'license':'AGPL-3',
    'website': "http://www.metrocomjaddi.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Accounting',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['account'],

    # always loaded
    'data': [
        # 'data/ir_sequence.xml',
        'security/ir.model.access.csv',
        'views/account_payment_view.xml',
        'views/bukti_potong_view.xml',
    ],
}
