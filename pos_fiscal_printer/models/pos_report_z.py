#módulo para almacenar el reporte z de la impresora fiscal
from odoo import models, fields, api
class PosReportZ(models.Model):
    _name = "pos.report.z"
    _description = "Reporte Z"
    _order = "id desc"
    _rec_name = "number"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    #número de reporte
    number = fields.Char("Número de reporte", required=True, tracking=True)

    #state
    state = fields.Selection([('draft', 'Borrador'), ('done', 'Hecho')], string='Estado', default='draft', tracking=True)

    #impresora fiscal
    x_fiscal_printer_id = fields.Many2one("x.pos.fiscal.printer", "Impresora fiscal", tracking=True)
    x_fiscal_printer_code = fields.Char("Código de la impresora fiscal", related="x_fiscal_printer_id.serial", store=True, tracking=True)
    connection_type = fields.Selection([('serial', 'Serial'), ('usb', 'USB'), ('usb_serial', 'USB Serial'),('file', 'Archivo'), ('api', 'API')], related="x_fiscal_printer_id.connection_type", store=True)
    #fecha y hora del reporte
    date = fields.Datetime("Fecha y hora", tracking=True)

    #sesiones pos
    pos_session_ids = fields.Many2many("pos.session", string="Sesiones POS")

    #total acumulado exento
    total_exempt = fields.Float("Total exento", tracking=True)

    #total base imponible iva 16
    total_base_iva_16 = fields.Float("Total base imponible", tracking=True)

    #total iva 16
    total_iva_16 = fields.Float("Total iva", tracking=True)

    # total acumulado exento nota de crédito
    total_exempt_nc = fields.Float("Total exento NC", tracking=True)

    # total base imponible iva 16 nota de crédito
    total_base_iva_16_nc = fields.Float("Total base imponible 16 NC", tracking=True)

    # total iva 16 nota de crédito
    total_iva_16_nc = fields.Float("Total iva NC", tracking=True)

    #ventas pos asociadas a las sesiones cargadas
    pos_order_ids = fields.Many2many("pos.order", string="Ventas POS")

    #total excento ventas pos
    total_exempt_pos = fields.Float("Total Excento POS", tracking=True, compute="_compute_total_pos")

    #total base imponible iva 16 ventas pos
    total_base_iva_16_pos = fields.Float("Total Base Imponible POS", tracking=True, compute="_compute_total_pos")

    #total iva 16 ventas pos
    total_iva_16_pos = fields.Float("Total IVA POS", tracking=True, compute="_compute_total_pos")

    #total excento ventas pos nota de crédito
    total_exempt_pos_nc = fields.Float("Total Excento POS NC", tracking=True, compute="_compute_total_pos")

    #total base imponible iva 16 ventas pos nota de crédito
    total_base_iva_16_pos_nc = fields.Float("Total Base Imponible POS NC", tracking=True, compute="_compute_total_pos")

    #total iva 16 ventas pos nota de crédito
    total_iva_16_pos_nc = fields.Float("Total IVA POS NC", tracking=True, compute="_compute_total_pos")

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    fac_desde = fields.Char("Factura desde", tracking=True)
    fac_hasta = fields.Char("Factura hasta", tracking=True)

    @api.depends('pos_order_ids', 'state')
    def _compute_total_pos(self):
        fac_nums = []
        for report in self:
            report.total_exempt_pos = sum(report.pos_order_ids.filtered(lambda x: x.amount_total > 0).mapped("lines").filtered(lambda x: x.tax_ids.amount == 0).mapped("price_subtotal_incl"))
            total_base_iva_16_pos = sum(report.pos_order_ids.filtered(lambda x: x.amount_total > 0).mapped("lines").filtered(lambda x: x.tax_ids.amount == 16).mapped("price_subtotal"))
            total_16_pos = sum(report.pos_order_ids.filtered(lambda x: x.amount_total > 0).mapped("lines").filtered(lambda x: x.tax_ids.amount == 16).mapped("price_subtotal_incl"))
            report.total_base_iva_16_pos = total_base_iva_16_pos
            report.total_iva_16_pos = total_16_pos - total_base_iva_16_pos

            total_base_iva_16_pos_nc = sum(
                report.pos_order_ids.filtered(lambda x: x.amount_total < 0).mapped("lines").filtered(
                    lambda x: x.tax_ids.amount == 16).mapped("price_subtotal"))
            total_iva_16_pos_nc = sum(report.pos_order_ids.filtered(lambda x: x.amount_total < 0).mapped("lines").filtered(
                lambda x: x.tax_ids.amount == 16).mapped("price_subtotal_incl"))

            report.total_exempt_pos_nc = sum(report.pos_order_ids.filtered(lambda x: x.amount_total < 0).mapped("lines").filtered(lambda x: x.tax_ids.amount == 0).mapped("price_subtotal_incl"))
            report.total_base_iva_16_pos_nc = total_base_iva_16_pos_nc
            report.total_iva_16_pos_nc = total_iva_16_pos_nc - total_base_iva_16_pos_nc
            for order in report.pos_order_ids:
                if order.num_factura:
                    if order.num_factura not in fac_nums:
                        fac_nums.append(int(order.num_factura))
            if fac_nums:
                report.fac_desde = min(fac_nums)
                report.fac_hasta = max(fac_nums)


    def action_done(self):
        self.state = 'done'

    def action_draft(self):
        self.state = 'draft'

    @api.onchange('pos_session_ids')
    def _onchange_pos_session_ids(self):
        for report in self:
            report.pos_order_ids = report.pos_session_ids.mapped("order_ids")


