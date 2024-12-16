# -*- coding: utf-8 -*-
{
    'name': "Accounting Report Enhancement",
    'version': '16.0.4.0.0',
    'summary': "Accounting Report Enhancement",
    'description': "Accounting Report Enhancement",
    'category': 'Accounting/Report',
    'website': "",
    'depends': ['account_reports'],
    'data': [
        'data/aged_partner_balance.xml',
        'data/third_party_general_ledger.xml',
        'data/third_party_trial_balance.xml',
        'data/account_withholding_assistant.xml',
        'views/account_report_view.xml',
    ],
    'license': "LGPL-3",
    'installable': True,
    'application': True,
}
