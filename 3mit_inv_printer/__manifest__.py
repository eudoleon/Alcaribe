# -*- coding: utf-8 -*-
{
    'name': "Impresora Fiscal - Backend",

    'summary': """
        Emite factura a rest-api de impresora fiscal""",

    'description': """
        V.1.0.0 - Impresora fiscal sin localizacion:
                    - Facturas de ventas.
        
    """,

    'author': "3Mit",
    'website': "http://www.yourcompany.com",

    # Categories can be used t filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['account','10n_ve_dual_currency_bs'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/nota_credito.xml',
        # 'views/options.xml'
    ],
    'assets': {
            "3mit_inv_printer/static/src/js/print_nc.js",
            # "3mit_inv_printer/static/src/js/print_options.js",
            "3mit_inv_printer/static/src/js/printer.js",  
    },
    # only loaded in demonstration mode
    'demo': [
    ],
}
