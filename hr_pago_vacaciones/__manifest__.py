# -*- coding: utf-8 -*-
{
    'name': "Pago de Vacaciones por modulo de ausencias",

    'summary': """Pago de Vacaciones por modulo de ausencias""",

    'description': """
       Pago de Vacaciones por modulo de ausencias.
    """,
    'version': '13.0',
    'author': 'd',
    'category': 'Tools',

    # any module necessary for this one to work correctly
    'depends': ['base','account','hr_holidays','hr_campos_parametrizacion'],

    # always loaded
    'data': [
        'vista/hr_leave_inherit_view.xml',
        'vista/wizard.xml',
        'vista/hr_leave_type_inherit_view.xml',
        'security/ir.model.access.csv',
    ],
    'application': True,
    'active':False,
    'auto_install': False,
}
