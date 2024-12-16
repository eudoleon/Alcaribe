# coding: utf-8
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
import calendar
from odoo.exceptions import UserError, ValidationError


class HrPauslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    dias = fields.Char(compute='_compute_dias')
    total_uds = fields.Float(compute='_compute_total_usd')

    def _compute_total_usd(self):
        for rec in self:
            if rec.slip_id.os_currecy_rate_gene!=0:
                rec.total_uds=rec.total/rec.slip_id.os_currecy_rate_gene
            else:
                rec.total_uds=rec.total


    """@api.depends('quantity', 'amount', 'rate','dias')
    def _compute_total(self):
        for line in self:
            line.total = line.dias*float(line.quantity) * line.amount * line.rate / 100"""

    def _compute_dias(self):
        valor="--"
        for rec in self:
            rec.name=rec.salary_rule_id.name
            if rec.code=="BASIC":
                valor=rec.slip_id.workdays#rec.slip_id.days_attended
            if rec.code=='DIADES':
                valor=rec.slip_id.saturdays_sundays_act #-rec.slip_id.saturdays_sundays_vac # nuevo2
            if rec.code=='DIADEL':
                valor=rec.slip_id.hollydays_str # nuevo2
            if rec.code=="DIAFE":
                valor=rec.slip_id.holydays
            if rec.code=="DIAFEL":
                valor=rec.slip_id.hollydays_ftr
            if rec.code=="LPP":
                valor=rec.slip_id.dias_peternidad
            if rec.code=="IRM":
                valor=rec.slip_id.dias_reposo_medico
            if rec.code=="IRML":
                valor=rec.slip_id.dias_reposo_medico_lab
            if rec.code=="PERE":
                valor=rec.slip_id.dias_permiso_remunerado
            if rec.code=="DPREPOS":
                valor=rec.slip_id.dias_pos_natal
            if rec.code=="PNR":
                valor=rec.slip_id.dias_no_remunerado
            if rec.code=="INASIS":
                valor=rec.slip_id.dias_ausencia_injus
            if rec.code=="BOAYEC":
                #valor=rec.slip_id.days_attended # nuevo2
                valor=rec.slip_id.struct_id.shedule_pay_value-rec.slip_id.dif_dias_ingreso-rec.slip_id.dif_dias_egreso # nuevo2
            if rec.code=="DSP":
                valor=int(rec.slip_id.dias_pen_d_value)
            if rec.code=="BFA":
                valor=int(rec.slip_id.dias_utilidades) # nuevo2
            if rec.code=="CESTIK":
                valor=rec.slip_id.struct_id.shedule_pay_value-rec.slip_id.dif_dias_ingreso-rec.slip_id.dif_dias_egreso # nuevo2
            rec.dias=str(valor)
            valor="--"