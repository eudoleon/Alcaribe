# -*- coding: utf-8 -*-
{
    'name': "Alertas de stock en ventas",

    'summary': """
        Manejo de alertas por inventario agotado""",

    'description': """
        Envío de email para notificar que se ha agotado el stock de un producto al momento de la venta
    """,

    'author': "Toh Soluciones Digitales",
    'website': "http://www.tohsoluciones.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Sales',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': ['sale_management', 'stock'],

    # always loaded
    'data': [
        'views/res_config_settings_views.xml',
        'data/email_stock_alert.xml',
    ],
    'images': ["static/description/miniatura_video.png"],
    'license': "AGPL-3",
}
