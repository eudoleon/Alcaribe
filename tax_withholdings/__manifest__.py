# -*- coding: utf-8 -*-
{
    'name': "Retenciones de impuesto",

    'summary': """
         Permite configurar, incluir en facturas de proveedores y 
         generar informes de retenciones de impuestos IVA e ISLR""",

    'description': """
        Permite configurar, generar, imprimir reporte de retencion y 
        exportar la base para entregar al SENIAT de lo correspondiente 
        a las retenciones sobre ISLR e IVA
    """,

    'author': "Techne Studio IT & Consulting",
    'website': "https://technestudioit.com/",

    'license': "OPL-1",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Account',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account', 'purchase'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'report/tax_withholding_reports.xml',
        'report/tax_withholding_templates.xml',
        'data/template_export_data.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
