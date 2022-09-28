# -*- coding: utf-8 -*-
###############################################################################
#
#    Copyright (C) 2019-TODAY OPeru.
#    Author      :  Grupo Odoo S.A.C. (<http://www.operu.pe>)
#
#    This program is copyright property of the author mentioned above.
#    You can`t redistribute it and/or modify it.
#
###############################################################################

from odoo import models, fields, api

class L10nLatamDocumentType(models.Model):
    _inherit = 'l10n_latam.document.type'

    type_of = fields.Selection([('1','FACTURA'),('2','BOLETA'),('3','NOTA DE CREDITO'),('4','NOTA DE DEBITO')],
                    string='Type of document', 
                    help='Used by Odoo Fact. \n'\
                            '1 = FACTURA \n'\
                            '2 = BOLETA \n'\
                            '3 = NOTA DE CRÉDITO \n'\
                            '4 = NOTA DE DÉBITO \n')    
