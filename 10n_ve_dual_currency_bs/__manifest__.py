# -*- coding: utf-8 -*-
###############################################################################
# Author: Jesus Pozzo
# Copyleft: 2023-Present.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
#
#
###############################################################################
{
    'name': "Dual Moneda Base USD to BS",
    'description': """
        *IMPORTANTE : este monudo funciona cuando la moneda base en contabilidad es el USD.
        *Este modulo permite trabajar con la moneda USD  permitien los paunte contable tener un historico en dolares.
        *Cargar automaticamente de acuerdo a la tasa BCV o Dolartoday los precios del producto.
        *Ver los precios en dolares en los pedidos de compras y ventas.
        *Apuntes contables en dolare sy bolivares.
        *Realizar pago y ver reflejado el monto en $$
        *Ve la tasa del dia en las ordenes y facturas .
        *Informe cxc y cxp en dual moneda.
        

    """,

    'author': "Jesús Pozzo",
    'website': "",
    'version': '16.0.1',
    'category': 'Localization',
    'license': 'AGPL-3',
    'depends': ['base','web','account','contacts','product','sale','territorial_pd','l10n_latam_base','account_debit_note','account_payment_group'],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_channel.xml',
        'data/ir_cron.xml',
        'views/account_menu.xml',
        'views/product_template.xml',
        'views/res_currency.xml',
        'views/sale_order.xml',
        'views/account_move.xml',
        'views/purchase_order.xml',
        'wizard/account_payment_register.xml',
        'views/account_payment.xml',
        #REPORTES
        'wizard/account_invoice_report_cxc.xml',
        'wizard/account_invoice_report_cxp.xml',
        'views/report_invoice.xml'

    ],
    'application': True,
    'installable': True,
    'auto_install': False,
    "assets": {
        "web.assets_backend": [
            '10n_ve_dual_currency_bs/static/src/js/widget_multy_currency.js',
            '10n_ve_dual_currency_bs/static/src/xml/widget_test.xml',
        ],
    },

}
