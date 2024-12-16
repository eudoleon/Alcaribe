from odoo import fields, models


class Users(models.Model):
    _inherit = 'res.users'

    pos_access_close = fields.Boolean(string='Access for Closing POS', default=True,
                                      help='Enabling this will allow user to close POS')
    pos_access_decrease_quantity = fields.Boolean(string='Access for Decreasing Quantity',
                                                  default=True,
                                                  help=('Enabling this will allow user to'
                                                        ' decrease quantity in order line'))
    pos_access_delete_order = fields.Boolean(string='Access to Order Deletion', default=True,
                                             help='Enabling this will allow user to delete order')
    pos_access_delete_orderline = fields.Boolean(string='Access to Order Line Deletion',
                                                 default=True, help=('Enabling this will allow '
                                                                     'user to delete order line'))
    pos_access_discount = fields.Boolean(string='Access to Discount', default=True,
                                         help='Enabling this will allow user to apply discount')
    pos_access_payment = fields.Boolean(string='Access to Payment', default=True,
                                        help='Enabling this will allow user to apply payment')
    pos_access_price = fields.Boolean(string='Access to Price Change', default=True,
                                      help='Enabling this will allow user to change price')
