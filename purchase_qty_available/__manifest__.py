# -*- coding: utf-8 -*-
{
    'name': "Purchase Qty On Hand",

    'summary': """
       Show quantity on hand in purchase order line.""",

    'description': """
        Show quantity on hand in purchase order line per selected product.
    """,

    'author': "Stephen Ngailo,StiloTech Limited",
   

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Purchases',
    'version': '15.0.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','purchase','stock'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
     'images': ['static/description/icon.png'],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
