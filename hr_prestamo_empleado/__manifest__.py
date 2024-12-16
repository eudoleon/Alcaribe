# -*- coding: utf-8 -*-
{
    'name': "Prestamo a empleados",

    'summary': """Prestamo a empleados""",

    'description': """
       Prestamo a empleados.
    """,
    'version': '15.0',
    'author': 'd',
    'category': 'Tools',

    # any module necessary for this one to work correctly
    'depends': ['hr','hr_payroll'],
    'data': [
    'views/prestamo_view.xml',
    'security/ir.model.access.csv',
    ],
    'application': True,
    'active':False,
    'auto_install': False,
}
