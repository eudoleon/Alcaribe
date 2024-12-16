# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class PosOrder(models.Model):
    _inherit = "pos.order"

    z_report = fields.Char("Reporte Z", ralated="session_id.x_pos_z_report_number", store=True)

    num_factura = fields.Char("Num. Factura Fiscal", store=True)

    def set_num_factura(self, name, number):
        o = self.env['pos.order'].search([('pos_reference','=',name)])
        if o:
            o.write({"num_factura": number})

    @api.model
    def _order_fields(self, ui_order):
        order_fields = super(PosOrder, self)._order_fields(ui_order)
        order_fields['num_factura'] = ui_order.get('num_factura')
        return order_fields

    def _export_for_ui(self, order):
        result = super(PosOrder, self)._export_for_ui(order)
        result.update({
            'num_factura': order.num_factura,
        })
        return result

class PosSession(models.Model):
    _inherit = "pos.session"

    x_pos_z_report_number = fields.Char("Número Reporte Z")

    #campo el reporte z desde pos.report.z
    pos_report_z_id = fields.Many2one("pos.report.z", "Reporte Z")

    def set_z_report(self, number):
        #buscar si existe un reporte z en pos.report.z con el mismo número
        z_report = self.env['pos.report.z'].sudo().search([('number','=',number)])
        if z_report:
            #agregar la sesión al campo pos_session_ids many2many
            z_report.write({"pos_session_ids": [(4, self.id)]})
            z_report._onchange_pos_session_ids()
            self.sudo().write({"x_pos_z_report_number": number, 'pos_report_z_id': z_report.id})
        else:
            #crear un reporte z con el número
            z_report = self.env['pos.report.z'].sudo().create({
                "number": number,
                'date': datetime.today(),
                'x_fiscal_printer_id': self.config_id.x_fiscal_printer_id.id,
                "pos_session_ids": [(4, self.id)],
            })
            z_report.sudo()._onchange_pos_session_ids()
            self.sudo().write({"x_pos_z_report_number": number, 'pos_report_z_id': z_report.id})
            activity = {
                'res_id': z_report.id,
                'res_model_id': self.env['ir.model'].search([('model', '=', 'pos.report.z')]).id,
                'user_id': self.env.user.id,
                'summary': 'Verificar reporte Z',
                'note': 'Verifica si existe otra sesión para este reporte Z y validar el reporte Z',
                'activity_type_id': 4,
                'date_deadline': datetime.today(),
            }

            self.env['mail.activity'].sudo().create(activity)

    def _loader_params_pos_payment_method(self):
        result = super()._loader_params_pos_payment_method()
        result['search_params']['fields'].extend([
            "x_printer_code",
            "x_igtf_percentage",
            "x_is_foreign_exchange",
        ])
        return result

    def _loader_params_account_tax(self):
        result = super()._loader_params_account_tax()
        result['search_params']['fields'].append('x_tipo_alicuota')
        return result

    def _loader_params_res_partner(self):
        result = super()._loader_params_res_partner()
        result['search_params']['fields'].extend(['company_type', 'city_id'])
        return result

    def _pos_ui_models_to_load(self):
        result = super(PosSession, self)._pos_ui_models_to_load()
        result.append('res.city')
        return result
    
    def _loader_params_res_company(self):
        result = super(PosSession, self)._loader_params_res_company()
        result['search_params']['fields'].append('city')
        return result

    def _loader_params_res_city(self):
        return {"search_params": {"domain": [("country_id.code", "=", "VE")], "fields": ["name", "country_id", "state_id"]}}
  


    def _get_pos_ui_res_city(self, params):
        return self.env['res.city'].search_read(**params['search_params'])

class AccountTax(models.Model):
    _inherit = "account.tax"

    x_tipo_alicuota = fields.Selection([
        ("exento", "Exento"),
        ("general", "General"),
        ("reducido", "Reducido"),
        ("adicional", "Adicional"),
    ], "Tipo de alícuota", tracking=True, default="general")

class PosConfig(models.Model):
    _inherit = "pos.config"

    x_fiscal_command_baudrate = fields.Integer("Baudrate", tracking=True, default=9600)
    x_fiscal_commands_time = fields.Integer("Tiempo de espera", tracking=True, default=750,)
    x_fiscal_printer_id = fields.Many2one("x.pos.fiscal.printer", "Impresora fiscal", tracking=True)
    x_fiscal_printer_code = fields.Char(related="x_fiscal_printer_id.serial")
    flag_21 = fields.Selection([('00', '00'), ('30', '30')], string="Flag 21", related="x_fiscal_printer_id.flag_21")
    connection_type = fields.Selection([('serial', 'Serial'), ('usb', 'USB'), ('usb_serial', 'USB Serial'),('file', 'Archivo'), ('api', 'API')], related="x_fiscal_printer_id.connection_type")
    api_url = fields.Char(related="x_fiscal_printer_id.api_url")

class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    x_printer_code = fields.Char("Código en la impresora")

    @api.constrains("x_printer_code")
    def _check_x_printer_code(self):
        for rec in self:
            if len(rec.x_printer_code) != 2:
                raise ValidationError("El código en la impresora sólo puede tener dos caracteres")

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_x_fiscal_command_baudrate = fields.Integer(
        "Baudrate",
        related="pos_config_id.x_fiscal_command_baudrate",
        store=True,
        readonly=False,
        default=9600
    )
    pos_x_fiscal_commands_time = fields.Integer(
        "Tiempo de espera", 
        related="pos_config_id.x_fiscal_commands_time",
        store=True,
        readonly=False,
        default=750,
    )
    pos_x_fiscal_printer_id = fields.Many2one(
        string="Impresora fiscal", 
        related="pos_config_id.x_fiscal_printer_id",
        readonly=False,
        store=True,
    )

    flag_21 = fields.Selection([('00', '00'), ('30', '30')], string="Flag 21", related="pos_config_id.flag_21",
        store=True)

    connection_type = fields.Selection([('serial', 'Serial'), ('usb', 'USB'), ('usb_serial', 'USB Serial'),('file', 'Archivo'), ('api', 'API')],
        related="pos_config_id.connection_type",
        store=True
    )

    api_url = fields.Char(related="pos_config_id.api_url",
        store=True)







    @api.constrains("pos_x_fiscal_commands_time")
    def _check_x_fiscal_commands_time(self):
        for rec in self:
            if rec.pos_x_fiscal_commands_time < 0:
                raise ValidationError(_("El tiempo entre comandos no puede ser cero"))

class Partner(models.Model):
    _inherit = "res.partner"

    @api.model
    def create_from_ui(self, partner):
        if partner.get('country_id'):
            partner['country_id'] = int(partner.get('country_id'))       
        if partner.get('city_id'):
            city_id = int(partner.get('city_id'))
            partner['city_id'] = city_id
            City = self.env['res.city']
            city = City.browse(city_id)
            if city.exists():
                partner['city'] = city.name
            else:
                partner['city'] = ''

        return super().create_from_ui(partner)