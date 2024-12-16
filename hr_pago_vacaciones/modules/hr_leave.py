# coding: utf-8
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
import calendar
from odoo.exceptions import UserError, ValidationError


class HrLeaves(models.Model):
    _inherit = 'hr.leave'

    payslip_id=fields.Many2one('hr.payslip')
    tipo_vacaciones = fields.Char(compute='_compute_tipo_vac')

    @api.depends('holiday_status_id')
    def _compute_tipo_vac(self):
        self.tipo_vacaciones=self.holiday_status_id.tipo_vacaciones


    def pagar_vaca(self):
        return self.env['hr.ext.pago_nom']\
            .with_context(active_ids=self.ids, active_model='hr.leave', active_id=self.id)\
            .action_register_ext_payment()

    def action_refuse(self):
        super().action_refuse()
        if self.payslip_id.state=='done':
            raise UserError(_('No se puede reversar esta aprobacion de ausencias, ya tiene un pago de vacaciones procesado. Primero vaya al pago, pongalo a borrador y luego puede ejecutar este proceso'))

    def action_draft(self):
        super().action_draft()
        self.payslip_id.action_payslip_draft()
        self.payslip_id.with_context(force_delete=True).unlink()


class HrWizardPago(models.Model):
    _name = 'hr.ext.pago_nom'

    leave_id=fields.Many2one('hr.leave')
    struct_id = fields.Many2one('hr.payroll.structure')
    tasa = fields.Float(default=1)



    def action_register_ext_payment(self):
        active_ids = self.env.context.get('active_ids')
        if not active_ids:
            return ''
        #raise UserError(_('valor=%s')%active_ids[0])
        self.leave_id=active_ids[0]
        return {
            'name': _('Register Payment'),
            'res_model': len(active_ids) == 1 and 'hr.ext.pago_nom',
            'view_mode': 'form',
            'view_id': len(active_ids) != 1 and self.env.ref('hr_pago_vacaciones.vista_from_pago_employee').id,
            'context': self.env.context,
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def pagar_nom(self):
        active_ids = self._context.get('active_ids') or self._context.get('active_id')
        leave_id=active_ids[0]
        busca_leave=self.env['hr.leave'].search([('id','=',active_ids[0])])
        #raise UserError(_('valor=%s')%active_ids[0])
        if busca_leave:
            for leave_id in busca_leave:
                values=({
                    'date_from':leave_id.request_date_from,
                    'date_to':leave_id.request_date_to,
                    'struct_id':self.struct_id.id,
                    'contract_id':leave_id.employee_id.contract_id.id,
                    'name':"pago vacaciones de "+leave_id.employee_id.name,
                    'employee_id':leave_id.employee_id.id,
                    'os_currecy_rate_gene':self.tasa,
                    'custom_rate_gene':True,
                })
                leave_id.payslip_id=self.env['hr.payslip'].create(values)
                leave_id.payslip_id.compute_sheet()
