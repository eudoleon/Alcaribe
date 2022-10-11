# -*- coding: utf-8 -*-
{
    'name': "Retención de IGTF Anticipada",

    'summary': """
        Agregar el funcionamiento del impuesto a las grandes transacciones financieras (IGTF) conociendo de antemano el monto a cancelar con moneda extranjera""",

    'description': """
        Desarrollo específico que permite indicar de antemano el monto a cancelar en moneda extranjera para calculo del IGTF. Este módulo agrega dos diarios a la ficha de las compañías, también se linkea a un impuesto de igtf para el area de ventas y otro para compras. Además en el pago crea un asiento de deuda que representa el monto a pagar por IGTF.
    """,

    'author': "Christian Isturiz",
    'website': "https://3mit.dev/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Accounting',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/register_payment_wizard_view.xml',
        'views/views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
