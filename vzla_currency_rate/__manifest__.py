# -*- coding: utf-8 -*-
{
    "name": " Venezuela - Currency Rate",
    "version": "1.2",
    'author': 'devs',
    'category': 'Accounting/Accounting',
    "description": """""",
    "website": "",
    'license': 'LGPL-3',
    "depends": ['product', 'account', 'purchase', 'sale',],
    "data": [
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/res_currency_rate_server_views.xml',
        'views/product_template_views.xml',
        'views/product_pricelist_views.xml',
        'views/product_attribute_views.xml',
        # 'views/account_move.xml',
        # 'views/sale_order.xml',
        # 'views/purchase_order.xml',
        #'views/exchange_rate.xml',
    ],
    'license': 'LGPL-3',
    'qweb': [
        'static/src/xml/systray.xml',
    ],
    # 'assets':{
    #     'web.assets_backend': [
    #         'vzla_currency_rate/static/src/js/systray_theme_menu.js'
    #     ],'web.assets_qweb': [
    #         'vzla_currency_rate/static/src/xml/**/*',
    #     ],
    # },
    "installable": True,

}
