# coding: utf-8
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
import calendar
from odoo.exceptions import UserError, ValidationError

class hr_payroll_hollydays(models.Model):
    _name = 'hr.payroll.hollydays'
    _description = 'Dias Feriados'

    hollydays = fields.Boolean('Dias')
    nombre = fields.Char('Motivo del dia Festivo', size=256, required=True)
    date_from = fields.Date('Desde', required=True)
    date_to = fields.Date('Hasta')

    @api.onchange('date_from')
    def onchange_date_from(self):
        if not self.hollydays:
            self.date_to = self.date_from

    @api.onchange('hollydays')
    def onchange_date_hollydays(self):
        if not self.hollydays:
            self.date_to = self.date_from

class hr_special_days(models.Model):
    _inherit = 'hr.payslip'

    saturdays = fields.Integer('Sabados', compute='_compute_fin_semana', store=True, readonly=True)
    sundays = fields.Integer('Domingos', compute='_compute_fin_semana', store=True, readonly=True)
    saturdays_sundays_vac = fields.Integer(compute='_compute_cant_sab_dom_vac_nom') # nuevo
    mondays = fields.Integer('Nro lunes', compute='_compute_days', help='este campo trae el numero de lunes',store=True, readonly=True)
    mondays_activo = fields.Integer('Nro lunes Activo', compute='_compute_mondays_activo', help='este campo trae el numero de lunes activos o laborales',store=True, readonly=True) # nuevo2
    workdays_periodo = fields.Integer('Dias Laborales del Período',compute='_compute_days') #nuevo
    workdays_periodo2 = fields.Integer('Dias Laborales del Período',compute='_compute_dias_periodo') #nuevo2
    saturdays_sundays_act = fields.Integer(compute='_compute_cant_sab_dom_act') # nuevo2

    workdays = fields.Integer('Dias Laborales Activos', help='este campo los dias habiles del periodo', compute='_compute_workdays',
                             store=True, readonly=True) #nuevo2
    holydays = fields.Integer('Dias Festivos', compute='_compute_days', readonly=True)
    hollydays_str = fields.Integer('Descansos Trabajados', compute='_compute_desfer_laborados')
    hollydays_ftr = fields.Integer('Feriados Trabajados', compute='_compute_desfer_laborados')
    days_attended = fields.Integer(string='Días asistidos', compute='_compute_days_attended')
    days_inasisti = fields.Integer(string='Dias Inasistidos', compute='_compute_days_inasisti')#odoo 14

    horas_extras_diurnas = fields.Float(compute='_compute_horas_extras_diurnas')
    horas_extras_nocturnas = fields.Float()

    tiempo_antiguedad = fields.Integer(compute='_compute_tiempo_antiguedad')
    dias_vacaciones = fields.Integer(compute='_compute_dias_vacaciones')

    sueldo_anterior_mes = fields.Float(compute='_compute_sueldo_mes_anterior')
    dias_utilidades = fields.Integer(compute='_compute_dias_utilidades', store=True) # nuevo2
    dias_por_antiguedad = fields.Integer(compute='compute_dias_por_ano_antiguedad')

    # PERMISOS Y AUSENCIAS 
    dias_permiso_remunerado = fields.Float(compute='_compute_dias')
    dias_no_remunerado = fields.Float(compute='_compute_dias')
    dias_ausencia_injus = fields.Integer(compute='_compute_dias')
    dias_vacaciones_pedidas = fields.Integer(compute='_compute_dias')
    dias_vacaciones_en_nomina = fields.Integer(compute='_compute_cant_vac_nom') #nuevo2

    dias_reposo_medico_lab = fields.Integer(compute='_compute_permiso')
    dias_reposo_medico = fields.Integer(compute='_compute_permiso')
    dias_pos_natal = fields.Integer(compute='_compute_permiso')
    dias_peternidad = fields.Integer(compute='_compute_permiso')

    ########################33 CAMPO PARA ABONOS ADICIONALES ###############################
    abono_check = fields.Boolean(default=False, string="Monto Abonos adicionales")
    abono_value = fields.Float(default=0)
    ########################33 CAMPO PARA DEDUCCIONES ADICIONALES ###############################
    salary_deduction_check = fields.Boolean(default=False, string="Monto Deducciones")
    salary_deduction_value = fields.Float(default=0)
    deduction_sc_check = fields.Boolean(default=False, string="Deducciones sin cobrar")
    deduction_sc_value = fields.Float(default=0)
    ########################33 dias pendientes ADICIONALES ###############################
    dias_pend_check = fields.Boolean(default=False, string="Dias pendientes por pagar")
    dias_pen_d_value = fields.Float(default=1)
    ####################### descuento por prestamos ########################
    habilitar_des_pres = fields.Boolean(default=False)
    custom_rate = fields.Boolean(default=True)
    os_currecy_rate = fields.Float(default=1)
    monto = fields.Float()
    monto_bs = fields.Float()
    currency_pres_id = fields.Many2one('res.currency', default=2)
    ########################33 CAMPO PARA DEDUCCIONES DE ANTICIPOS POR VACACIONES ###############################
    anticipo_vac_check = fields.Boolean(default=False, string="Anticipos de Vacaciones")
    anticipo_vac_value = fields.Float(default=1)
    #################### ADICIONALES ############
    #fecha_hoy = fields.Date(compute='_compute_hoy')

    fecha_hoy = fields.Date(default=lambda *a:datetime.now().strftime('%Y-%m-%d'),readonly=True) # ojo
    fecha_aux_util = fields.Date() # nuevo2

    custom_rate_gene = fields.Boolean(default=False)
    os_currecy_rate_gene = fields.Float(digits=(12, 4))
    os_currecy_rate_gene_aux = fields.Float(compute='_compute_tasa_odoo',digits=(12, 4))
    ################### DIAS POR DIFERENCIA DE EGRESO O INGRESO ########
    dif_dias_ingreso = fields.Integer(compute='_compute_dif_ingreso') # nuevo2
    dif_dias_egreso = fields.Integer(compute='_compute_dif_egreso') # nuevo2

    ################ Sueldo mensual a la fecha de pago ###########
    sueldo=fields.Monetary(compute='_compute_sueldo',store=True) #nuev2

    @api.depends('employee_id') # nuevo2
    def _compute_sueldo(self):
        for selff in self:
            if selff.employee_id.contract_id.wage:
                selff.sueldo=selff.employee_id.contract_id.wage
            else:selff.sueldo=0


    def recalcular_nom(self):
        self.compute_sheet()

    @api.depends('date_from','date_to','employee_id') # nuevo2
    def _compute_dif_ingreso(self):
        for selff in self:
            delta=0
            if selff.contract_id.date_start and selff.contract_id.date_start>=selff.date_from:
                delta=selff.days_dife(selff.date_from,selff.contract_id.date_start)
            
            selff.dif_dias_ingreso=delta

    @api.depends('date_from','date_to','employee_id') # nuevo2
    def _compute_dif_egreso(self):
        for selff in self:
            beta=0
            if selff.contract_id.date_end:
                if selff.contract_id.date_end<=selff.date_to: 
                    beta=selff.days_dife(selff.contract_id.date_end,selff.date_to)
            selff.dif_dias_egreso=beta

    @api.depends('date_from', 'date_to') # nuevo2
    def _compute_dias_periodo(self):
        valor=0
        for selff in self:
            if selff.company_id.tipo_dif_dias=="fech_con":
                if selff.struct_id.shedule_pay_value==15:
                    valor=11-selff.valida_cant_dia_feriado(selff.date_from,selff.date_to)
                if selff.struct_id.shedule_pay_value==30:
                    valor=22-selff.valida_cant_dia_feriado(selff.date_from,selff.date_to)
                if selff.struct_id.shedule_pay_value==7:
                    valor=5-selff.valida_cant_dia_feriado(selff.date_from,selff.date_to)
            selff.workdays_periodo2=valor

    @api.depends('date_from','date_to','employee_id') # nuevo2 *
    def _compute_mondays_activo(self):
        if self.struct_id.tipo_struct!='vac':
            for selff in self:
                nro_lunes=nro_lunes_no_activo=0
                rango_dias=selff.days_dife(selff.date_from,selff.date_to)
                dia_in=selff.dia(selff.date_from)
                mes_in=selff.mes(selff.date_from)
                ano_in=selff.ano(selff.date_from)
                dia=dia_in
                i=0
                for i in range(rango_dias+1):
                    dia_aux=10
                    dia_aux=calendar.weekday(ano_in,mes_in,dia+i)
                    if dia_aux==0:
                        nro_lunes=nro_lunes+1

                op1=selff.env['hr.leave'].search([('holiday_status_id.code','=','VAC'),('employee_id','=',selff.employee_id.id),('state','=','validate'),('request_date_to','>=',selff.date_from),('request_date_to','<=',selff.date_to)])
                op2=selff.env['hr.leave'].search([('holiday_status_id.code','=','VAC'),('employee_id','=',selff.employee_id.id),('state','=','validate'),('request_date_from','<=',selff.date_to),('request_date_from','>=',selff.date_from)])
                op3=selff.env['hr.leave'].search([('holiday_status_id.code','=','VAC'),('employee_id','=',selff.employee_id.id),('state','=','validate'),('request_date_from','<',selff.date_from),('request_date_to','>',selff.date_to)])
                # regresa de vacaciones
                if op1:
                    for det in op1:
                        #raise UserError(_('op=%s')%op1)
                        delta=selff.days_dife(det.request_date_to,selff.date_to)
                        #raise UserError(_('op=%s')%delta)
                        dia_in=selff.dia(det.request_date_to)
                        mes_in=selff.mes(det.request_date_to)
                        ano_in=selff.ano(det.request_date_to)
                        dia=dia_in
                        j=0
                        for j in range(delta+1):
                            dia_auxx=10
                            dia_auxx=calendar.weekday(ano_in,mes_in,dia+j)
                            if dia_auxx==0:
                                nro_lunes_no_activo=nro_lunes_no_activo+1
                        nro_lunes=0
                                #raise UserError(_('aux=%s')%dia_auxx)
                # SALE A VACACIONES
                if op2:
                    for det in op2:
                        delta=selff.days_dife(selff.date_from,det.request_date_from)
                        dia_in=selff.dia(selff.date_from)
                        mes_in=selff.mes(selff.date_from)
                        ano_in=selff.ano(selff.date_from)
                        dia=dia_in
                        j=0
                        for j in range(delta):
                            dia_auxx=10
                            dia_auxx=calendar.weekday(ano_in,mes_in,dia+j)
                            if dia_auxx==0:
                                nro_lunes_no_activo=nro_lunes_no_activo+1
                        nro_lunes=0

                if op3:
                    nro_lunes_no_activo=nro_lunes=0

                #verifica si hay inicio de contrato
                if selff.contract_id.date_start and selff.contract_id.date_start>=selff.date_from:
                    delta=selff.days_dife(selff.contract_id.date_start,selff.date_to)
                    rango=delta
                    dia_in=selff.dia(selff.contract_id.date_start)
                    mes_in=selff.mes(selff.contract_id.date_start)
                    ano_in=selff.ano(selff.contract_id.date_start)
                    dia=dia_in
                    k=0 
                    #raise UserError(_('delta=%s')%delta)
                    for k in range(rango+1):
                        dia_ayu=10
                        dia_ayu=calendar.weekday(ano_in,mes_in,dia+k)
                        if dia_ayu==0:
                            nro_lunes_no_activo=nro_lunes_no_activo+1
                    nro_lunes=0
                    #raise UserError(_('nro_lunes_no_activo=%s')%(dia+k))
                # verifica si hay un contranto por vencer
                if selff.contract_id.date_end:
                    if selff.contract_id.date_end<=selff.date_to: 
                        nro_lunes_no_activo=0
                        delta=selff.days_dife(selff.date_from,selff.contract_id.date_end)
                        dia_in=selff.dia(selff.date_from)
                        mes_in=selff.mes(selff.date_from)
                        ano_in=selff.ano(selff.date_from)
                        dia=dia_in
                        w=0
                        for w in range(delta+1):
                            dia_ayuu=10
                            dia_ayuu=calendar.weekday(ano_in,mes_in,dia+w)
                            if dia_ayuu==0:
                                nro_lunes_no_activo=nro_lunes_no_activo+1
                        nro_lunes=0

                #selff.mondays_activo=nro_lunes_no_activo
                selff.mondays_activo=abs(nro_lunes-nro_lunes_no_activo)
        else:
            for selff in self:
                selff.mondays_activo=0


    @api.depends('date_from','date_to','employee_id') # nuevo2
    def _compute_fin_semana(self):
        for selff in self:
            dia_in=selff.dia(selff.date_from)
            mes_in=selff.mes(selff.date_from)
            ano_in=selff.ano(selff.date_from)
            i=dia_in-1
            i=sabado=domingo=0
            if selff.company_id.tipo_dif_dias=="fech_cal":
                diferencia=selff.days_dife(selff.date_from,selff.date_to)
                for i in range(diferencia+1):
                    dia_aux=0
                    dia_aux=calendar.weekday(ano_in,mes_in,i+1)
                    if dia_aux==5:
                        sabado=sabado+1
                    if dia_aux==6:
                        domingo=domingo+1
            if selff.company_id.tipo_dif_dias=="fech_con":
                if selff.struct_id.shedule_pay_value==30:
                    sabado=4
                    domingo=4
                if selff.struct_id.shedule_pay_value==15:
                    sabado=2
                    domingo=2
                if selff.struct_id.shedule_pay_value==7:
                    sabado=1
                    domingo=1
            selff.saturdays=sabado
            selff.sundays=domingo

    """@api.depends('date_from','date_to','employee_id') # nuevo2 antiguo
    def _compute_workdays(self):
        for selff in self:
            diferencia=diferencia_2=0
            ban_vac=ban_contr=0
            op1=selff.env['hr.leave'].search([('holiday_status_id.code','=','VAC'),('employee_id','=',selff.employee_id.id),('state','=','validate'),('request_date_to','>=',selff.date_from),('request_date_to','<=',selff.date_to)])
            op2=selff.env['hr.leave'].search([('holiday_status_id.code','=','VAC'),('employee_id','=',selff.employee_id.id),('state','=','validate'),('request_date_from','<=',selff.date_to),('request_date_from','>=',selff.date_from)])
            if op1:
                #raise UserError(_('op=%s')%op1)
                for det in op1: # aqui viene de vacaciones
                    diferencia=selff.days_dife(selff.date_to,det.request_date_to)-selff.holydays-(selff.saturdays+selff.sundays)
                    ban_vac=1
                    #raise UserError(_('op=%s')%diferencia)
            if op2:
                #raise UserError(_('op=%s')%op2)
                for det in op2: # aqui sale a vacaciones
                    #diferencia=selff.days_dife(det.request_date_from,selff.date_to)-selff.holydays
                    diferencia=selff.days_dife(selff.date_from,det.request_date_from)-selff.holydays-(selff.saturdays+selff.sundays)
                    ban_vac=1
            if ban_vac==0: # aqui no tiene vacaciones
                if selff.contract_id.date_start and selff.contract_id.date_start>=selff.date_from: # aqui si ingreso en un periodo de nomina
                    dia_in=selff.dia(selff.contract_id.date_start)
                    mes_in=selff.mes(selff.contract_id.date_start)
                    ano_in=selff.ano(selff.contract_id.date_start)
                    ban_contr=1
                    i=dia_in-1
                    diferencia_2=selff.days_dife(selff.date_from,selff.contract_id.date_start)
                    if selff.company_id.tipo_dif_dias=="fech_cal":
                        for i in range(diferencia_2+1):
                                dia_aux=0
                                dia_aux=calendar.weekday(ano_in,mes_in,i+1)
                                if dia_aux==5:
                                    diferencia_2=diferencia_2-1
                                if dia_aux==6:
                                    diferencia_2=diferencia_2-1

                if selff.contract_id.date_end:
                    if selff.contract_id.date_end<=selff.date_to: 
                        ban_contr=1
                        diferencia_2=selff.days_dife(selff.date_from,selff.contract_id.date_end)
                        

            if selff.company_id.tipo_dif_dias=="fech_cal":
                #diferencia=selff.days_dife(selff.date_from,selff.date_to)+1-selff.holydays-selff.saturdays-selff.sundays#-diferencia_2
                diferencia=selff.days_dife(selff.date_from,selff.date_to)+1-(selff.saturdays+selff.sundays)-selff.holydays-diferencia_2
            if selff.company_id.tipo_dif_dias=="fech_con":
                dia=selff.struct_id.shedule_pay_value
                diferencia=dia-(selff.holydays+selff.saturdays+selff.sundays)-diferencia_2

            

            if diferencia>0:
                selff.workdays=diferencia #+2 # ojo cambiar despues
            if diferencia==0:
                selff.workdays=diferencia"""

    @api.depends('date_from','date_to','employee_id') # nuevo2 *
    def _compute_workdays(self):
        for selff in self:
            diferencia=diferencia_2=0
            ban_vac=ban_contr=0
            # INICIALMENTE SE ASUME UN PERIODO COMPLETO SIN VACACIONES Y SIN INGRESO O EGRESO DE PERSONAL
            if selff.company_id.tipo_dif_dias=="fech_con" :
                dia=selff.struct_id.shedule_pay_value
                diferencia=dia-(selff.holydays+selff.saturdays+selff.sundays) 
            if selff.company_id.tipo_dif_dias=="fech_cal" :
                #diferencia=selff.days_dife(selff.date_from,selff.date_to)+1-selff.holydays-selff.saturdays-selff.sundays#-diferencia_2
                diferencia=selff.days_dife(selff.date_from,selff.date_to)-(selff.saturdays+selff.sundays)-selff.holydays#-1    

            # AHORA SE VALIDA SI HAY VACACIONES
            op1=selff.env['hr.leave'].search([('holiday_status_id.code','=','VAC'),('employee_id','=',selff.employee_id.id),('state','=','validate'),('request_date_to','>=',selff.date_from),('request_date_to','<=',selff.date_to)])
            op2=selff.env['hr.leave'].search([('holiday_status_id.code','=','VAC'),('employee_id','=',selff.employee_id.id),('state','=','validate'),('request_date_from','<=',selff.date_to),('request_date_from','>=',selff.date_from)])
            op3=selff.env['hr.leave'].search([('holiday_status_id.code','=','VAC'),('employee_id','=',selff.employee_id.id),('state','=','validate'),('request_date_from','<',selff.date_from),('request_date_to','>',selff.date_to)])
            if op1:
                for det in op1: # aqui regresa de vacaciones
                    diferencia=selff.days_dife(det.request_date_to,selff.date_to)-selff.resta_dia_31(selff.date_to)-selff.saturdays_sundays_act #-selff.holydays-(selff.saturdays+selff.sundays-selff.saturdays_sundays_vac)
                    ban_vac=1
            if op2:
                for det in op2: # aqui se va de vacaciones
                    diferencia=selff.days_dife(selff.date_from,det.request_date_from)-selff.saturdays_sundays_act#-(selff.saturdays+selff.sundays-selff.saturdays_sundays_vac)
                    """if selff.company_id.tipo_dif_dias=="fech_cal":
                        diferencia=selff.days_dife(selff.date_from,det.request_date_from)-(selff.saturdays+selff.sundays-selff.saturdays_sundays_vac)
                    if selff.company_id.tipo_dif_dias=="fech_con":
                        diferencia=selff.struct_id.shedule_pay_value-(selff.days_dife(selff.date_to,det.request_date_from)+1)-(selff.saturdays+selff.sundays-selff.saturdays_sundays_vac)"""
                    ban_vac=1

            if op3:
                #raise UserError(_('op3=%s')%op3)
                diferencia=0
                """for det in op3:
                    diferencia=selff.days_dife(selff.date_from,selff.date_from)-(selff.saturdays+selff.sundays-selff.saturdays_sundays_vac)
                    if diferencia<0:
                        diferencia=0"""
            ##  AHORA VALIDA SI HAY INICIO O CULMINACION DE CONTRATO
            #### VALIDA SI HAY UN CONTRATO INICIANDO
            if selff.contract_id.date_start and selff.contract_id.date_start>=selff.date_from:

                dia_in=selff.dia(selff.contract_id.date_start)
                mes_in=selff.mes(selff.contract_id.date_start)
                ano_in=selff.ano(selff.contract_id.date_start)
                dia=dia_in
                i=0
                rango=selff.days_dife(selff.contract_id.date_start,selff.date_to)
                #raise UserError(_('rango=%s')%rango)
                diferencia_2=rango+1
                for i in range(rango+1):
                    dia_aux=0
                    dia_aux=calendar.weekday(ano_in,mes_in,dia+i)
                    if dia_aux==5:
                        diferencia_2=diferencia_2-1
                    if dia_aux==6:
                        diferencia_2=diferencia_2-1
                diferencia=diferencia_2-1*selff.valida_cant_dia_feriado(selff.contract_id.date_start,selff.date_to)-1*selff.resta_dia_31(selff.date_to)

                


            #### VALIDA SI HAY UN CONTRATO POR CULMINAR
            if selff.contract_id.date_end:
                if selff.contract_id.date_end<=selff.date_to:
                    dia_in=selff.dia(selff.date_from)
                    mes_in=selff.mes(selff.date_from)
                    ano_in=selff.ano(selff.date_from)
                    dia=dia_in
                    i=0
                    rango=selff.days_dife(selff.date_from,selff.contract_id.date_end)
                    diferencia_2=rango+1
                    for i in range(rango+1):
                        dia_aux=0
                        dia_aux=calendar.weekday(ano_in,mes_in,dia+i)
                        if dia_aux==5:
                            diferencia_2=diferencia_2-1
                        if dia_aux==6:
                            diferencia_2=diferencia_2-1

                    diferencia=diferencia_2

            
            selff.workdays=diferencia #diferencia_2

    # nuevo 2
    def resta_dia_31(self,date):
        fecha = str(date)
        #fecha = date
        fecha_aux=fecha
        dia=fecha[8:10]  
        #raise UserError(_('dia=%s')%dia)
        if dia=='31':
            resultado=1
        else:
            resultado=0
        #resultado=1
        return resultado


    ## nuevo 2
    def valida_cant_dia_feriado(self,fecha_inc,fecha_fin):
        cont=0
        busca=self.env['hr.payroll.hollydays'].search([('date_from','>=',fecha_inc),('date_to','<=',fecha_fin),('hollydays','=',True)])
        if busca:
            cont=cont+1
        return cont

    @api.depends('date_from','date_to','employee_id') # nuevo2
    def _compute_cant_sab_dom_act(self):
        cant_act=0
        for selff in self:
            dia=selff.struct_id.shedule_pay_value
            if dia==15:
                cant_act=4
            if dia==30:
                cant_act=8
            if dia==7:
                cant_act=2
            #verifica si hay inicio de contrato
            if selff.contract_id.date_start and selff.contract_id.date_start>=selff.date_from:
                nro_fin_act=0
                delta=selff.days_dife(selff.contract_id.date_start,selff.date_to)
                rango=delta
                dia_in=selff.dia(selff.contract_id.date_start)
                mes_in=selff.mes(selff.contract_id.date_start)
                ano_in=selff.ano(selff.contract_id.date_start)
                dia=dia_in
                k=0 
                for k in range(rango+1):
                    dia_ayu=0
                    dia_ayu=calendar.weekday(ano_in,mes_in,dia+k)
                    if dia_ayu==5 or dia_ayu==6:
                        nro_fin_act=nro_fin_act+1
                cant_act=nro_fin_act

            # verifica si hay un contranto por vencer
            if selff.contract_id.date_end:
                if selff.contract_id.date_end<=selff.date_to:
                    nro_fin_act=0
                    delta=selff.days_dife(selff.date_from,selff.contract_id.date_end)
                    dia_in=selff.dia(selff.date_from)
                    mes_in=selff.mes(selff.date_from)
                    ano_in=selff.ano(selff.date_from)
                    dia=dia_in
                    w=0
                    for w in range(delta+1):
                        dia_ayuu=0
                        dia_ayuu=calendar.weekday(ano_in,mes_in,dia+w)
                        if dia_ayuu==5 or dia_ayuu==6:
                            nro_fin_act=nro_fin_act+1
                    cant_act=nro_fin_act

            # verifica si hay vacaciones
            op1=selff.env['hr.leave'].search([('holiday_status_id.code','=','VAC'),('employee_id','=',selff.employee_id.id),('state','=','validate'),('request_date_to','>=',selff.date_from),('request_date_to','<=',selff.date_to)]) # aqui regresa de vacaciones
            op2=selff.env['hr.leave'].search([('holiday_status_id.code','=','VAC'),('employee_id','=',selff.employee_id.id),('state','=','validate'),('request_date_from','<=',selff.date_to),('request_date_from','>=',selff.date_from)]) # sale a vacaciones
            op3=selff.env['hr.leave'].search([('holiday_status_id.code','=','VAC'),('employee_id','=',selff.employee_id.id),('state','=','validate'),('request_date_from','<',selff.date_from),('request_date_to','>',selff.date_to)]) # si en tod la nomina esta de vacaciones aun
            
            if op1:
                cant_act=0
                for det in op1:
                    delta=selff.days_dife(det.request_date_to,selff.date_to)-1
                    dia_in=selff.dia(det.request_date_to)+1
                    mes_in=selff.mes(det.request_date_to)
                    ano_in=selff.ano(det.request_date_to)
                    dia=dia_in
                    j=0
                    for j in range(delta+1):
                        dia_auxx=0
                        dia_auxx=calendar.weekday(ano_in,mes_in,dia+j)
                        if dia_auxx in (5,6):
                            cant_act=cant_act+1

            if op2:
                cant_act=0
                for det in op2:
                    delta=selff.days_dife(selff.date_from,det.request_date_from)-1
                    dia_in=selff.dia(selff.date_from)
                    mes_in=selff.mes(selff.date_from)
                    ano_in=selff.ano(selff.date_from)
                    dia=dia_in
                    j=0
                    for j in range(delta+1):
                        dia_aux=0
                        dia_auxx=calendar.weekday(ano_in,mes_in,dia+j)
                        if dia_auxx in (5,6):
                            cant_act=cant_act+1 #dar33

            if op3:
                cant_act=0


            selff.saturdays_sundays_act=cant_act




    @api.depends('date_from','date_to','employee_id') # nuevo2 *
    def _compute_cant_sab_dom_vac_nom(self):
        for selff in self: 
            if selff.struct_id.tipo_struct!="vac":
                i=0
                diferencia=saturdays=sundays=0 
                op1=selff.env['hr.leave'].search([('holiday_status_id.code','=','VAC'),('employee_id','=',selff.employee_id.id),('state','=','validate'),('request_date_to','>=',selff.date_from),('request_date_to','<=',selff.date_to)])
                op2=selff.env['hr.leave'].search([('holiday_status_id.code','=','VAC'),('employee_id','=',selff.employee_id.id),('state','=','validate'),('request_date_from','<=',selff.date_to),('request_date_from','>=',selff.date_from)])
                op3=selff.env['hr.leave'].search([('holiday_status_id.code','=','VAC'),('employee_id','=',selff.employee_id.id),('state','=','validate'),('request_date_from','<',selff.date_from),('request_date_to','>',selff.date_to)])
                op=""
                if op1:
                    for det in op1:
                        dia_in=selff.dia(selff.date_from)
                        mes_in=selff.mes(selff.date_from)
                        ano_in=selff.ano(selff.date_from)
                        i=0
                        dia=dia_in
                        diferencia=selff.days_dife(selff.date_from,det.request_date_to)
                        for i in range(diferencia+1):
                            dia_aux=0
                            dia_aux=calendar.weekday(ano_in,mes_in,dia+i)
                            if dia_aux==5:
                                saturdays=saturdays+1
                            if dia_aux==6:
                                sundays=sundays+1
                if op2:
                    for det in op2:
                        dia_in=selff.dia(det.request_date_from)
                        mes_in=selff.mes(det.request_date_from)
                        ano_in=selff.ano(det.request_date_from)
                        i=0
                        dia=dia_in
                        diferencia=selff.days_dife(det.request_date_from,selff.date_to)
                        for i in range(diferencia+1):
                            dia_aux=0
                            dia_aux=calendar.weekday(ano_in,mes_in,dia+i)
                            if dia_aux==5:
                                saturdays=saturdays+1
                            if dia_aux==6:
                                sundays=sundays+1

                if op3:
                    for det in op3:
                        dia_in=selff.dia(selff.date_from)
                        mes_in=selff.mes(selff.date_from)
                        ano_in=selff.ano(selff.date_from)
                        i=0
                        dia=dia_in
                        diferencia=selff.days_dife(selff.date_from,selff.date_to)
                        for i in range(diferencia+1):
                            dia_aux=0
                            dia_aux=calendar.weekday(ano_in,mes_in,dia+i)
                            if dia_aux==5:
                                saturdays=saturdays+1
                            if dia_aux==6:
                                sundays=sundays+1

                selff.saturdays_sundays_vac=sundays+saturdays

            if selff.struct_id.tipo_struct=='vac':
                diferencia=saturdays=sundays=0
                dia_in=selff.dia(selff.date_from)
                mes_in=selff.mes(selff.date_from)
                ano_in=selff.ano(selff.date_from)
                i=0
                dia=dia_in
                diferencia=selff.days_dife(selff.date_from,selff.date_to)
                for i in range(diferencia+1):
                    dia_aux=0
                    dia_aux=calendar.weekday(ano_in,mes_in,dia+i)
                    if dia_aux==5:
                        saturdays=saturdays+1
                    if dia_aux==6:
                        sundays=sundays+1
                    ultimo_dia=selff.dia_mes_ultimo(mes_in)
                    if (dia+i)>=ultimo_dia:# adaptacion calendar
                        dia=-1*i
                        mes_in=mes_in+1
                        #raise UserError(_('i=%s')%i)
                selff.saturdays_sundays_vac=saturdays+sundays

            if not selff.struct_id.tipo_struct:
                selff.saturdays_sundays_vac=0
                

    def dia_mes_ultimo(self,mes): # nuevo2
        if mes==1:
            valor=31
        if mes==2:
            valor=28
        if mes==3:
            valor=31
        if mes==4:
            valor=30
        if mes==5:
            valor=31
        if mes==6:
            valor=30
        if mes==7:
            valor=31
        if mes==8:
            valor=31
        if mes==9:
            valor=30
        if mes==10:
            valor=31
        if mes ==11:
            valor=30
        if mes==12:
            valor=31
        return valor

    @api.depends('date_from','date_to','employee_id') # nuevo2 *
    def _compute_cant_vac_nom(self):
        for selff in self: 
            diferencia=0 
            # AQUI SALE ANTES DE LA NOMINA Y SE REINTEGRA A MITAD DE NOMINA
            op1=selff.env['hr.leave'].search([('holiday_status_id.code','=','VAC'),('employee_id','=',selff.employee_id.id),('state','=','validate'),('request_date_to','>=',selff.date_from),('request_date_to','<=',selff.date_to)])

            # AQUI SALE EN MITAD DE LA NOMINA Y REGRESA PASADO LA NOMINA
            op2=selff.env['hr.leave'].search([('holiday_status_id.code','=','VAC'),('employee_id','=',selff.employee_id.id),('state','=','validate'),('request_date_from','<=',selff.date_to),('request_date_from','>=',selff.date_from)])

            op3=selff.env['hr.leave'].search([('holiday_status_id.code','=','VAC'),('employee_id','=',selff.employee_id.id),('state','=','validate'),('request_date_from','<=',selff.date_from),('request_date_to','>=',selff.date_to)])
            #raise UserError(_('op1=%s y op2=%s')%(op1,op2))
            op=""
            if op1:
                for det in op1:
                    diferencia=selff.days_dife(selff.date_from,det.request_date_to)+1
            if op2:
                for det in op2:
                    diferencia=selff.days_dife(det.request_date_from,selff.date_to)+1
            if op3:
                for det in op3:
                    diferencia=selff.days_dife(selff.date_from,selff.date_to)+1
            if diferencia>0:
                selff.dias_vacaciones_en_nomina=diferencia
            if diferencia==0:
                selff.dias_vacaciones_en_nomina=diferencia



    @api.onchange('employee_id','currecy_rate_gene')
    def _compute_tasa_odoo(self):
        valor=1
        lista_tasa = self.env['res.currency.rate'].search([('currency_id', '=', 2),('name','<=',self.fecha_hoy)],order='name ASC')
        if lista_tasa:
            for det in lista_tasa:
                if det.rate:
                    valor=det.inverse_company_rate
        self.os_currecy_rate_gene_aux=valor
        if self.custom_rate_gene!=True:
            self.os_currecy_rate_gene=valor

    

    @api.onchange('os_currecy_rate_gene')
    def valida_valor_tasa_nula(self):
        if self.os_currecy_rate_gene==0 or self.os_currecy_rate_gene<0:
            raise UserError(_('Valor de la tasa no puede ser nula o negativa'))

    ######### FUNCION QUE COLOCA LA TASA PERSONALIZADA EN EL ASIENTO CONTABLE
    def action_payslip_done(self):
        super().action_payslip_done()
        #raise UserError(_('asiento=%s')%self.move_id.id)
        for roc in self:
            roc.valida_pago_repetido()
            roc.move_id.custom_rate=roc.custom_rate_gene
            roc.move_id.os_currency_rate=roc.os_currecy_rate_gene

    #@api.onchange('employee_id') # ojo
    #def _compute_hoy(self):
        #for selff in self:
            #hoy=datetime.now().strftime('%Y-%m-%d')
            #selff.fecha_hoy=hoy

    ############## FUNCION QUER VALIDA QUE A UN EMPLEADO NO SE LE PAGUE UNA NOMINA 2 VECES EN UN MISMO PERIODO
    def valida_pago_repetido(self):
        rastrea=self.env['hr.payslip'].search([('employee_id','=',self.employee_id.id),('struct_id','=',self.struct_id.id),('date_from','<=',self.date_from),('date_to','>=',self.date_from),('id','!=',self.id)])
        if rastrea:
            raise UserError(_('No se puede procesar esta nomina. El empleado %s  ya se le generó esta nómina en este periódo')%self.employee_id.name)

    @api.onchange('currency_pres_id','monto','os_currecy_rate')
    def calcula_monto_prestamo_bs(self):
        if self.currency_pres_id.id!=3:
               self.monto_bs=self.monto*self.os_currecy_rate
        else:
            self.monto_bs=self.monto



    @api.depends('date_from','date_to')
    def _compute_dias(self): # Nuevo
        for selff in self:
            dia_in=selff.dia(selff.date_from)
            mes_in=selff.mes(selff.date_from)
            ano_in=selff.ano(selff.date_from)
            i=1
            verifica=""
            ban_vac=saturdays=sundays=0
            dias_descontar_1=dias_descontar_2=dias_descontar_3=dias_descontar_0=0
            #verifica=selff.env['hr.leave'].search([('employee_id','=',selff.employee_id.id),('state','=','validate'),('request_date_to','<=',selff.date_to),('request_date_from','>=',selff.date_from)])
            verifica1=selff.env['hr.leave'].search([('employee_id','=',selff.employee_id.id),('state','=','validate'),('request_date_to','>=',selff.date_from),('request_date_to','<=',selff.date_to)])
            verifica2=selff.env['hr.leave'].search([('employee_id','=',selff.employee_id.id),('state','=','validate'),('request_date_from','<=',selff.date_to),('request_date_from','>=',selff.date_from)])
            if verifica1:
                verifica=verifica1
            if verifica2:
                verifica=verifica2
            #raise UserError(_('verifica= %s')%verifica)
            if verifica:
                for det in verifica:
                    if det.holiday_status_id.code=='PR':
                        dias_descontar_1=dias_descontar_1+det.number_of_days
                    if det.holiday_status_id.code=='PNR':
                        dias_descontar_2=dias_descontar_2+det.number_of_days
                    # Lo activo si registro la ausencia por el modulo de ausencias y no por asistencias
                    #if det.holiday_status_id.code=='ANJ': # lo 
                        #dias_descontar_3=dias_descontar_3+det.number_of_days
                    if det.holiday_status_id.code=='VAC':
                        dias_descontar_0=dias_descontar_0+det.number_of_days
                        ban_vac=1

            selff.dias_permiso_remunerado=dias_descontar_1
            selff.dias_no_remunerado=dias_descontar_2
            selff.dias_vacaciones_pedidas=dias_descontar_0

            #Lo activo si registro la ausencia por el modulo de ausencias y no por asistencias
            #selff.dias_ausencia_injus=dias_descontar_3

            #Lo activo si el calculo de la ausencia por el modulo de asistencias
            total_dias_justifi=selff.dias_permiso_remunerado+selff.dias_vacaciones_pedidas+selff.dias_reposo_medico+selff.dias_reposo_medico_lab+selff.dias_pos_natal+selff.dias_peternidad
            selff.dias_ausencia_injus=selff.days_inasisti-total_dias_justifi if (selff.days_inasisti-total_dias_justifi)>=0 else 0
            ####### EL SIGUIENTE CODIGO SE VA A CONDENAR
            """if ban_vac==1:
                selff.dias_vacaciones_en_nomina=abs(selff.dias_vacaciones_pedidas-selff.workdays_periodo)
                raise UserError(_(' Aqui=%s')%selff.dias_vacaciones_en_nomina)
                for i in range(selff.dias_vacaciones_en_nomina+1):
                    dia_aux=0
                    dia_aux=calendar.weekday(ano_in,mes_in,i+1)
                    if dia_aux==5:
                        saturdays=saturdays+1
                    if dia_aux==6:
                        sundays=sundays+1
                selff.saturdays_sundays_vac=sundays+saturdays
            if ban_vac==0:
                selff.saturdays_sundays_vac=0"""

    @api.depends('date_from','date_to')
    def _compute_permiso(self):
        for selff in self:
            dias_descontar_4=0
            dias_descontar_5=dias_descontar_6=dias_descontar_7=0
            verifica=selff.env['hr.leave'].search([('employee_id','=',selff.employee_id.id),('state','=','validate'),('request_date_to','>=',selff.date_from)])
            #raise UserError(_('verifica= %s')%verifica)
            if verifica:
                for det in verifica:
                    if det.holiday_status_id.code=='RML':
                        dias_descontar_4=dias_descontar_4+det.number_of_days
                    if det.holiday_status_id.code=='RM':
                        dias_descontar_5=dias_descontar_5+det.number_of_days
                    if det.holiday_status_id.code=='DPPN':
                        dias_descontar_6=dias_descontar_6+det.number_of_days
                    if det.holiday_status_id.code=='LPP':
                        dias_descontar_7=dias_descontar_7+det.number_of_days

            selff.dias_reposo_medico_lab=dias_descontar_4
            selff.dias_reposo_medico=dias_descontar_5
            selff.dias_pos_natal=dias_descontar_6
            selff.dias_peternidad=dias_descontar_7


    @api.depends('employee_id','date_from','date_to')
    def _compute_tiempo_antiguedad(self):
        tiempo=0
        for selff in self:
            if selff.employee_id.id:
                fecha_ing=selff.employee_id.contract_id.date_start
                fecha_actual=selff.date_to
                if selff.employee_id.contract_id:
                    dias=selff.days_dife(fecha_actual,fecha_ing)
                    tiempo=dias/360
            selff.tiempo_antiguedad=tiempo

    #nuevo2
    @api.depends('employee_id')
    def _compute_dias_utilidades(self):
        for selff in self:
            dias_utilidades=30
            indicador=self.env['hr.payroll.indicadores.economicos'].search([('code','=','DUT')])
            if indicador:
                for det in indicador:
                    dias_utilidades=det.valor

            data=selff.date_to
            fecha = str(data)
            fecha_aux=fecha
            ano=fecha_aux[0:4]  
            ultimo_mes_ano=ano+"-12-31"
            selff.fecha_aux_util=ultimo_mes_ano
            diferencia=selff.days_dife(selff.fecha_aux_util,selff.contract_id.date_start)
            meses=round(diferencia/30,0)
            if meses>12:
                meses=12

            dias_utilidades=dias_utilidades*meses/12
            selff.dias_utilidades=dias_utilidades


    @api.depends('employee_id')
    def _compute_sueldo_mes_anterior(self):
        for selff in self:
            mes_actual=selff.mes(selff.date_to)
            mes_anterior=sueldo_anterior=0
            mes_anterior=mes_actual-1
            if mes_anterior==0:
                mes_anterior=12
            verifica=selff.env['hr.payroll.prestaciones'].search([('employee_id','=',selff.employee_id.id),('nro_mes','=',mes_anterior)],order='id desc')
            #raise UserError(_('valor= %s')%verifica)
            if verifica:
                for det in verifica:
                    sueldo_anterior=det.sueldo_base_mensual
            selff.sueldo_anterior_mes=sueldo_anterior

    @api.depends('employee_id')
    def _compute_dias_vacaciones(self):
        dias_difrute=0
        for selff in self:
            verifica=selff.env['hr.payroll.dias.vacaciones'].search([('service_years','=',selff.tiempo_antiguedad)])
            if verifica:
                for det in verifica:
                    dias_difrute=det.pay_day
            selff.dias_vacaciones=dias_difrute

    def compute_dias_por_ano_antiguedad(self):
        dias_antiguedad=0
        for selff in self:
            verifica_antig=selff.env['hr.payroll.dias.vacaciones'].search([('service_years','=',selff.tiempo_antiguedad)])
            if verifica_antig:
                for det in verifica_antig:
                    dias_antiguedad=det.pay_day_garantia
            selff.dias_por_antiguedad=dias_antiguedad

    @api.depends('date_from', 'date_to')
    def _compute_days(self): #nuevo
        for selff in self:
            holydays = mondays = saturdays = sundays = workdays = nro_feriado = 0
            hr_payroll_hollydays = selff.env['hr.payroll.hollydays'] ## busca en la tabla de feriados
            selff.actualiza_periodo()
            dia_in=selff.dia(selff.date_from)
            mes_in=selff.mes(selff.date_from)
            ano_in=selff.ano(selff.date_from)
            dia_fin=selff.dia(selff.date_to)
            mes_fin=selff.mes(selff.date_to)
            ano_fin=selff.ano(selff.date_to)
            dia=dia_in


            if not selff.employee_id.contract_id.date_start:
                fecha_contrato_ini=selff.fecha_hoy
            else:
                fecha_contrato_ini=selff.employee_id.contract_id.date_start
            if selff.date_from>=fecha_contrato_ini:
                fecha_from=selff.date_from
            else:
                fecha_from=fecha_contrato_ini


            if not selff.employee_id.contract_id.date_end:
                fecha_contrato_fin=selff.fecha_hoy
            else:
                fecha_contrato_fin=selff.employee_id.contract_id.date_end
            if selff.date_to<fecha_contrato_fin:
                fecha_to=selff.date_to
            else:
                fecha_to=fecha_contrato_fin

            dif_dia=selff.days_dife(fecha_from,fecha_to)
            dif_dia=dif_dia+1
            mes=mes_in
            for i in range(dif_dia):
                dia_aux=0
                dia_aux=calendar.weekday(ano_in,mes,dia)
                if dia_aux==0:
                    mondays=mondays+1
                if dia_aux==5:
                    saturdays=saturdays+1
                if dia_aux==6:
                    sundays=sundays+1
                dia=dia+1
                if dia>selff.verif_ult_dia_mes(mes):
                    dia=1
                    mes=mes+1
            hollyday_id = hr_payroll_hollydays.search([('date_from','>=',selff.date_from),('date_to','<=',selff.date_to),('hollydays','=',True)])
            #raise UserError(_('valor= %s')%hollyday_id)
            if hollyday_id:
                for det_holyday in hollyday_id:
                    nro_feriado=1+selff.days_dife(det_holyday.date_from,det_holyday.date_to)
                    holydays=holydays+nro_feriado

            if selff.company_id.tipo_dif_dias=='fech_cal':
                workdays = dif_dia - saturdays - sundays - holydays  #  OJO REVISAR PARA SUPER CAUCHOS
            if selff.company_id.tipo_dif_dias=='fech_con':
                workdays = selff.struct_id.shedule_pay_value - saturdays - sundays - holydays
                if selff.struct_id.shedule_pay_value==15:
                    saturdays=2
                    sundays=2
                    mondays=2
                if selff.struct_id.shedule_pay_value==30:
                    saturdays=4
                    sundays=4
                    mondays=4
                if selff.struct_id.shedule_pay_value==7:
                    saturdays=1
                    sundays=1
                    mondays=1

            selff.workdays_periodo=workdays

            ##### nuevo2
            """if selff.dias_vacaciones_pedidas>0:
                if selff.dias_vacaciones_pedidas>workdays:
                    workdays=abs(workdays-selff.dias_vacaciones_pedidas)#+1
                else:
                    workdays=abs(workdays-selff.dias_vacaciones_pedidas)"""

            #selff.saturdays=saturdays #nuevo2
            #selff.sundays=sundays #nuevo2
            selff.mondays=mondays
            #selff.workdays=workdays #nuevo2
            selff.holydays=holydays

    @api.depends('date_from','date_to')
    def _compute_days_attended(self):
        for selff in self:
            nro_asis=0
            # asistencia=selff.env['hr.attendance'].search([('check_out','<=',selff.date_to),('check_in','>=',selff.date_from),('employee_id','=',selff.employee_id.id)])
            # #raise UserError(_('valor= %s')%asistencia)
            # if asistencia:
            #     for det in asistencia:
            #         nro_asis=nro_asis+1
            selff.days_attended=nro_asis
            #self.days_attended=69

    #odoo 14
    """@api.depends('date_from','date_to') ### si uso el modulo de ausencias o inasistencias
    def _compute_days_inasisti(self):
        for selff in self:
            dias_descontar=0
            verifica=selff.env['hr.leave'].search([('employee_id','=',selff.employee_id.id),('state','=','validate'),('request_date_to','<=',selff.date_to),('request_date_from','>=',selff.date_from)])
            #raise UserError(_('verifica= %s')%verifica)
            if verifica:
                for det in verifica:
                    dias_descontar=dias_descontar+det.number_of_days
            selff.days_inasisti=dias_descontar"""

    @api.depends('date_from','date_to') ### si uso el modulo de asistencias
    def _compute_days_inasisti(self):
        for selff in self:
            selff.days_inasisti=selff.workdays-selff.days_attended if (selff.workdays-selff.days_attended)>=0 else 0
            #selff.days_inasisti=selff.workdays-selff.days_attended

    @api.depends('date_from','date_to','employee_id')
    def _compute_desfer_laborados(self):
        for selff in self:
            nro_feriado=nro_desc=nro_dia=0
            selff.hollydays_str=nro_feriado
            # asistencia=selff.env['hr.attendance'].search([('check_out','<=',selff.date_to),('check_in','>=',selff.date_from),('employee_id','=',selff.employee_id.id)])
            # #raise UserError(_('valor= %s')%asistencia)
            # if asistencia:
            #     for det in asistencia:
            #         fecha=det.check_out
            #         dia=selff.dia(fecha)
            #         mes=selff.mes(fecha)
            #         ano=selff.ano(fecha)
            #         nro_dia=calendar.weekday(ano,mes,dia)
            #         if nro_dia==5 or nro_dia==6:# aqui verifica si trabajo el sabado (5) o domingo (6)
            #             nro_desc=nro_desc+1
            #         # aqui verifica si trabaja en un dia feriado
            lista_feriado= False#selff.env['hr.payroll.hollydays'].search([('date_from','<=',det.check_out),('date_to','>=',det.check_out)])
            if lista_feriado:
                for ret in lista_feriado:
                    nro_feriado=nro_feriado+1
            selff.hollydays_str=nro_desc
            selff.hollydays_ftr=nro_feriado

    @api.depends('date_from','date_to','employee_id')
    def _compute_horas_extras_diurnas(self):
        for selff in self:
            horas=0
            dias_asis=0
            total_horas_extras=0
            selff.horas_extras_diurnas=total_horas_extras
            selff.horas_extras_nocturnas=total_horas_extras
            # horas_extr_d=selff.env['hr.attendance'].search([('check_out','<=',selff.date_to),('check_in','>=',selff.date_from),('employee_id','=',selff.employee_id.id)])
            # if horas_extr_d:
            #     for rec in horas_extr_d:
            #         horas=horas+rec.worked_hours
            #         dias_asis=dias_asis+1
            cantidad_horas_dia_permitida=selff.employee_id.contract_id.resource_calendar_id.hours_per_day
            total_horas_dias_permitidas=dias_asis*cantidad_horas_dia_permitida
            total_horas_extras=horas-total_horas_dias_permitidas
            if horas>total_horas_dias_permitidas:
                selff.horas_extras_diurnas=total_horas_extras
                selff.horas_extras_nocturnas=total_horas_extras


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

    def ano2(self,data):
        fecha = str(data)
        fecha_aux=fecha
        ano=fecha_aux[0:4]  
        resultado=ano
        return int(resultado)

    def days_dife(self,d1, d2):
        if not d1 or not d2:
            valor=0
        else:
            valor=abs((d2 - d1).days)
        return valor

    def actualiza_periodo(self):
        feriados=self.env['hr.payroll.hollydays'].search([])
        if feriados:
            for det in feriados:
                inicio=det.date_from
                fin=det.date_to
                ano_actual=self.ano(self.date_from)
                dia=self.dia(inicio)
                mes=self.mes(inicio)
                ano=self.ano(inicio)
                nuevo_from=str(ano_actual)+"-"+str(mes)+"-"+str(dia)
                dia=self.dia(fin)
                mes=self.mes(fin)
                ano=self.ano(fin)
                nuevo_to=str(ano_actual)+"-"+str(mes)+"-"+str(dia)
                det.date_from=nuevo_from
                det.date_to=nuevo_to

    def verif_ult_dia_mes(self,mes):
        if mes==1:
            ultimo=31
        if mes==2:
            ultimo=28
        if mes==3:
            ultimo=31
        if mes==4:
            ultimo=30
        if mes==5:
            ultimo=31
        if mes==6:
            ultimo=30
        if mes==7:
            ultimo=31
        if mes==8:
            ultimo=31
        if mes==9:
            ultimo=30
        if mes==10:
            ultimo=31
        if mes==11:
            ultimo=30
        if mes==12:
            ultimo=31
        return ultimo

    def float_format(self,valor):
        #valor=self.base_tax
        if valor:
            result = '{:,.2f}'.format(valor)
            result = result.replace(',','*')
            result = result.replace('.',',')
            result = result.replace('*','.')
        else:
            result="0,00"
        return result
