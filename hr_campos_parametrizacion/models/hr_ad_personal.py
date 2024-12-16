# coding: utf-8
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
import calendar
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval

class HrAdPeronal(models.Model):

    _name = 'hr.ad.personal'
    _order = 'structur_id asc, rule_id asc'
    

    name=fields.Char()
    modo=fields.Selection([('t','Todos los empleados de esta nómina'),('u','Un empleado en especifico')])
    employee_id=fields.Many2one('hr.employee')
    #employee2_id=fields.Many2one('hr.payroll.employeed')
    structur_id=fields.Many2one('hr.payroll.structure')
    rule_id=fields.Many2one('hr.salary.rule')
    state=fields.Selection(selection=[('hold','En Espera'),('action','En ejecución'),('culminated','Culminado')],default='hold')
    company_id=fields.Many2one("res.company", string="Compañia", default=lambda self: self.env.company)
    currency_id=fields.Many2one('res.currency',default=lambda self: self.env.company.currency_id)

    modo_aplicacion=fields.Selection([
        ('a','Siempre'), # colocar una opcion que diga de forma semanal, quincenal, mensual
        ('b','A partir de una fecha Especifica'), # colocar campo fecha y opcion si es quincenal, semanal, mensual
        ('c','Una Sola vez inmediatamente en la siguiente Nómina'),
        ('d','Una Sola vez en una Fecha Especifica'), #colocar una opcion aqui una fecha que sea parte de un periodo de pago
    ], string="Modo de Aplicación", default='a', required=True)
    shedule_pay=fields.Selection([
        ('mensual','Una vez al Mes'),
        ('quincenal','Cada Quincena'),
        ('semanal','Cada Semana'),
    ], string="Pago planificado", default='mensual', required=True)
    shedule_pay_mensual=fields.Selection([('1ra','Primera quincena mes'),('ult','Segunda quincena mes')],default='1ra')
    fecha=fields.Date()

    origen_calculo=fields.Selection([('1','Confg. en la regla o concepto'),('2','Aqui en AD Personal')],default="1")
    modo_calculo = fields.Selection([('a','Valor Fijo'),('b','Por Fórmula')],default='a')
    monto_fijo=fields.Monetary()
    formula = fields.Text(default="  # Available variables:"
                                  "  #----------------------"
                                  "# payslip: object containing the payslips"
                                  " # employee: hr.employee object"
                                  "# contract: hr.contract object"
                                  "# rules: object containing the rules code (previously computed)"
                                  "# categories: object containing the computed salary rule categories (sum of amount of all rules belonging to that category)."
                                  "# worked_days: object containing the computed worked days."
                                  "# inputs: object containing the computed inputs."
                                  "# Note: returned value have to be set in the variable 'result'"
                                  "     "
                                  "result = contract.wage * 0.10"
                                  )
    @api.depends('rule_id')
    @api.onchange('rule_id')
    def actualiza_name(self):
      #raise UserError(_("prueba"))
      for selff in self:
        selff.name=selff.rule_id.name

    def activar(self):
        if self.modo=='u' and self.employee_id:# aqui si selecciono un empleado
          ban_1=0
          for line_employee in self.structur_id.employee_ids:
              if line_employee.empleado_id==self.employee_id:
                  ban_1=ban_1+1
          if ban_1==0:
              raise UserError(_("Este empleado no pertenece a la nómina seleccionada. Vaya primero a la estructura"
                              " o Nómina e incorpore a este empleado"))

          valida_ad=self.env['hr.ad.personal'].search([('employee_id','=',self.employee_id.id),('state','=','action'),('rule_id','=',self.rule_id.id),('id','!=',self.id)])
          if valida_ad:
              raise UserError(_("Ya existe un adp activo con la misma Regla o Concepto y Empleado. No se puede activar el AD actual"))

          if ban_1>0:
              self.state='action'

        if self.modo=='t': # aqui si es todo los empleados del proceso de la nomina
          if not self.structur_id.employee_ids:
            raise UserError(_("Este proceso de nómina no tiene asociado empleados"))
          else:
            cont=0
            for employee in self.structur_id.employee_ids:
              valida_ad=self.env['hr.ad.personal'].search([('employee_id','=',employee.id),('state','=','action'),('rule_id','=',self.rule_id.id),('id','!=',self.id)])
              if valida_ad:
                raise UserError(_("Ya existe un adp activo con la misma Regla o Concepto y Empleado. No se puede activar el AD actual"))
              cont=cont+1
              if cont<=1:
                self.employee_id=employee.id
                self.modo='u'
                self.state='action'
              else:
                self.duplica(employee)

    def duplica(self,employee):
      values=({
        'name':self.name,
        'modo':self.modo,
        'employee_id':employee.id,
        'structur_id':self.structur_id.id,
        'rule_id':self.rule_id.id,
        'modo_aplicacion':self.modo_aplicacion,
        'shedule_pay':self.shedule_pay,
        'shedule_pay_mensual':self.shedule_pay_mensual,
        'fecha':self.fecha,
        'origen_calculo':self.origen_calculo,
        'modo_calculo':self.modo_calculo,
        'monto_fijo':self.monto_fijo,
        'formula':self.formula,
        })
      id_ad_personal=self.env['hr.ad.personal'].create(values)
      id_ad_personal.state='action'




    def cancel(self):
        self.state='hold'

    def unlink(self):
        for rec in self:
            if rec.state=="action":
                raise UserError(_("No se puede eliminar los AD personales que esten en estatus de ejecución"))
        super(HrAdPeronal,self).unlink()