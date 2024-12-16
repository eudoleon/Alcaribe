# -*- coding: utf-8 -*-
{
    'name': 'Venezuela: POS fiscal printer',
    'version': '16.0.1.0.1',
    'category': 'Localization',
    'summary': 'Fiscal printing using serial ports',
    'author': 'Easy Solution Services',
    'company': 'Easy Solution Services',
    'maintainer': 'Easy Solution Services',
    'website': '',
    'description': 'Impresoras modelos SRP812, DT230, HKA80, PP9, PP9-PLUS, PD3100DL, TD1140.',
    'depends': ['point_of_sale', 'pos_igtf_tax'],
    'data': [
        'security/ir.model.access.csv',
        'views/inherited_views.xml',
        'views/x_pos_fiscal_printer_views.xml',
        'views/pos_report_z.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            'pos_fiscal_printer/static/src/scss/**/*',
            'pos_fiscal_printer/static/src/js/AbstractReceiptScreen.js',
            'pos_fiscal_printer/static/src/js/PartnerDetailsEdit.js',
            'pos_fiscal_printer/static/src/js/NotaCreditoPopUp.js',
            'pos_fiscal_printer/static/src/js/PrintingMixin.js',
            'pos_fiscal_printer/static/src/js/ReporteZPopUp.js',
            'pos_fiscal_printer/static/src/js/ReprintingPopUp.js',
            'pos_fiscal_printer/static/src/xml/**/*',
            'pos_fiscal_printer/static/lib/js/**/*',
            'pos_fiscal_printer/static/lib/css/**/*',
        ],
        # 'web.assets_backend': [
        #     'pos_fiscal_printer/static/src/js/GetZBackends.js',
        # ],
    },
    'license': 'LGPL-3',
}
