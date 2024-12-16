# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields,models,api,_
import datetime
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero
from datetime import datetime

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    prestamo_id=fields.Many2one('hr.prestamo', string='Lineas de Prestamos')
    status_prestamo=fields.Selection(selection=[('hold','En Espera'),('granted','Otorgado'),('solvent','Solvente')],default='hold')
    prestamo_activo = fields.Boolean(default=False)
    descuento_prestamo_activo = fields.Boolean(default=False)

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'


    def action_payslip_done(self):
        #raise UserError(_('Prueba BEBE'))
        res = super(HrPayslip, self).action_payslip_done()

        for det in self:
            empleado = self.env['hr.employee'].search([('id','=',det.employee_id.id)])
            for det_empl in empleado:
                if det_empl.descuento_prestamo_activo==True:
                    self.actualiza_descuento()
                if det_empl.status_prestamo=="hold" and det_empl.prestamo_activo==True:
                    vals={
                    'status_prestamo':"granted",
                    'prestamo_activo':False,
                    'descuento_prestamo_activo':True,
                    }
                    self.env['hr.employee'].browse(det_empl.id).write(vals)
        return res

    def actualiza_descuento(self):
        for selff in self:
            data_prestamo = self.env['hr.prestamo'].search([('empleado_id', '=', selff.employee_id.id),('status_prestamo','=','pending')])
            if data_prestamo:
                for det in data_prestamo:
                    monto_cuotas=det.monto_cuotas
                    cuotas=det.cuotas
                    #raise UserError(_('cuotas %s')%cuotas)
                    i=1
                    cont_solvete=0
                    for i in range(cuotas):
                        num=i+1
                        line_prestamo = self.env['hr.prestamo.line'].search([('prestamo_id','=',det.id)],order ="num_cuota asc")
                        if line_prestamo:
                            booleano=0
                            #cont_solvete=0
                            for det in line_prestamo:
                                if det.status_pago=="solvent":
                                    cont_solvete=cont_solvete+1
                                if det.status_pago=="pending" and booleano==0:
                                    vals={
                                    'monto_pagado':monto_cuotas,
                                    'status_pago':"solvent",
                                    'fecha_pago':datetime.now(),
                                    'payslip_id':selff.id,
                                    'payslip_run_id':selff.payslip_run_id,
                                    }
                                    self.env['hr.prestamo.line'].browse(det.id).write(vals)
                                    booleano=1
                                    cont_solvete=cont_solvete+1
                            #raise UserError(_('cont_solvete %s')%cont_solvete)
                            if cont_solvete==cuotas:
                                #raise UserError(_('listo'))
                                data_prestamo.write({'status_prestamo':"solvent",})
                                empleado2 = self.env['hr.employee'].search([('id','=',selff.employee_id.id)])
                                #raise UserError(_('empleado2 = %s')%empleado2)
                                for det_empl2 in empleado2:
                                    valss={
                                    'prestamo_activo':False,
                                    'descuento_prestamo_activo':False,
                                    'status_prestamo':"solvent",
                                    }
                                    empleado2.write(valss)



class SaleOrder(models.Model):
    _name = 'hr.prestamo'

    empleado_id=fields.Many2one("hr.employee",string="Empleado")
    cedula=fields.Char(string="Cedula")
    prestamo_fecha = fields.Date(string='Fecha del Prestamo')
    monto_prestamo = fields.Float(string='Monto del Prestamo', help='Monto del Prestamo')
    porcentaje= fields.Float(string='Porcentaje de Interes')
    status_prestamo=fields.Selection(selection=[('hold','En Espera'),('pending','Pendiente'),('solvent','Solvente')],default='hold',index=True, tracking=True,readonly=True, copy=False)
    adeudado=fields.Float(string='Monto Adeudado', help='Monto Adeudado')
    cuotas=fields.Integer(string="Nro de Cuotas", default='1')
    monto_cuotas= fields.Float(string="Monto Cuotas")
    prestamo_line_ids = fields.One2many('hr.prestamo.line', 'prestamo_id', string='Prestamos')
    company_id = fields.Many2one("res.company", string="Compañia", default=lambda self: self.env.company)
    forma_pago=fields.Selection(selection=[
        ('biweekly','Quincenal'),
        ('weekly','Semanal'),
        ('monthly','Mensual'),
        ('quarterly','Trimestral'),
        ('semi-annually','Semestral')
        ])

    @api.onchange('porcentaje','monto_prestamo')
    def monto_adeudado(self):
        if (self.porcentaje or self.porcentaje>0) and self.porcentaje<=100:
            self.adeudado=(self.monto_prestamo*self.porcentaje/100)+self.monto_prestamo
        if self.porcentaje==0 or self.porcentaje==0.00:
            self.adeudado=self.monto_prestamo
        if self.porcentaje<0:
            raise UserError(_(' El Porcentaje no puede ser Negativo'))
        if self.porcentaje>100:
            raise UserError(_(' El Porcentaje no puede ser ser mayor a 100%'))

    @api.onchange('cuotas','adeudado')
    def valor_cuotas(self):
        if self.cuotas>0 or self.cuotas:
            self.monto_cuotas=self.adeudado/self.cuotas
        if self.cuotas==0:
            raise UserError(_('El Número de cuotas no puede ser Nulo'))
        if self.cuotas<0:
            raise UserError(_('El Número de cuotas no puede ser Negativo'))

    @api.onchange('empleado_id')
    def compute_cedula(self):
        lista_empleado = self.env['hr.employee'].search([('id', '=', self.empleado_id.id)])
        if lista_empleado:
            for det in lista_empleado:
                if det.identification_id:
                    self.cedula=det.identification_id
                else:
                    self.cedula='00000000'
        if not lista_empleado:
            self.cedula='00000000'

    def aprobar(self):
        verifica_prestamo = self.env['hr.prestamo'].search([('empleado_id','=',self.empleado_id.id),('status_prestamo','=','pending')])
        if verifica_prestamo:
            raise ValidationError(_("Este empleado tiene un prestamo aun pendiente por pagar."))
        else:
            i=0
            pagos = self.env['hr.prestamo.line']
            for i in range(self.cuotas):
                num=i+1
                vals={
                'prestamo_id':self.id,
                'monto_pagado':0.00,
                'status_pago':"pending",
                'num_cuota':num,
                }
                pag = pagos.create(vals)
            self.status_prestamo='pending'

            empleado = self.env['hr.employee'].search([('id','=',self.empleado_id.id)])
            for det_empl in empleado:
                vals={
                'prestamo_id':self.id,
                'status_prestamo':"hold",
                'prestamo_activo':True,
                #'status_prestamo':self.status_prestamo,
                }
                self.env['hr.employee'].browse(det_empl.id).write(vals)


    def cancel(self):
        verifica=self.env['hr.employee'].search([('id','=',self.empleado_id.id),('status_prestamo','in',('granted','solvent'))])
        if verifica:
            raise ValidationError(_("Este empleado tiene un prestamo ya en ejecucion por nomina. No se puede realizar la accion solicitada"))
        pagos = self.env['hr.prestamo.line'].search([('prestamo_id','=',self.id)])
        pagos.unlink()
        self.status_prestamo='hold'

        empleado = self.env['hr.employee'].search([('id','=',self.empleado_id.id)])
        for det_empl in empleado:
            vals={
            'prestamo_id':self.id,
            'prestamo_activo':False,
            #'status_prestamo':self.status_prestamo,
            }
            self.env['hr.employee'].browse(det_empl.id).write(vals)


class SaleOrder(models.Model):
    _name = 'hr.prestamo.line'

    prestamo_id = fields.Many2one('hr.prestamo', string='Lineas de Prestamos')
    fecha_pago = fields.Date(string='Fecha del Pago')
    status_pago = fields.Selection(selection=[('pending','Pendiente'),('solvent','Solvente')],default='pending')
    monto_pagado = fields.Float(string='Monto Pagado')
    num_cuota = fields.Integer(string="#")
    payslip_id = fields.Integer(string="Id pago Individual")
    payslip_run_id = fields.Integer(string="Id pago por lote")
