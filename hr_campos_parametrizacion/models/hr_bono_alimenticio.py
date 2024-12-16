# coding: utf-8
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
import calendar
from odoo.exceptions import UserError, ValidationError


class hr_special_days(models.Model):
    _inherit = 'hr.payslip'

    #days_attended = fields.Char(string='Días asistidos', compute='_compute_days_attended')
    monto_bono_alimenticio = fields.Float(compute='_bono_div')


    def _bono_div(self):
        for selff in self:
            id_moneda_bono=selff.employee_id.contract_id.bono_alimenticio_currency.id
            id_moneda_compa=selff.company_id.currency_id.id
            monto_bono_alimenticio=selff.employee_id.contract_id.bono_alimenticio_value
            dia_pago=selff.employee_id.contract_id.bono_alimenticio_dia_tasa
            valor_aux=0.000000000000000000000000000001
            if id_moneda_compa!=id_moneda_bono:
                tasa= selff.env['res.currency.rate'].search([('currency_id','=',id_moneda_bono),('name','<=',selff.date_to)],order="name asc") #('hora','>=',selff.date_from)
                for det_tasa in tasa:
                    if dia_pago=='al' or not dia_pago:
                        valor_aux=det_tasa.rate#rate_real
                    if dia_pago!='al':
                        fecha_tasa=det_tasa.name#hora
                        dia=selff.dia(fecha_tasa)
                        mes=selff.mes(fecha_tasa)
                        ano=selff.ano(fecha_tasa)
                        dia_aux=str(calendar.weekday(ano,mes,dia))
                        if dia_pago==dia_aux:
                            valor_aux=det_tasa.rate#rate_real
                rate=round(1*valor_aux,2)
                resultado=monto_bono_alimenticio*rate
            else:
                resultado=monto_bono_alimenticio
            selff.monto_bono_alimenticio=resultado

    def dia(self,date):
        fecha = str(date)
        fecha_aux=fecha
        dia=fecha[8:10]  
        resultado=dia
        return int(resultado)

    def mes(self,date):
        fecha = str(date)
        fecha_aux=fecha
        mes=fecha[5:7]
        resultado=mes
        return int(resultado)

    def ano(self,date):
        fecha = str(date)
        fecha_aux=fecha
        ano=fecha_aux[0:4]  
        resultado=ano
        return int(resultado)
