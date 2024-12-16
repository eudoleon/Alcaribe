# coding: utf-8

from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    type = fields.Selection([('sale', 'Ventas'), ('sale_refund', 'Reembolso de venta'), ('purchase', 'Compras'),
                            ('purchase_refund', 'Reembolso de compra'), ('cash', 'Efectivo'), ('bank', 'Banco'),
                            ('general', 'Varios'), ('situation', 'Situacion de Apertura/Cierre'),
                            ('sale_debit', 'Débito de venta'), ('purchase_debit', 'Débito de compra')], string='Tipo',
                            size=32, required=True,
                            help="Seleccione 'Venta' para los diarios de facturas de clientes. "
                                 "Seleccione 'Compra' para los diarios de facturas de proveedores."
                                 "Seleccione 'Efectivo' o 'Banco' para los diarios que se utilizan en"
                                 "pagos de clientes o proveedores."
                                 " Seleccione 'General' para diarios de operaciones diversas."
                                 " Seleccione 'Situación de apertura / cierre' para las entradas generadas "
                                 " para nuevos años fiscales."
                                 " Seleccione 'Débito de venta' para los diarios de notas de débito del cliente."
                                 " Seleccione 'Débito de compra' para los diarios de notas de débito del proveedor.")

    default_iva_account = fields.Many2one('account.account', string='Cuenta retención IVA')
    default_islr_account = fields.Many2one('account.account', string='Cuenta retención ISLR')
    is_iva_journal = fields.Boolean(default=False)
    is_islr_journal = fields.Boolean(default=False)
    eliminar_impuestos = fields.Boolean(default=False, string="Eliminar impuestos")
    permitir_itf = fields.Boolean(default=False, string="Permitir ITF")

