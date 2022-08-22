# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

{
    'name': "Product App",
    'version': '14.0.1.0',
    'category': 'Sales/Sales',
    'summary': 'Product App.This module provide seperate menu in main of product.Product Menu|Product|Main Menu Product|Menu Product.',
    'description': """Product App
    This module provides seprate product app.""",
    'author': "Kanak Infosystems LLP.",
    'website': 'https://www.kanakinfosystems.com',
    'images': ['static/description/banner.gif'],
    'depends': ['product'],
    'license': 'OPL-1',
    'data': [
        'views/product_template_view.xml',
        'views/res_config_settings_views.xml'
    ],
    'sequence': 1,
    'installable': True,
    'application': False,
    'auto_install': False,
}
