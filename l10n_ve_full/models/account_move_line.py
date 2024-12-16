# coding: utf-8
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    apply_wh = fields.Boolean(
        string='Withheld', default=False,
        help="Indicates whether a line has been retained or not, to"
             " accumulate the amount to withhold next month, according"
             " to the lines that have not been retained.")
    concept_id = fields.Many2one('account.wh.islr.concept', 'Concepto de Islr', ondelete='cascade',
                                 help="concepto de retención de ingresos asociada a esta tasa",
                                 default=lambda self: self.env['account.wh.islr.concept'].search(
                                     [('name', '=', 'NO APLICA RETENCION')]))
    state = fields.Selection([('draft', 'Borrador'),
                              ('open', 'Abierto'),
                              ('paid', 'Pagado'),
                              ('cancel', 'Cancelado'),
                              ], index=True, readonly=True, default='draft', tracking=True, copy=False,
                             help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed Invoice.\n"
                                  " * The 'Pro-forma' status is used when the invoice does not have an invoice number.\n"
                                  " * The 'Open' status is used when user creates invoice, an invoice number is generated. It stays in the open status till the user pays the invoice.\n"
                                  " * The 'Paid' status is set automatically when the invoice is paid. Its related journal entries may or may not be reconciled.\n"
                                  " * The 'Cancelled' status is used when user cancel invoice.")


    wh_xml_id = fields.Many2one('account.wh.islr.xml.line',string='XML Id',default=0,help="XML withhold line id")


    # @api.onchange('product_id')
    # def _onchange_product_id(self):
    #     super(AccountMoveLine, self)._onchange_product_id()
    #     for line in self:
    #         line.concept_id = line.product_id.concept_id

    @api.model_create_multi
    def create(self, vals):
        """ Initialilizes the fields wh_xml_id and apply_wh,
        when it comes to a new line
        """
        context = self._context or {}
        if context.get('new_key', False):
            vals.update({'wh_xml_id': False,
                         'apply_wh': False,
                         })
        return super(AccountMoveLine, self).create(vals)


