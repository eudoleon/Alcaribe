# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
{
    "name": "Product Multiple Barcode Scanner - Enterprise Edition",
    "author": "Softhealer Technologies",
    "website": "http://www.softhealer.com",
    "support": "support@softhealer.com",
    "category": "Productivity",
    "license": "OPL-1",
    "summary": "Multiple Barcode For Products Multiple QRCode Product Multi Barcode Product Multi QRCode Multi Bar Code Multiple Bar Code Multiple QR Code Multi QR Code Product Barcodes Search Product By Barcode Search Product By QRcode Odoo",
    "description": """Mainly the use of this module, you can assign multiple Barcode/QRCode for each product. Also, you can search that product in inventory operations like the delivery order, incoming order (receipt ), inventory adjustment, internal transfer & return order.""",
    "version": "0.0.1",
    'depends': [
        'sh_product_multi_barcode',
        'stock_barcode',
    ],
    "data": [
        "views/product_template_views.xml",
        "views/product_product_views.xml",
    ],
    'images': ['static/description/background.png'],
    "installable": True,
    "auto_install": False,
    "application": True,
    "price": "130",
    "currency": "EUR"
}
