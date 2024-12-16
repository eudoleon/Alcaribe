# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Contract Aditional Data',
    'version': '1.1',
    'author': 'd',
    'category': 'Human Resources',
    'sequence': 104,
    'summary': 'Adds aditional fields to hr_contract module',
    'description': '''
        Agrega los siguientes campos adicionales al contrato de los empleados:\n
            * Bono Nocturno\n
            * Dias de Sueldo Pendiente\n
            * Feriados\n
            * Feriados no Laborados\n
            * Horas extraordinarias Diurnas\n
            * Retroactivo de Sueldo\n
            * Aporte Patronal F.A.O.V.\n
            * Aporte Patronal  Fondo de Ahorro\n
            * Aporte Patronal P.I.E.\n
            * Aporte Patronal S.O.S.\n
            * Fondo de Caja de Ahorro\n
            * Horas no Laboradas\n
            * Inasistencias Injustificadas\n
            * Permiso no Remunerados Dias\n
            * Permiso no Remunerados Horas\n
            * Retenciones  F.A.O.V.\n
            * Retenciones Fondo de Ahorro\n
            * Retenciones I.S.L.R.\n
            * Retenciones P.I.E.\n
            * Retenciones  S.O.S.\n
    ''',
    'depends': [
        'base_setup',
        'base',
        'hr',
        'hr_contract',
        'hr_payroll',
        #'hr_attendance',
        'hr_holidays',
        #'l10n_ve_res_currency',
        'hr_holidays',
        'hr_payroll_account',  ## este es un modulo de odoo nativo para que haga el asiento de la nomina
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_contract_add_fields_view1.xml',
        'views/hr_special_days.xml',
        'views/hr_vacation_days.xml',
        'views/hr_indicadores_economicos.xml',
        'views/hr_prestaciones.xml',
        'views/hr_incremento_view.xml',
        'views/hr_config_faov.xml',
        'views/hr_config_ince.xml',
        'views/hr_employee_inherit.xml', #ojo
        'views/hr_seting_inherit.xml',
        'views/x_hr_inherit_payroll_structure.xml',
        'views/hr_salary_rule_inherit.xml',
        'views/hr_ad_personal.xml',
        'views/hr_inherit_payslip_view.xml',
        'views/hr_inherit_payslip_run_view.xml',
        'views/hr_payslip_employee_inherit.xml',
        'views/hr_requisiciones.xml',
        'report/recibo_pago.xml',
        'report/recibo_vacaciones.xml',
        'report/recibo_liquidacion.xml',
        'report/recibo_pago_utilidades.xml', # nuevo2
        'report/constancia_trabajo.xml',
        'report/requisicion.xml',
        'views/hr_menu_setting_employee.xml',
        'report/monto_ince.xml',
        'wizard/wizard_generar_txt_view.xml',
        'report/monto_faov.xml',
        'views/hr_control_periodo_vacaciones.xml',
        'views/hr_leave_type_inherit_view.xml',
        
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'qweb': [],
}