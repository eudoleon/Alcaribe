{
    'name': '[Original] POS User Access',
    'version': '16.0.1.0',
    'summary': """User Access to Closing POS, Order Deletion, Order Line Deletion,
                  Discount Application, Order Payment, Price Change and Decreasing Quantity,
Odoo POS validation, Odoo POS validate, Odoo POS confirmation, Odoo POS confirm,
Odoo POS checking, Odoo POS check, Odoo POS access, Odoo POS user, user access, access right,
delete order, delete order line, POS closing, closing POS, decrease quantity""",
    'description': """
POS User Access
===============

This module allows restrictions on some features in POS UI if the cashier has no access rights

Per Point of Sale, you can define access/restriction for the following features:
* POS Closing
* Order Deletion
* Order Line Deletion
* Discount Application
* Order Payment
* Price Change
* Decresing Quantity


Compatibility
-------------

This module is compatible and tested with these modules:
* Restaurant module (pos_restaurant)
""",
    'category': 'Sales/Point of Sale',
    'author': 'MAC5',
    'contributors': ['MAC5'],
    'website': 'https://apps.odoo.com/apps/modules/browse?author=MAC5',
    'depends': [
        'point_of_sale',
    ],
    'data': [
        'views/res_users_views.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            'pos_user_access_mac5/static/src/js/**/*',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'images': ['static/description/banner.gif'],
    'price': 49.99,
    'currency': 'EUR',
    'support': 'mac5_odoo@outlook.com',
    'license': 'OPL-1',
    'live_test_url': 'https://youtu.be/MYYPt25GcDw',
}
