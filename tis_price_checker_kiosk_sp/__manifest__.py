# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd.
# - © Technaureus Info Solutions Pvt. Ltd 2020. All rights reserved.9

{
    'name': 'Price Checker with Special Price',
    'version': '15.0.0.5',
    'sequence': 1,
    'category': 'product',
    'summary': 'Price Checker Kiosk Mode',
    'author': 'Technaureus Info Solutions Pvt. Ltd.',
    'website': 'http://www.technaureus.com/',
    'price': 149.99,
    'currency': 'EUR',
    'license': 'Other proprietary',
    'description': """
    Price Checker Kiosk Mode
        """,
    'depends': ['product', 'sale_management'],
    'data': [
        'security/security.xml',
        'views/price_checker_kiosk_view.xml',
        'views/res_config_settings_views.xml',
        'views/res_users_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'tis_price_checker_kiosk_sp/static/src/js/price_checker_kiosk.js',
            'tis_price_checker_kiosk_sp/static/src/scss/price_checker.scss',

        #],
        #'web.assets_qweb': [
            'tis_price_checker_kiosk_sp/static/src/xml/**/*',
            'tis_price_checker_kiosk_sp/static/src/scss/**/*',

        ],

    },

    'images': ['images/main_screenshot.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'live_test_url': 'https://www.youtube.com/watch?v=fnSzjRjYyFw&feature=youtu.be'
}
