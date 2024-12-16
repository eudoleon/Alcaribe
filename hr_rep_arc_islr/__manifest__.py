# -*- coding: utf-8 -*-
{
    'name': "Reporte Pre nomina",

    'summary': """Generar los Comprobantes de Retención de Impuestos sobre la Renta, por Concepto de Sueldos y Salarios.""",

    'description': """
       Generar los Comprobantes de Retención de Impuestos sobre la Renta, por Concepto de Sueldos y Salarios.
    """,
    'version': '15.0',
    'author': 'd',
    'category': 'Tools',

    # any module necessary for this one to work correctly
    'depends': ['base','account','hr_campos_parametrizacion'],

    # always loaded
    'data': [
        #'report/reporte_view.xml',
        #'report/reporte_view_resu.xml',
        'report/reporte_view.xml',
        'wizard/wizard.xml',
        'security/ir.model.access.csv',
    ],
    'application': True,
    'active':False,
    'auto_install': False,
}
