#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from datetime import datetime
import pytz

from odoo import api, fields, models
from odoo.osv import expression

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    planning_slot_count = fields.Integer(compute='_compute_planning_slot_count', groups="planning.group_planning_manager")

    @api.depends('date_from', 'date_to', 'contract_id')
    def _compute_planning_slot_count(self):
        self.planning_slot_count = 0
        planning_slips = self.filtered(lambda p: p.contract_id.work_entry_source == 'planning')
        if not planning_slips:
            return
        domain = []
        slip_by_employee = defaultdict(lambda: self.env['hr.payslip'])
        for slip in planning_slips:
            slip_by_employee[slip.employee_id.id] |= slip
            domain = expression.OR([
                domain,
                [
                    ('employee_id', '=', slip.employee_id.id),
                    ('start_datetime', '<=', slip.date_to),
                    ('end_datetime', '>=', slip.date_from),
                ],
            ])
        domain = expression.AND([
            [('state', '=', 'published')],
            domain,
        ])
        read_group = self.env['planning.slot'].read_group(domain, fields=['id'], groupby=['employee_id', 'start_datetime:day'], lazy=False)
        employee_ids = list({planning['employee_id'][0] for planning in read_group})
        employee_tz = {employee.id: pytz.timezone(employee.tz) for employee in self.env['hr.employee'].browse(employee_ids)}
        for result in read_group:
            employee_id = result['employee_id'][0]
            slips = slip_by_employee[employee_id]
            start_date_utc = datetime.strptime(result['__range']['start_datetime:day']['from'], '%Y-%m-%d %H:%M:%S')
            start_date_employee = start_date_utc.astimezone(employee_tz[employee_id]).date()
            for slip in slips:
                if slip.date_from <= start_date_employee and start_date_employee <= slip.date_to:
                    slip.planning_slot_count += result['__count']

    def action_open_planning_slots(self):
        self.ensure_one()
        action = self.employee_id.action_view_planning()
        action['domain'] = expression.AND([
            action['domain'],
            [
                ('state', '=', 'published'),
                ('start_datetime', '<=', self.date_to),
                ('end_datetime', '>=', self.date_from),
            ],
        ])
        action['context']['default_scale'] = 'month'
        return action
