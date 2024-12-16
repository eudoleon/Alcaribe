# coding: utf-8
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
import calendar
from odoo.exceptions import UserError, ValidationError

class hrIncrementoBanda(models.Model):
    _name = 'hr.banda.incremento'
    _description = 'Tabla de Banda de incremento Salarial'

    fecha_decreto = fields.Date()
    fecha_incremento = fields.Date()
    motivo = fields.Char()
    responsable = field_id = fields.Many2one('res.partner')
    sueldo_minimo = fields.Float()
    state = fields.Selection([('draft','Borrador'),('actv','Activo'),('inactv','Inactivo')],default="draft")
    tipo_aumento = fields.Selection([('porcentaje', 'Porcentaje(%)'),('fix','Monto Fijo'),('fac','Factor de corrección')],default="fix")
    monto_fijo = fields.Float()
    monto_porcentage_basa = fields.Selection([('sm','Monto Sueldo Mínimo'),('wage','Salario Mensual Contrato Individual')])
    porcentage = fields.Float()
    texto = fields.Text(defaul='Texto instructivo')
    seleccion_aumento = fields.Selection([('lot','Por Lote'),('ind','Individual')],default='lot')
    line  = fields.Many2many(comodel_name='hr.banda.empleado', string='Lineas de Empleados')
    line_ind_empleado  = fields.One2many('hr.ind.empleado','banda_incremento_id', string='Selección Empleados')

    def procesar(self):
        if self.tipo_aumento=="fix" and self.seleccion_aumento!='ind':
            verifica=self.env['hr.contract'].search([('state','=','open')],order='id desc')
            if verifica:
                for det in verifica:
                    sueldo_anterior=det.wage
                    det.wage=det.wage+self.monto_fijo
                    self.registra_employe(det,sueldo_anterior)
                self.state="actv"
                lista_banda=self.env['hr.banda.incremento'].search([('id','!=',self.id)],order='id desc')
                for det_ban in lista_banda:
                    det_ban.state="inactv"

                self.line = self.env['hr.banda.empleado'].search([('banda_incremento_id','=',self.id)])

        if self.tipo_aumento=="porcentaje" and self.seleccion_aumento!='ind':
            verifica=self.env['hr.contract'].search([('state','=','open')],order='id desc')
            if verifica:
                for det in verifica:
                    if self.monto_porcentage_basa=="wage":
                        sueldo_anterior=det.wage
                        det.wage=(det.wage+det.wage*self.porcentage/100)
                        self.registra_employe(det,sueldo_anterior)
                    if self.monto_porcentage_basa=="sm":
                        if self.sueldo_minimo==0 or self.sueldo_minimo<0:
                            raise UserError(_('El campo dee sueldo minimo no debe ser nulo ni negativo'))
                        else:
                            sueldo_anterior=det.wage
                            det.wage=(det.wage+self.sueldo_minimo*self.porcentage/100)
                            self.registra_employe(det,sueldo_anterior)
                self.state="actv"
                lista_banda=self.env['hr.banda.incremento'].search([('id','!=',self.id)],order='id desc')
                for det_ban in lista_banda:
                    det_ban.state="inactv"

                self.line = self.env['hr.banda.empleado'].search([('banda_incremento_id','=',self.id)])

        if self.tipo_aumento=="fac":
            raise UserError(_('Esta opcion no esta disponible aun'))

        if self.seleccion_aumento=='ind':
            if self.line_ind_empleado:
                for empleado in self.line_ind_empleado:
                    verifica=self.env['hr.contract'].search([('state','=','open'),('employee_id','=',empleado.employee_id.id)],order='id desc')
                    if verifica:
                        for det in verifica:
                            if self.tipo_aumento=="fix":
                                sueldo_anterior=det.wage
                                det.wage=det.wage+self.monto_fijo
                                self.registra_employe(det,sueldo_anterior)
                            if self.tipo_aumento=="porcentaje":
                                if self.monto_porcentage_basa=="wage":
                                    sueldo_anterior=det.wage
                                    det.wage=(det.wage+det.wage*self.porcentage/100)
                                    self.registra_employe(det,sueldo_anterior)
                                if self.monto_porcentage_basa=="sm":
                                    if self.sueldo_minimo==0 or self.sueldo_minimo<0:
                                        raise UserError(_('El campo dee sueldo minimo no debe ser nulo ni negativo'))
                                    else:
                                        sueldo_anterior=det.wage
                                        det.wage=(det.wage+self.sueldo_minimo*self.porcentage/100)
                                        self.registra_employe(det,sueldo_anterior)
                        self.state="actv"
                        lista_banda=self.env['hr.banda.incremento'].search([('id','!=',self.id)],order='id desc')
                        for det_ban in lista_banda:
                            det_ban.state="inactv"

                        self.line = self.env['hr.banda.empleado'].search([('banda_incremento_id','=',self.id)])
                    else:
                        raise UserError(_('El empleado %s no posse contrato activo')%empleado.employee_id.name)
            else:
                raise UserError(_('Debe seleccionar al menos un empleado activo con contrato'))

    def unlink(self):
        for selff in self:
            if selff.state!="draft":
                raise UserError(_('No se puede eliminar los registros. Solo los que estan en estado Borrador'))
            else:
                res = super(hrIncrementoBanda, self).unlink()



    def registra_employe(self,contrac,sueldo_anterior):
        employee=self.env['hr.banda.empleado']
        values={
        'banda_incremento_id':self.id,
        'employee_id':contrac.employee_id.id,
        'sueldo_anterior':sueldo_anterior,
        'sueldo_nuevo':contrac.wage,
        }
        id_employee = employee.create(values)

    def cancel(self):
        if self.state=="actv":
            banda_emple=self.env['hr.banda.empleado'].search([('banda_incremento_id','=',self.id)])
            for det_emple in banda_emple:
                list_contrato=self.env['hr.contract'].search([('state','=','open'),('employee_id','=',det_emple.employee_id.id)])
                list_contrato.write({
                    'wage':det_emple.sueldo_anterior
                    })
            banda_emple.unlink()
            self.state="draft"
        if self.state=="inactv":
            raise UserError(_('No se puede cancelar esta banda ya que hay otra más reciente y activa'))


class hrBantaEmpleado(models.Model):
    _name = 'hr.banda.empleado'
    _description = 'Tabla de empleados que entra en la banda salarial'

    banda_incremento_id=fields.Many2one('hr.banda.incremento')
    employee_id=fields.Many2one('hr.employee')
    sueldo_anterior=fields.Float()
    sueldo_nuevo=fields.Float()

class hrIndEmpleado(models.Model):
    _name = 'hr.ind.empleado'
    _description = 'Tabla de empleados individuales'

    banda_incremento_id=fields.Many2one('hr.banda.incremento')
    employee_id=fields.Many2one('hr.employee')
