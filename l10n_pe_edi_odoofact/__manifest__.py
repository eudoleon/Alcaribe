# -*- coding: utf-8 -*-
###############################################################################
#
#    Copyright (C) 2019-TODAY OPeru.
#    Author      :  Grupo Odoo S.A.C. (<http://www.operu.pe>)
#
#    This program is copyright property of the author mentioned above.
#    You can`t redistribute it and/or modify it.
#
###############################################################################

{
    'name': 'Factura Electronica - Peru',
    'version': '14.0.10',
    'author': 'OPeru',
    'category': 'Accounting',
    'summary': 'Factura electronica Peru con PSE/OSE Nubefact',
    'description': '''
    EDI Peruvian Localization
    Allow the user to generate the EDI document for Peruvian invoicing with PSE/OSE Nubefact.
    ''',
    'depends': [
        'account',
        'sale',
        'base',
        'web',
        'uom',
        'account_debit_note',
        'l10n_pe', 
        'l10n_latam_base', 
        'l10n_latam_invoice_document',
        'l10n_pe_edi_catalog'
    ],
    'data': [
        'wizard/account_move_reversal_view.xml',
        'wizard/account_debit_note_view.xml',
        'wizard/l10n_pe_edi_move_cancel_view.xml',
        'views/l10n_pe_edi_picking_number_view.xml',
        'views/res_company_views.xml',
        'views/account_views.xml',
        'views/account_tax_views.xml',
        'views/account_move_views.xml',
        'views/product_views.xml',
        'views/edi_request_view.xml',
        'views/edi_shop_views.xml',
        'views/report_menu_view.xml',
        'views/uom_uom_views.xml',
        'views/catalog_views.xml',
        'report/report_assets.xml',
        'data/l10n_latam_identification_type_data.xml',
        'data/account_tax_data.xml',
        'data/currency_data.xml',
        'data/ir_cron_data.xml',
        'data/l10n_pe_edi_data.xml',
        'data/mail_template_data.xml',
        'data/uom_data.xml',
        'template/send_invoice_report_email_template.xml',
        'views/res_config_settings_views.xml',
        'views/report_invoice.xml',
        'security/ir.model.access.csv',        
    ],
    'installable': True,
    'images': ['static/description/banner.png'],
    'live_test_url': 'http://www.operu.pe/manuales',
    'license': 'OPL-1',
    'support': 'modulos@operu.pe',
    'sequence': 1,
    'post_init_hook': '_l10n_pe_edi_odoofact_init',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
