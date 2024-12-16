# -*- coding: utf-8 -*-
{
    'name': "3mit_print_server",

    'summary': """
        Interface con Servicio de Impresora Fiscal""",

    'description': """
        tickets y Opciones de Impresora Fiscal
    """,

    'author': "3mit",
    'website': "http://www.3mit.dev",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Sales/Point Of Sale',
    'version': '16.3.2.3',

    # any module necessary for this one to work correctly
    'depends':['point_of_sale'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/options.xml',
        'views/pos_config.xml',
        'views/wizards.xml',
        'views/views.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            "3mit_print_server/static/src/js/dialog.js",
            "3mit_print_server/static/src/js/print_nc.js",
            "3mit_print_server/static/src/js/print_factura.js",
            "3mit_print_server/static/src/js/print_options.js",
        ],
        'point_of_sale.assets': [
            '3mit_print_server/static/src/js/print_ticket.js',
            '3mit_print_server/static/src/js/discount_button.js',
            '3mit_print_server/static/xml/dialog.xml',
            '3mit_print_server/static/xml/pos.xml',
        ],
    },
    'controllers': [
        'controllers/controllers.py'
    ],
    'installable': True,
    'active': True,
    "license": "AGPL-3",
}
