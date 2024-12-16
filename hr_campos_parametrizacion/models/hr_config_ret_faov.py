# coding: utf-8
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
import calendar
from odoo.exceptions import UserError, ValidationError

class HrConfigFaov(models.Model):
    _name = 'hr.config.faov'
    _description = 'Configuracion retencion FAOV'

    grup_nomina_id = fields.Many2one('hr.payroll.structure.type')
    tipo_pago_id = fields.Many2one('hr.payroll.structure')
    line_reglas = fields.One2many('hr.faov.reglas', 'config_faov_id', string='reglas')
    regla_sueldo_base = fields.Many2one('hr.salary.rule')
    activo = fields.Boolean(default=True)

class HrLineReglas(models.Model):
    _name = 'hr.faov.reglas'

    config_faov_id = fields.Many2one('hr.config.faov')
    tipo_nomina_id = fields.Many2one(related='config_faov_id.grup_nomina_id',store=True)
    tipo_pago_id = fields.Many2one(related='config_faov_id.tipo_pago_id',store=True)
    regla_id = fields.Many2one('hr.salary.rule')