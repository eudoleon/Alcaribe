# coding: utf-8
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
import calendar
from odoo.exceptions import UserError, ValidationError

class hr_tindicadores_economicos(models.Model):
    _name = 'hr.payroll.indicadores.economicos'
    _description = 'Indicadores Económicos'

    name = fields.Char()
    code = fields.Char()
    valor = fields.Float()


    #service_years= fields.Integer()
    #pay_day = fields.Integer()