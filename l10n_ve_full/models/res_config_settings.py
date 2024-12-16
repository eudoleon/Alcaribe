# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    #IVA
    allow_vat_wh_outdated = fields.Boolean(
        string="Retención Automática de IVA", related="company_id.allow_vat_wh_outdated", readonly=False)

    # ISLR
    automatic_income_wh = fields.Boolean(
        'Retención Automática de Ingresos', related="company_id.automatic_income_wh", readonly=False)

    calculate_wh_itf = fields.Boolean('Retención automática de ITF', related="company_id.calculate_wh_itf", readonly=False)

    wh_porcentage = fields.Float('% ITF', help="El porcentaje a aplicar para retener", related="company_id.wh_porcentage", readonly=False)

    account_wh_itf_id = fields.Many2one('account.account', string="Cuenta ITF", related="company_id.account_wh_itf_id",
                                        help="Esta cuenta se utilizará en lugar de la predeterminada"
                                             "para generar el asiento del ITF", readonly=False)

    # IGTF Divisa
    aplicar_igtf_divisa = fields.Boolean(
        'Retención de IGTF Divisa',
        help='Cuando sea Verdadero, la Retención de la IGTF Cliente estará disponible en el pago de factura',
        related="company_id.aplicar_igtf_divisa", readonly=False)
    igtf_divisa_porcentage = fields.Float('% IGTF Divisa', help="El porcentaje a aplicar para retener ", related="company_id.igtf_divisa_porcentage", readonly=False)

    account_debit_wh_igtf_id = fields.Many2one('account.account', string="Cuenta Recibos IGTF",
                                               help="Esta cuenta se utilizará en lugar de la predeterminada"
                                                    "para generar el asiento del IGTF Divisa", related="company_id.account_debit_wh_igtf_id", readonly=False)

    account_credit_wh_igtf_id = fields.Many2one('account.account', string="Cuenta Pagos IGTF",
                                                help="Esta cuenta se utilizará en lugar de la predeterminada"
                                                     "para generar el asiento del IGTF Divisa", related="company_id.account_credit_wh_igtf_id", readonly=False)

    #representante
    representante_legal = fields.Char('Representante Legal', related="company_id.representante_legal", readonly=False)
    representante_cedula = fields.Char('Cédula', related="company_id.representante_cedula", readonly=False)
    firma_representante = fields.Binary('Firma Representante', related="company_id.firma_representante", readonly=False)

