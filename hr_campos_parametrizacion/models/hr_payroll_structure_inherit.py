# coding: utf-8
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
import calendar
from odoo.exceptions import UserError, ValidationError

class HrPayrollStructure(models.Model):
    _inherit = 'hr.payroll.structure'

    activo_prestaciones = fields.Boolean(string='Calcular Prsetaciones Sociales', default=True)
    shedule_pay_value = fields.Integer(string='Valor Pago Planificado', compute='_compute_dias_pago')

    @api.onchange('schedule_pay')
    def _compute_dias_pago(self):
        value=15
        if self.schedule_pay=="monthly":
            value=30
        if self.schedule_pay=="quarterly":
            value=90
        if self.schedule_pay=="semi-annually":
            value=180
        if self.schedule_pay=="annually":
            value=360
        if self.schedule_pay=="weekly":
            value=7
        if self.schedule_pay=="bi-weekly":
            value=15
        if self.schedule_pay=="bi-monthly":
            value=60
        self.shedule_pay_value=value