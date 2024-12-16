# coding: utf-8
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
import calendar
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval

class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'
    _order = 'sequence, id'
    _description = 'Salary Rule'

    desc_ley = fields.Char()
    company_id = fields.Many2one('res.company','Company',default=lambda self: self.env.company.id)
    condition_select = fields.Selection([
        ('none', 'Always True'),
        ('range', 'Range'),
        ('adp','Módulo AD Personal'),
        ('python', 'Python Expression')
    ], string="Condition Based on", default='none', required=True)
    amount_python_compute_aux = fields.Text()
    amount_select_aux= fields.Char()
    devengado = fields.Boolean(default=False,help="Al activar este campo, indica que esta regla sera parte del calculo de los devengados, para otra regla, o ince, faov, sso, etc")

    utilidades = fields.Boolean(default=False)
    vacaciones = fields.Boolean(default=False)
    prestaciones = fields.Boolean(default=False)
    rpvh = fields.Boolean(default=False)
    islr = fields.Boolean(default=False)
    inces = fields.Boolean(default=False)
    salario_normal = fields.Boolean(default=False)


    def _satisfy_condition(self, localdict):
        self.ensure_one()
        #raise UserError(_('localdict=%s')%localdict)
        if self.condition_select == 'none':
            return True
        if self.condition_select == 'range':
            try:
                result = safe_eval(self.condition_range, localdict)
                return self.condition_range_min <= result <= self.condition_range_max
            except:
                raise UserError(_('Wrong range condition defined for salary rule %s (%s).') % (self.name, self.code))
        
        if self.condition_select == 'adp':
            return self.cod_adp(localdict)
            #return True
        else:  # python code
            try:
                safe_eval(self.condition_python, localdict, mode='exec', nocopy=True)
                return localdict.get('result', False)
            except:
                raise UserError(_('Wrong python condition defined for salary rule %s (%s).') % (self.name, self.code))
    

    def cod_adp(self,localdict):
        #raise UserError(_('Entro en python regla=%s')%localdict['contract'])
        #raise UserError(_('Entro en python regla=%s')%localdict['employee'].id)
        #raise UserError(_('Entro en python regla=%s')%localdict['payslip'].id)
        valor=False
        aprueba='no'
        busca_ad_personal=self.env['hr.ad.personal'].search([('employee_id','=',localdict['employee'].id),('state','=','action'),('rule_id','=',self.id)])
        if busca_ad_personal:
            for det in busca_ad_personal:
                if det.modo_aplicacion=="a": #Modo aplicacion = siempre
                    if det.shedule_pay=="mensual":
                        fecha=str(localdict['payslip'].date_from)
                        mes = int(fecha[5:7])
                        year = int(fecha[0:4])
                        if mes<10:
                            mess="0"+str(mes)
                        if det.shedule_pay_mensual=="1ra":
                            if str(localdict['payslip'].date_from)<=str(year)+"-"+mess+"-05" and str(localdict['payslip'].date_to)>=str(year)+"-"+mess+"-05":
                                aprueba='si'
                        if det.shedule_pay_mensual=="ult":
                            if str(localdict['payslip'].date_from)<=str(year)+"-"+mess+"-25" and str(localdict['payslip'].date_to)>=str(year)+"-"+mess+"-25":
                                aprueba="si"
                    if det.shedule_pay=="quincenal" or det.shedule_pay=="semanal":
                        aprueba="si"

                if det.modo_aplicacion=="b": #Modo aplicacion = A partir de una fecha Especifica
                    if localdict['payslip'].date_to>=det.fecha:
                        aprueba="si"

                if det.modo_aplicacion=="c": #Modo aplicacion = Una Sola vez inmediatamente en la siguiente Nómina
                    aprueba="si"

                if det.modo_aplicacion=="d": #Modo aplicacion = Una Sola vez en una Fecha Especifica
                    if localdict['payslip'].date_to>=det.fecha:
                        aprueba="si"

                if aprueba=='si':
                    
                    if det.origen_calculo=="2":
                        if not self.amount_python_compute_aux:
                            self.amount_python_compute_aux=self.amount_python_compute
                        if not self.amount_select_aux:
                            self.amount_select_aux=self.amount_select
                            self.amount_select='code'
                        if not det.modo_calculo:
                            raise UserError(_("El concepto o regla: %s, es tipo AD personal, y no tiene configurado el modo del calculo, vaya al módulo de ad personal y configure")%self.name)
                        if det.modo_calculo=="a":  # si en el modulo de ad personal la opcion es monto fijo
                            self.amount_python_compute="result = employee.rule_python"
                            localdict['employee'].rule_python=det.monto_fijo
                        if det.modo_calculo=='b': # si en el modulo de ad personal la opcion es por formula
                            self.amount_python_compute="employee.rule_python"
                            localdict['employee'].rule_python=safe_eval(det.formula,localdict, mode='exec', nocopy=True)
                        valor=True

                    if det.origen_calculo=="1":
                        if self.amount_python_compute_aux and (self.amount_python_compute=="result = employee.rule_python" or self.amount_python_compute=="employee.rule_python"):
                            self.amount_python_compute=self.amount_python_compute_aux
                        self.amount_python_compute_aux=""
                        if self.amount_select_aux:
                            self.amount_select=self.amount_select_aux
                        self.amount_select_aux=""
                        valor=True
        return valor
                    #raise UserError(_("monto=%s")%monto)


###  ESTAS CLASES O CÓDIGOS DE ABAJO NO SE MUEVE DE ESTE ARCHIVO POR AHORA
class HrEmployee(models.Model):

    _inherit='hr.employee'

    rule_python=fields.Text()

class HrPayslip(models.Model):

    _inherit = 'hr.payslip'

    @api.constrains('state') #@api.onchange
    def valida_adp(self):
        for selff in self:
            if selff.state=="done":
                for line in selff.line_ids:
                    rule=line.salary_rule_id
                    employee_id=selff.employee_id.id
                    busca_ad_personal=selff.env['hr.ad.personal'].search([('employee_id','=',employee_id),('state','=','action'),('rule_id','=',rule.id)])
                    if busca_ad_personal:
                        for rec in busca_ad_personal:
                            if rec.modo_aplicacion=='c' or rec.modo_aplicacion=='d':
                                rec.state="culminated"