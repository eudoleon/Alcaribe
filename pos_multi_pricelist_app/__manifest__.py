# -*- coding: utf-8 -*-
{
    'name': 'Allow Multi Currencies Pricelist in POS',
    "author": "Edge Technologies",
    'version': '16.0.1.2',
    'live_test_url': "https://youtu.be/YoVeJpDWzw0",
    "images": ['static/description/main_screenshot.png'],
    'summary': "POS multi pricelist pos multi currency pricelist multi currency pricelist on pos different currency pricelist point of sale multi pricelist point of sale multi currency price-list multi currency pricelist on pos pricelist pos multi currencies pricelist.",
    'description': """Using this module you can use multi currencies pricelist in pos.
allow multi currency pricelist in point of sale
when a user applies price-list for the point of sale, then it may have different currency on different pricelist, but by default odoo only support pos pricelist for single currency on point of sale session. that's why when people have different currency on different price-list they cannot apply it in pos session/configuration. we provide a solution with this app which helps user to use multiple price-list with different in point of sale and when the relevant price list is applied on pos screen currency conversation are automatically done based on accounting currency rate and. when user select the different currency's pricelist then order amount and all products price is effected based on exchange rate of the currency
pos multi pricelist pos multi currency price-list multi currency pricelist on pos multiple currency pricelist on pos
point of sale multi pricelist point of sale multi currency price-list multi currency pricelist on point of sale multiple currency pricelist on point of sale pos pricelist pos price-list point of sale pricelist point of sale price-list on point of sale pricelist on point of sale pricelist on pos price-list on pos price list on point of sale price list on pos
pos currency pricelist pos pricelist currency pos product pricelist pos product currency
point of sale currency pricelist point of sale pricelist currency point of sale product pricelist point of sale product currency.




""",
    "license": "OPL-1",
    'depends': ['base', 'point_of_sale'],
    'data': [
        'views/pos_payment.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            'pos_multi_pricelist_app/static/src/js/multi_pricelist.js',
            'pos_multi_pricelist_app/static/src/js/Screens/SetPricelistButtonInherit.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'price': 28,
    'currency': "EUR",
    'category': 'Point of Sale',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
