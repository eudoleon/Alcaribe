# coding: utf-8
from email.policy import default

from odoo import fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    appl_type = fields.Selection(string='Tipo de Alicuota', required=False,
                                 selection=[('exento', 'Exento'), ('sdcf', 'No tiene derecho a crédito fiscal'),
                                            ('general', 'Alicuota General'), ('reducido', 'Alicuota Reducida'),
                                            ('adicional', 'Alicuota General + Adicional')],
                                 help='Especifique el tipo de alícuota para el impuesto para que pueda procesarse '
                                      'según el libro de compra / venta generado')

    wh_vat_collected_account_id = fields.Many2one(
        'account.account',
        string="Cuenta de retención de IVA de factura",
        help="Esta cuenta se utilizará al aplicar una retención a una Factura")

    wh_vat_paid_account_id = fields.Many2one(
        'account.account',
        string="Cuenta de Devolucion de la retención de IVA",
        help="Esta cuenta se utilizará al aplicar una retención a un Reembolso")

    type_tax = fields.Selection([('iva', 'IVA'),
                                 ('municipal', 'Municipal')], required=True, help="Selecione el Tipo de Impuesto",
                                string="Tipo de Impuesto")

    tax_id = fields.Many2one('account.tax', string='Tax', required=False, ondelete='set null',
                             help="Tax relation to original tax, to be able to take off all data from invoices.")

