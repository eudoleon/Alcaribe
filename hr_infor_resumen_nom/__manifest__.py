# -*- coding: utf-8 -*-
{
    'name': "Reporte resumen nomina",

    'summary': """Reporte resumen nomina""",

    'description': """
       Reporte resumen nomina.
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
        #'vista/hr_inherit_payslip_run_view.xml',
        #'vista/hr_payslip_employee_inherit.xml',
    ],
    'application': True,
    'active':False,
    'auto_install': False,
}
