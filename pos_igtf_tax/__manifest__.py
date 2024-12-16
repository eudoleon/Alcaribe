# -*- coding: utf-8 -*-
{
    'name': 'Venezuela: POS IGTF',
    'version': '16.0.1.0.1',
    'author': 'Easy Solutions Service',
    'company': 'Easy Solutions Service',
    'maintainer': 'Easy Solutions Service',
    'website': '',
    'category': 'Localization',
    'summary': 'IGTF en el POS',
    'depends': ['point_of_sale','pos_show_dual_currency'],
    'data': [
        'views/inherited_views.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            'pos_igtf_tax/static/src/scss/**/*',
            'pos_igtf_tax/static/src/xml/**/*',
            'pos_igtf_tax/static/src/js/**/*',
        ],
    },
    'license': 'LGPL-3',
}
