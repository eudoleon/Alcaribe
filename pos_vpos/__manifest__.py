# -*- coding: utf-8 -*-
{
    'name': "POS VPOS",
    'version': '0.1.1',
    'category': 'Sales/Point of Sale',
    'summary': 'Integración de POS con terminal VPOS',
    'description': '',
    # 'license':'proprietary',
    'author': 'gPyME',
    'website': '',

    'sequence': 6,
    # any module necessary for this one to work correctly
    'depends': ['point_of_sale'],
    'instalable': True,
    'assets': {
        'point_of_sale.assets': [
            'pos_vpos/static/src/js/models.js',
            'pos_vpos/static/src/js/payment.js',
            'pos_vpos/static/src/js/paymentScreen.js',
            'pos_vpos/static/src/xml/*.xml',
        ],
        'web.assets_backend': [
            #'pos_vpos/static/src/js/actions.js',
            'pos_vpos/static/src/js/pos_config_kanban_dropdown.js',
        ]},

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        # 'views/assets.xml',
        'views/pos_config.xml',
        'views/res_config_settings_views.xml',
        'views/pos_payment_method_views.xml',
        'views/point_of_sale_dashboard.xml'

    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],

}
