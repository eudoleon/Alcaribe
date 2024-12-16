# -*- coding: utf-8 -*-
import logging
from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AccountMoveLineResumen(models.Model):
    _name = 'account.move.line.resumen'

    invoice_id = fields.Many2one('account.move', ondelete='cascade')
    type=fields.Char()
    state=fields.Char()
    state_voucher_iva=fields.Char()
    total_con_iva = fields.Float(string=' Total con IVA')
    total_base = fields.Float(string='Total Base Imponible')

    base_general = fields.Float(string='Total Base General')
    base_reducida = fields.Float(string='Total Base Reducida')
    base_adicional = fields.Float(string='Total Base General + Reducida')

    total_exento = fields.Float(string='Total Excento')
    alicuota_general = fields.Float(string='Alicuota General')
    alicuota_reducida = fields.Float(string='Alicuota Reducida')
    alicuota_adicional = fields.Float(string='Alicuota General + Reducida')

    retenido_general = fields.Float(string='retenido General')
    retenido_reducida = fields.Float(string='retenido Reducida')
    retenido_adicional = fields.Float(string='retenido General + Reducida')    

    tax_id = fields.Many2one('account.tax', string='Tipo de Impuesto')
    total_valor_iva = fields.Float(string='Total IVA')

    porcentaje_ret = fields.Float(string='Porcentaje de Retencion IVA')
    total_ret_iva = fields.Float(string='Total IVA Retenido')    
    vat_ret_id = fields.Many2one('account.wh.iva', string='Nro de Comprobante IVA')
    nro_comprobante = fields.Char(string='Nro de Comprobante', compute="_nro_comp")
    tipo_doc = fields.Char()
    fecha_fact= fields.Date()
    fecha_comprobante= fields.Date()


    def _nro_comp(self):
        self.nro_comprobante=self.vat_ret_id.name