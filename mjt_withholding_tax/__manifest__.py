# -*- coding: utf-8 -*-
{
    'name': "Account Withholding Tax",

    'summary': """
        Extend Account Invoice usage""",

    'description': """
        Extend Account Invoice usage  
    """,

    'author': "MJT",
    'license':'AGPL-3',
    'website': "http://www.metrocomjaddi.com",
    'category': 'Accounting',
    'version': '0.1',
    'images': [
        'static/description/banner.jpg',
    ],

    'depends': ['base', 'account', 'mjt_wht_payment'],

    # always loaded
    'data': [
        # 'data/ir_sequence.xml',
        'security/ir.model.access.csv',
        'views/account_tax_view.xml',
        'views/account_move_view.xml',
        'wizard/account_payment_register_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}