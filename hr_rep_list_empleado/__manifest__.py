# -*- coding: utf-8 -*-
{
    'name': "Reporte Listado Empleados",

    'summary': """Generar Reporte Listado Empleados.""",

    'description': """
       Generar Reporte Listado Empleados.
    """,
    'version': '15.0',
    'author': 'd',
    'category': 'Tools',

    # any module necessary for this one to work correctly
    'depends': ['base','account','hr_campos_parametrizacion'],

    # always loaded
    'data': [
        'report/reporte_view.xml',
        'wizard/wizard.xml',
        'security/ir.model.access.csv',
    ],
    'application': True,
    'active':False,
    'auto_install': False,
}
