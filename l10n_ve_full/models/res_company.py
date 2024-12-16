# -*- coding: UTF-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
import re


class ResCompany(models.Model):
    _inherit = 'res.company'

    rif = fields.Char(string='RIF')
    fax = fields.Char(string="Fax", size=13)
    allow_vat_wh_outdated = fields.Boolean(
        string="Permitir retención de IVA",
        help="Permite confirmar comprobantes de retención para anteriores o futuras "
             " fechas.")
    propagate_invoice_date_to_vat_withholding = fields.Boolean(
        string='Propagar fecha de factura a retención de IVA', default=False,
        help='Propague la fecha de la factura a la retención de IVA. Por defecto está en '
             'Falso.')

    #ISLR
    automatic_income_wh = fields.Boolean(
        'Retención Automática de Ingresos', default=False,
        help='Cuando sea cierto, la retención de ingresos del proveedor se'
             'validara automáticamente')
    propagate_invoice_date_to_income_withholding = fields.Boolean(
        'Propague la fecha de la factura a la retención de ingresos', default=False,
        help='Propague la fecha de la factura a la retención de ingresos. Por defecto es'
             'en falso')

    #ITF
    calculate_wh_itf = fields.Boolean(
        'Retención automática de ITF',
        help='Cuando sea Verdadero, la Retención de la ITF se validará automáticamente', default=False)
    wh_porcentage = fields.Float('Porcentaje ITF', help="El porcentaje a aplicar para retener", default=2)

    account_wh_itf_id = fields.Many2one('account.account', string="Cuenta ITF",
                                        help="Esta cuenta se utilizará en lugar de la predeterminada"
                                             "para generar el asiento del ITF")


    # IGTF Divisa
    aplicar_igtf_divisa = fields.Boolean(
        'Retención de IGTF Divisa',
        help='Cuando sea Verdadero, la Retención de la IGTF Cliente estará disponible en el pago de factura',
        default=False)
    igtf_divisa_porcentage = fields.Float('% IGTF Divisa', help="El porcentaje a aplicar para retener ")

    account_debit_wh_igtf_id = fields.Many2one('account.account', string="Cuenta Recibos IGTF",
                                               help="Esta cuenta se utilizará en lugar de la predeterminada"
                                                    "para generar el asiento del IGTF Divisa")

    account_credit_wh_igtf_id = fields.Many2one('account.account', string="Cuenta Pagos IGTF",
                                                help="Esta cuenta se utilizará en lugar de la predeterminada"
                                                     "para generar el asiento del IGTF Divisa")

    representante_legal = fields.Char(string='Representante Legal')
    representante_cedula = fields.Char(string='Cédula Representante Legal')
    firma_representante = fields.Binary(string='Firma Representante Legal')


    # @api.onchange('calculate_wh_itf')
    # def _onchange_check_itf(self):
    #     for rec in self:
    #         if not rec.calculate_wh_itf:
    #             rec.wh_porcentage = 0
    #             if rec.account_wh_itf_id:
    #                 rec.account_wh_itf_id = False
    #     return

    @api.model_create_multi
    def create(self, vals):
        res = super(ResCompany, self).create(vals)
        for r in res:
            if r.rif:
                if not self.validate_rif_er(r.rif):
                    raise UserError('El rif tiene el formato incorrecto. Ej: V-01234567-8, E-01234567-8, J-01234567-8 o '
                                    'G-01234567-8. Por favor intente de nuevo.')
                if self.validate_rif_duplicate(r.rif, res):
                    raise UserError('El cliente o proveedor ya se encuentra registrado con el rif: %s y se encuentra activo'
                                    % r.rif)
            if r.email:
                if not self.validate_email_addrs(r.email, 'email'):
                    raise UserError('El email es incorrecto. Ej: cuenta@dominio.xxx. Por favor intente de nuevo')
        return res

    def write(self, vals):
        res = super(ResCompany, self).write(vals)
        if vals.get('rif'):
            res_r = self.validate_rif_er(vals.get('rif'))
            if not res_r:
                raise UserError('El rif tiene el formato incorrecto. Ej: V-01234567-8, E-01234567-8, J-01234567-8 o '
                                'G-01234567-8. Por favor intente de nuevo')
            if self.validate_rif_duplicate(vals.get('rif'), False):
                raise UserError('El cliente o proveedor ya se encuentra registrado con el rif: %s y se encuentra activo'
                                % vals.get('rif').upper())

        if vals.get('email'):
            res = self.validate_email_addrs(vals.get('email'), 'email')
            if not res:
                raise UserError('El email es incorrecto. Ej: cuenta@dominio.xxx. Por favor intente de nuevo')
        return res

    @staticmethod
    def validate_rif_er(field_value):
        res = {}
        rif_obj = re.compile(r"[VEJGC]{1}[-]{1}[0-9]{9}[-]{1}[0-9]{1}", re.X)
        rif_obj_2 = re.compile(r"[VEJGC]{1}[-]{1}[0-9]{8}[-]{1}[0-9]{1}", re.X)
        if rif_obj.search(field_value.upper()) or rif_obj_2.search(field_value.upper()):
            res = {
                'rif': field_value
            }
        return res

    def validate_rif_duplicate(self, valor, res):
        if self:
            aux_ids = self.ids
            aux_item = self
        else:
            aux_ids = res.ids
            aux_item = res
        for _ in aux_item:
            company = self.env['res.company'].search([('rif', '=', valor), ('id', 'not in', aux_ids)])
            if company:
                return True
            else:
                return False

    @staticmethod
    def validate_email_addrs(email, field):
        res = {}
        mail_obj = re.compile(r"""
                    \b             # comienzo de delimitador de palabra
                    [\w.%+-]       # usuario: Cualquier caracter alfanumerico mas los signos (.%+-)
                    +@             # seguido de @
                    [\w.-]         # dominio: Cualquier caracter alfanumerico mas los signos (.-)
                    +\.            # seguido de .
                    [a-zA-Z]{2,3}  # dominio de alto nivel: 2 a 6 letras en minúsculas o mayúsculas.
                    \b             # fin de delimitador de palabra
                    """, re.X)  # bandera de compilacion X: habilita la modo verborrágico, el cual permite organizar
        # el patrón de búsqueda de una forma que sea más sencilla de entender y leer.
        if mail_obj.search(email):
            res = {
                field: email
            }
        return res