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
    'name' : 'Catalogos SUNAT',
    'version' : '14.0.2',
    'author' : 'OPeru',
    'category' : 'Accounting & Finance',
    'summary': 'Datos de Tablas para la factura electronica.',
    'license': 'LGPL-3',
    'contributors': [
        'Leonidas Pezo <leonidas@operu.pe>',
    ],
    'description' : """
Factura electronica - Datos Catalogos SUNAT.
====================================

Tablas:
--------------------------------------------
    * Tablas requeridas para los Documentos electronicos Peru

    """,
    'website': 'http://www.operu.pe/contabilidad',
    'depends' : [
        'base',
        'account',
        'l10n_pe',
    ],
    'data': [
        'data/identification_type_data.xml',
        'data/catalog_data.xml',
        'views/catalog_views.xml',
        'security/ir.model.access.csv',   
    ],
    'qweb' : [
    ],
    'demo': [
        #'demo/account_demo.xml',
    ],
    'test': [
        #'test/account_test_users.yml',
    ],
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'auto_install': False,
    "sequence": 1,
    "post_init_hook": "l10n_pe_edi_catalog_init",
    'uninstall_hook': 'l10n_pe_edi_catalog_unistall',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
