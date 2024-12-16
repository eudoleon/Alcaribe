# coding: utf-8
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
import calendar
from odoo.exceptions import UserError, ValidationError

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    metodo_tipo = fields.Boolean()
    tipo_metodo = fields.Selection([('men', 'Mensual'),('tri','trimestral')],related='company_id.tipo_metodo')

class Company(models.Model):
    _inherit = 'res.company'

    tipo_metodo = fields.Selection([('men', 'Mensual'),('tri','Trimestral')],default='tri')
    tipo_dif_dias = fields.Selection([('fech_con','Fecha Contable'),('fech_cal','Fecha Calendario')],default='fech_con')

    #service_years= fields.Integer()
    #pay_day = fields.Integer()