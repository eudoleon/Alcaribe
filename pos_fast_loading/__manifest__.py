# -*- coding: utf-8 -*-
#################################################################################
# Author      : Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# Copyright(c): 2015-Present Webkul Software Pvt. Ltd.
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://store.webkul.com/license.html/>
#################################################################################
{
    "name":  "POS Fast Loading",
    "summary":  """This module is used to load the data fast into pos. It can load more than 1 Lac products and 50k customers in just few seconds.Fast Data Loading|Load Data Faster|Faster Loading Data|Speed Up Loading|POS Data Load.""",
    "category":  "Point Of Sale",
    "version":  "1.0.2",
    "sequence":  1,
    "author":  "Webkul Software Pvt. Ltd.",
    "license":  "Other proprietary",
  
    "website":  "https://store.webkul.com/Odoo-POS-Fast-Loading.html",
    "description":  """fast load, fast load data, data fast into pos, data faster loading, fast loading""",
    "live_test_url":  "http://odoodemo.webkul.com/?module=pos_fast_loading&custom_url=/pos/auto",
    "depends":  ['pos_sale_product_configurator'],
    "data":  [
        'security/ir.model.access.csv',
        'views/pos_fast_loading_view.xml',
        'data/cron.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            "/pos_fast_loading/static/src/js/models.js",
            "/pos_fast_loading/static/src/js/chrome.js",
            'pos_fast_loading/static/src/xml/**/*',
        ],
    },
    "images":  ['static/description/banner.gif'],
    "application":  True,
    "installable":  True,
    "auto_install":  False,
    "price":  249,
    "currency":  "USD",
    "pre_init_hook":  "pre_init_check",
}
