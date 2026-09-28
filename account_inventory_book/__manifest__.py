# -*- coding: utf-8 -*-
{
    'name': "Libro de Inventario",
    'summary': "Libro de Inventario (Entradas y Salidas Valoradas)",
    'description': """
        Módulo para la emisión del Libro de Inventario según la normativa legal (Artículo 177).
        Permite filtrar por fechas, productos o categorías y generar reportes en formato PDF y XLSX.
    """,
    'author': "Devs",
    'category': "Accounting/Reporting",
    'version': "16.0.1.0.1",
    'license': "LGPL-3",
    'depends': [
        'base',
        'account',
        'stock',
        'stock_account',
        'product',
    ],
    'data': [
        'security/ir.model.access.csv',
        'report/account_inventory_book_report.xml',
        'wizard/account_inventory_book.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
