# coding: utf-8
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
import calendar
from odoo.exceptions import UserError, ValidationError

class HrConfigInce(models.Model):
    _name = 'hr.config.ince'
    _description = 'Configuracion retencion INCE'

    name = fields.Char()
    name_aux = fields.Char(compute='_compute_name')
    tipo_nomina_id = fields.Many2one('hr.payroll.structure.type')
    pago_utilidades= fields.Boolean(default=False)
    tipo_pago_id = fields.Many2one('hr.payroll.structure')
    line_reglas = fields.One2many('hr.ince.reglas', 'config_ince_id', string='reglas')
    activo = fields.Boolean(default=True)

    @api.onchange('tipo_nomina_id')
    def _compute_name(self):
    	valor="/"
    	for rec in self:
	    	if rec.tipo_nomina_id:
	    		valor=rec.tipo_nomina_id.name
	    	rec.name_aux=valor
	    	if rec.name=="/" or not rec.name:
	    		rec.name=valor


class HrLineReglas(models.Model):
	_name = 'hr.ince.reglas'

	config_ince_id=fields.Many2one('hr.config.ince')
	tipo_nomina_id=fields.Many2one(related='config_ince_id.tipo_nomina_id',store=True)
	tipo_pago_id = fields.Many2one(related='config_ince_id.tipo_pago_id',store=True)
	regla_id = fields.Many2one('hr.salary.rule')