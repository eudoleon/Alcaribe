# -*- coding: utf-8 -*-
{
    'name': "Reporte Pre nomina",

    'summary': """Reporte Pre nomina""",

    'description': """
       Reporte Pre nomina.
    """,
    'version': '15.0',
    'author': 'd',
    'category': 'Tools',
    'depends': ['base','account','hr_campos_parametrizacion'],

    # always loaded
    'data': [
        'report/reporte_view.xml',
        'report/reporte_view_resu.xml',
        'report/reporte_view_cta_analyt.xml',
        'wizard/wizard.xml',
        'security/ir.model.access.csv',
    ],
    'application': True,
    'active':False,
    'auto_install': False,
}
