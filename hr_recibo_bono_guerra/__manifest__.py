# -*- coding: utf-8 -*-
{
    'name': "Reporte Pre nomina",

    'summary': """Recibo de Bono de Guerra.""",

    'description': """
       Recibo de Bono de Guerra.
    """,
    'version': '15.0',
    'author': 'INM & LDR Soluciones Tecnológicas y Empresariales C.A - Ing. Darrell Sojo',
    'category': 'Tools',
    'website': 'http://soluciones-tecno.com',

    # any module necessary for this one to work correctly
    'depends': ['base','account','hr_campos_parametrizacion'],

    # always loaded
    'data': [
        'report/recibo_pago_bono_guerra.xml',
        #'wizard/wizard.xml',
        #'security/ir.model.access.csv',
    ],
    'application': True,
    'active':False,
    'auto_install': False,
}
