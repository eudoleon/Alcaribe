# -*- coding: utf-8 -*-
{
    # App information
    'name': 'Reporte de excel',
    'version': '1.0',
    'category': 'Stock',
    'summary': 'Using this App, one can Print Tax Report in Excel in Odoo.',
    'license': 'OPL-1',
     
    # Dependencies
    'depends': ['account'],
    
    # Views
    'data': [
        'views/account_tax_menu.xml'
        ],
        
    # Odoo Store Specific
    'images': ['static/description/Text-Report-in-Excel-Store-Cover.jpg'],  
    
        
    'installable': True,
    'auto_install': False,
    'application':True,
    'sequence':1,
}
