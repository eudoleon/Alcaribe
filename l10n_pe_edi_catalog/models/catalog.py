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
from odoo.osv import expression

class CatalogTmpl(models.Model):
    _name = 'l10n_pe_edi.catalog.tmpl'
    _description = 'Catalog Template'

    active = fields.Boolean(string='Active', default=True)
    code = fields.Char(string='Code', size=4, index=True, required=True)
    name = fields.Char(string='Description', index=True, required=True)

    def name_get(self):
        result = []
        for table in self:
            result.append((table.id, "%s %s" % (table.code, table.name or '')))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        if operator == 'ilike' and not (name or '').strip():
            domain = []
        else:
            domain = ['|', ('name', 'ilike', name), ('code', 'ilike', name)]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

class Catalog03(models.Model):
    _name = "l10n_pe_edi.catalog.03"
    _description = 'Codigos - Tipo de Unidad de Medida Comercial'
    _inherit = 'l10n_pe_edi.catalog.tmpl'

    code = fields.Char(string='Code', size=8, required=True)

class Catalog06(models.Model):
    _name = "l10n_pe_edi.catalog.06"
    _description = 'Tipo de documento de Identidad'
    _inherit = 'l10n_pe_edi.catalog.tmpl'

    default = fields.Char(string='Default value', size=128)
        
class Catalog07(models.Model):
    _name = "l10n_pe_edi.catalog.07"
    _description = 'Codigos de Tipo de Afectacion del IGV'
    _inherit = 'l10n_pe_edi.catalog.tmpl'

    no_onerosa = fields.Boolean(string='No onerosa')
    type = fields.Selection([
        ('taxed','Taxed'),
        ('exonerated','Exonerated'),
        ('unaffected','Unaffected'),
        ('exportation','Exportation')],string='Type')
    code_of = fields.Char(string="Code by Odoo Fact")
    
class Catalog08(models.Model):
    _name = "l10n_pe_edi.catalog.08"
    _description = 'Codigos de Tipo de Afectacion del IGV'
    _inherit = 'l10n_pe_edi.catalog.tmpl'

class Catalog09(models.Model):
    _name = "l10n_pe_edi.catalog.09"
    _description = 'Codigos de Tipo de Nota de Credito Electronica'
    _inherit = 'l10n_pe_edi.catalog.tmpl'

class Catalog10(models.Model):
    _name = "l10n_pe_edi.catalog.10"
    _description = 'Codigos de Tipo de Nota de Debito Electronica'
    _inherit = 'l10n_pe_edi.catalog.tmpl'

class Catalog11(models.Model):
    _name = "l10n_pe_edi.catalog.11"
    _description = 'Codigo de Tipo de Valor de Venta'
    _inherit = 'l10n_pe_edi.catalog.tmpl'

class Catalog12(models.Model):
    _name = "l10n_pe_edi.catalog.12"
    _description = 'Codigos -Documentos Relacionados Tributarios'
    _inherit = 'l10n_pe_edi.catalog.tmpl'

class Catalog14(models.Model):
    _name = "l10n_pe_edi.catalog.14"
    _description = 'Codigos - Otros Conceptos Tributarios'
    _inherit = 'l10n_pe_edi.catalog.tmpl'

class Catalog15(models.Model):
    _name = "l10n_pe_edi.catalog.15"
    _description = 'Codigos-Elementos Adicionales en la Factura Electrónica '
    _inherit = 'l10n_pe_edi.catalog.tmpl'

    name = fields.Char(string='Value', size=256, index=True, required=True)

class Catalog16(models.Model):
    _name = "l10n_pe_edi.catalog.16"
    _description = 'Codigos - Tipo de Precio de Venta Unitario'
    _inherit = 'l10n_pe_edi.catalog.tmpl'

class Catalog17(models.Model):
    _name = "l10n_pe_edi.catalog.17"
    _description = 'Codigos -Tipo de Operacion'
    _inherit = 'l10n_pe_edi.catalog.tmpl'

class Catalog18(models.Model):
    _name = "l10n_pe_edi.catalog.18"
    _description = 'Codigos - Modalidad de  Traslado'
    _inherit = 'l10n_pe_edi.catalog.tmpl'

class Catalog19(models.Model):
    _name = "l10n_pe_edi.catalog.19"
    _description = 'Codigos de Estado de Item'
    _inherit = 'l10n_pe_edi.catalog.tmpl'

class Catalog20(models.Model):
    _name = "l10n_pe_edi.catalog.20"
    _description = 'Codigos - Motivo de Traslado'
    _inherit = 'l10n_pe_edi.catalog.tmpl'

class Catalog21(models.Model):
    _name = "l10n_pe_edi.catalog.21"
    _description = 'Codigos-Documentos Relacionados '
    _inherit = 'l10n_pe_edi.catalog.tmpl'

class Catalog22(models.Model):
    _name = "l10n_pe_edi.catalog.22"
    _description = 'Codigos- Regimenes de Percepcion'
    _inherit = 'l10n_pe_edi.catalog.tmpl'

    rate = fields.Char(string='Tasa', size=10, index=True, required=True)

class Catalog23(models.Model):
    _name = "l10n_pe_edi.catalog.23"
    _description = 'Codigos- Regimenes de Retencion'
    _inherit = 'l10n_pe_edi.catalog.tmpl'

    rate = fields.Float(string='Rate', default=0.0)

class Catalog24(models.Model):
    _name = "l10n_pe_edi.catalog.24"
    _description = 'Codigos- Recibo Electronico por Servicios Publicos'
    _inherit = 'l10n_pe_edi.catalog.tmpl'

    name = fields.Char(string='Service', size=128, index=True, required=True)
    rate_code = fields.Char(string='Rate code', size=4, index=True, required=True)
    
class Catalog25(models.Model):
    _name = "l10n_pe_edi.catalog.25"
    _description = 'Codigos - Producto SUNAT'
    _inherit = 'l10n_pe_edi.catalog.tmpl'

    code = fields.Char(string='Code', size=8, required=True)

class Catalog26(models.Model):
    _name = "l10n_pe_edi.catalog.26"
    _description = 'Códigos - Tipo de préstamo (créditos hipotecarios)'
    _inherit = 'l10n_pe_edi.catalog.tmpl'

    code = fields.Char(string='Code', size=8, required=True)

class Catalog27(models.Model):
    _name = "l10n_pe_edi.catalog.27"
    _description = 'Codigos - Indicador de primera vivienda'
    _inherit = 'l10n_pe_edi.catalog.tmpl'

    code = fields.Char(string='Code', size=8, required=True)

class Catalog51(models.Model):
    _name = "l10n_pe_edi.catalog.51"
    _description = 'Codigo de  Tipo de Factura'
    _inherit = 'l10n_pe_edi.catalog.tmpl'

    code = fields.Char(string='Code', size=12, index=True, required=True)

class Catalog52(models.Model):
    _name = "l10n_pe_edi.catalog.52"
    _description = 'Codigos de Leyendas'
    _inherit = 'l10n_pe_edi.catalog.tmpl'

    code = fields.Char(string='Code', size=12, index=True, required=True)

class Catalog53(models.Model):
    _name = "l10n_pe_edi.catalog.53"
    _description = 'Codigos de Cargos o Descuentos'
    _inherit = 'l10n_pe_edi.catalog.tmpl'

    code = fields.Char(string='Code', size=12, index=True, required=True)

class Catalog54(models.Model):
    _name = "l10n_pe_edi.catalog.54"
    _description = 'Codigos de Bienes y Servicio Sujetos a Detraccion'
    _inherit = 'l10n_pe_edi.catalog.tmpl'

    code = fields.Char(string='Code', size=12, index=True, required=True)
    code_of = fields.Char(string="Code by Odoo Fact")
    rate = fields.Float(string='Rate', default=0.0)

    def name_get(self):
        result = []
        for table in self:
            result.append((table.id, "%s %s (%s %%)" % (table.code, table.name or '', table.rate and str(table.rate) or '')))
        return result

class Catalog55(models.Model):
    _name = "l10n_pe_edi.catalog.55"
    _description = 'Codigo de identificacion del Item'
    _inherit = 'l10n_pe_edi.catalog.tmpl'

    code = fields.Char(string='Code', size=12, index=True, required=True)

class Catalog56(models.Model):
    _name = "l10n_pe_edi.catalog.56"
    _description = 'Codigo de Tipo de Servicio Publico'
    _inherit = 'l10n_pe_edi.catalog.tmpl'

    code = fields.Char(string='Code', size=12, index=True, required=True)

class Catalog57(models.Model):
    _name = "l10n_pe_edi.catalog.57"
    _description = 'Codigo de Tipo de Servicio Publicos-Telecomunicaciones'
    _inherit = 'l10n_pe_edi.catalog.tmpl'

    code = fields.Char(string='Code', size=12, index=True, required=True)
    
class Catalog58(models.Model):
    _name = "l10n_pe_edi.catalog.58"
    _description = 'Codigo de Tipo de Medidor-Recibo de Luz'
    _inherit = 'l10n_pe_edi.catalog.tmpl'

    code = fields.Char(string='Code', size=12, index=True, required=True)

class Catalog59(models.Model):
    _name = "l10n_pe_edi.catalog.59"
    _description = 'Códigos - Medios de Pago'
    _inherit = 'l10n_pe_edi.catalog.tmpl'

    code = fields.Char(string='Code', size=12, index=True, required=True)
    code_of = fields.Char(string="Code by Odoo Fact")

class Catalog60(models.Model):
    _name = "l10n_pe_edi.catalog.60"
    _description = 'Códigos -  Tipo de dirección'
    _inherit = 'l10n_pe_edi.catalog.tmpl'

    code = fields.Char(string='Code', size=12, index=True, required=True)