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
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends':['point_of_sale'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/assets.xml',
        'views/options.xml',
        'views/pos_config.xml',
        'views/wizards.xml',
        'views/views.xml'
    ],
    'qweb': ['static/xml/dialog.xml'],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'active': True,
}
