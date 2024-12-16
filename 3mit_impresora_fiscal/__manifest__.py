# coding: utf-8
###########################################################################

##############################################################################
{
    "name": "Modificaciones para impresora fiscal",
    'version': '16.0.0.0',
    "author": "3mit",
    "license": "AGPL-3",
    "category": "ventas",
    #"website": "",
    "colaborador":"Ing Yorman Pineda",
    'depends': [ 'point_of_sale', 'account'],

    'demo': [
    ],
    "data": [
        'security/ir.model.access.csv',
        'views/reemprimir.xml',
    ],
    'test': [

    ],
    "installable": True,
    'application': True,

}
