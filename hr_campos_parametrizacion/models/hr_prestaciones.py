# coding: utf-8
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
import calendar
from odoo.exceptions import UserError, ValidationError

class hr_tiempo_servicio(models.Model):
    _name = 'hr.payroll.prestaciones'
    _description = 'Tabla de Prestaciones'

    company_id = fields.Many2one("res.company", string="Compañia", default=lambda self: self.env.company)
    employee_id=fields.Many2one("hr.employee",string="Empleado")
    ano= fields.Integer(string="Año")
    mes = fields.Integer(string='Meses Cumplido')
    nro_mes = fields.Integer(string="Nro mes Operacion")
    sueldo_base_mensual = fields.Float()
    sueldo_int_mensual = fields.Float()
    nro_ano = fields.Integer(string="Años Servicios")
    dias_disfrutes = fields.Integer(string='Dias de prestaciones')
    alicuota = fields.Float()

    dias_add_gps = fields.Integer(string="Dias Adicionales Gps")
    alicuota_add_gps = fields.Float()
    acumulado_add_gps = fields.Float()

    retiros = fields.Float()
    acumulado = fields.Float()
    tasa_int = fields.Float(string="Tasa BCV")
    monto_int= fields.Float(string="Monto")
    acumulado_int = fields.Float(string="Intereses Acumulados")

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    ultimo_suldo_base_mensual = fields.Float()
    sueldo_minimo_actual = fields.Float(compute='_compute_sueldo_minimo')

    def _compute_sueldo_minimo(self):
        sueldo_minimo=0
        indicador=self.env['hr.payroll.indicadores.economicos'].search([('code','=','SM')])
        if indicador:
            for det_in in indicador:
                sueldo_minimo=det_in.valor
        self.sueldo_minimo_actual=sueldo_minimo



    def action_payslip_done(self):
        #raise UserError(_('Prueba BEBE'))
        res = super(HrPayslip, self).action_payslip_done()
        cal=self.calculo_prestaciones()


    def calculo_prestaciones(self):
        if not self.company_id.tipo_metodo:
            raise UserError(_('Configure un tipo de metodo para el cálculo de prestaciones sociales de empleados para esta compañia'))
        if self.company_id.tipo_metodo=='tri':
            nro_dias_utilidades = 1
            if self.struct_id.activo_prestaciones==True:
                for selff in self:
                    sueldo_base_mensual=0.0001
                    nro_ano=dias_disfrutes=alicuota=acumulado=tasa_int=acumulado_int=0
                    mes=0
                    acumulado_add_gps=dias_add_gps=0
                    mes_nomina=selff.mes(selff.date_to)
                    ano_actual=selff.ano(selff.date_to)
                    valida=selff.env['hr.payroll.prestaciones'].search([('employee_id','=',selff.employee_id.id),('ano','=',ano_actual),('nro_mes','=',mes_nomina)])
                    if not valida:
                        if selff.contract_id.wage>0:
                            sueldo_base_mensual=selff.contract_id.wage
                            selff.ultimo_suldo_base_mensual=sueldo_base_mensual
                        if selff.tiempo_antiguedad>0:
                            nro_ano=selff.tiempo_antiguedad
                        indicadores=selff.env['hr.payroll.indicadores.economicos'].search([('code','=','DUT')])
                        if indicadores:
                            for det_indi in indicadores:
                                nro_dias_utilidades=det_indi.valor
                        indicadores2=selff.env['hr.payroll.indicadores.economicos'].search([('code','=','TP')])
                        if indicadores2:
                            for det_indi2 in indicadores2:
                                tasa_int=det_indi2.valor
                        verifica=selff.env['hr.payroll.prestaciones'].search([('employee_id','=',selff.employee_id.id),('id','!=',selff.id)],order="id ASC") #('ano','=',ano_actual)
                        if verifica:
                            #raise UserError(_('Ya hay una nomina procesada/pagada en el mes seleccionado para %s')%self.employee_id.name)
                            for det_v in verifica:
                                #acumulado=det_v.alicuota
                                if det_v.mes==11:
                                    mes=0
                                else:
                                    mes=det_v.mes+1
                        if mes==3 or mes==6 or mes==9:
                            dias_disfrutes=15
                        if mes==0:
                            busca_mes=selff.env['hr.payroll.prestaciones'].search([('employee_id','=',selff.employee_id.id),('mes','=','0'),('id','!=',selff.id)],order="mes ASC")
                            if busca_mes:
                                dias_disfrutes=15
                                dias_add_gps=selff.dias_por_antiguedad
                            if not busca_mes:
                                dias_disfrutes=0
                        if mes>0:
                            dias_add_gps=0
                        #if self.tiempo_antiguedad==0:
                            #dias_disfrutes=15
                        #if self.tiempo_antiguedad>0:
                            #dias_disfrutes=self.dias_vacaciones+1
                        sueldo_base_diario=sueldo_base_mensual/30
                        fraccion_diaria_vaca=sueldo_base_diario*selff.dias_vacaciones/360
                        fraccion_diaria_utilidades=sueldo_base_diario*nro_dias_utilidades/360
                        sueldo_integral_mensual=(sueldo_base_diario+fraccion_diaria_vaca+fraccion_diaria_utilidades)*30 # AQUI COLOCAR INASISTENCIA
                        
                        alicuota_add_gps=(sueldo_base_diario+fraccion_diaria_vaca+fraccion_diaria_utilidades)*dias_add_gps
                        acumulado_add_gps=selff.compute_acumulado_add_gps()+alicuota_add_gps

                        alicuota=(sueldo_integral_mensual/30)*dias_disfrutes
                        acumulado=selff.compute_acumulado()+alicuota

                        monto_int=(acumulado*tasa_int)/1200
                        acumulado_int=selff.compute_acumulado_int()+monto_int

                        ret = selff.env['hr.payroll.prestaciones']
                        values = {
                        'employee_id': selff.employee_id.id,
                        'sueldo_int_mensual':sueldo_integral_mensual,
                        'sueldo_base_mensual':sueldo_base_mensual,
                        'nro_ano':nro_ano,
                        'mes':mes,
                        'nro_mes':mes_nomina,
                        'ano':selff.ano(selff.date_to),
                        'dias_disfrutes':dias_disfrutes,
                        'alicuota':alicuota,
                        'acumulado':acumulado,
                        'tasa_int':tasa_int,
                        'monto_int':monto_int,
                        'acumulado_int':acumulado_int,
                        'dias_add_gps':dias_add_gps,
                        'alicuota_add_gps':alicuota_add_gps,
                        'acumulado_add_gps':acumulado_add_gps,
                        }
                        rets=ret.create(values)

    def compute_acumulado(self):
        acum=0
        lista=self.env['hr.payroll.prestaciones'].search([('employee_id','=',self.employee_id.id),('id','!=',self.id),('nro_mes','!=',self.mes(self.date_to))])
        if lista:
            for det in lista:
                acum=acum+det.alicuota
        return acum

    def compute_acumulado_add_gps(self):
        acum=0
        lista=self.env['hr.payroll.prestaciones'].search([('employee_id','=',self.employee_id.id),('id','!=',self.id),('nro_mes','!=',self.mes(self.date_to))])
        if lista:
            for det in lista:
                acum=acum+det.alicuota_add_gps
        return acum

    def compute_acumulado_int(self):
        acum=0
        lista=self.env['hr.payroll.prestaciones'].search([('employee_id','=',self.employee_id.id),('id','!=',self.id),('nro_mes','!=',self.mes(self.date_to))])
        if lista:
            for det in lista:
                acum=acum+det.monto_int
        return acum


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

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    acumulado = fields.Float(compute='_compute_acumulado')
    acumulado_gps = fields.Float(compute='_compute_acumulado_gps')
    disponible = fields.Float(compute='_compute_disponible')
    tasa_int = fields.Float(compute='_compute_tasa_bcv')
    acumulado_int = fields.Float(compute='_compute_acumulado_int')
    custom_currency_id = fields.Many2one(
        'res.currency', 
        default=lambda self: self.env.user.company_id.currency_id, 
        string='Currency', 
        readonly=True
    )

    def _compute_acumulado(self):
        acum=0
        lista=self.env['hr.payroll.prestaciones'].search([('employee_id','=',self.id)])
        if lista:
            for det in lista:
                acum=acum+det.alicuota
        self.acumulado=acum

    def _compute_acumulado_gps(self):
        acum=0
        lista=self.env['hr.payroll.prestaciones'].search([('employee_id','=',self.id)])
        if lista:
            for det in lista:
                acum=acum+det.alicuota_add_gps
        self.acumulado_gps=acum

    def _compute_acumulado_int(self):
        acum_int=0
        lista=self.env['hr.payroll.prestaciones'].search([('employee_id','=',self.id)])
        if lista:
            for det in lista:
                acum_int=acum_int+det.monto_int
        self.acumulado_int=acum_int

    def _compute_tasa_bcv(self):
        tasa_int=0
        indicador=self.env['hr.payroll.indicadores.economicos'].search([('code','=','TP')])
        if indicador:
            for det in indicador:
                tasa_int=det.valor
        self.tasa_int=tasa_int

    def _compute_disponible(self):
        acum=0
        acum_prestamo=0
        lista=self.env['hr.payroll.prestaciones'].search([('employee_id','=',self.id)])
        if lista:
            for det in lista:
                acum=acum+det.alicuota
                acum_prestamo=acum_prestamo+det.retiros
        total=(acum-acum_prestamo)*75/100

        self.disponible=total
