# coding: utf-8
from odoo import fields, models

class IslrWhConcept(models.Model):
    _name = 'account.wh.islr.concept'
    _description = 'Concepto de retención de ingresos'

    name= fields.Char(
            'Concepto de retención', required=True,
            help="Nombre del concepto de retención, ejemplo: Honorarios "
                 "Profesionales, Comisiones a ...")
    codigo = fields.Char(string="Código")
    withholdable= fields.Boolean(
            string=' A Retener', default=True,
            help="Compruebe si la retención del concepto se retiene o no ")
    # property_retencion_islr_payable= fields.Many2one(
    #         'account.account',
    #         string="Cuenta de Compra para la Retención de Ingresos",
    #         company_dependet=True,
    #         required=False,
    #         help="Esta cuenta se usará como la cuenta donde se retuvo"
    #              "los importes se cargarán en su totalidad (Compra) del impuesto sobre la renta"
    #              "por este concepto")
    # property_retencion_islr_receivable= fields.Many2one(
    #         'account.account',
    #         string="Cuenta de Venta para la Retención de Ingresos",
    #         company_dependet=True,
    #         required=False,
    #         help="Esta cuenta se usará como la cuenta donde se retuvo"
    #              "los importes se cargarán en (Venta) del impuesto sobre la renta")
    rate_ids= fields.One2many(
            'account.wh.islr.rates', 'concept_id', 'Tasas',
            help="Tasa de concepto de retención", required=False)

    user_id = fields.Many2one('res.users', 'Responsible', default=lambda self: self.env.user)
