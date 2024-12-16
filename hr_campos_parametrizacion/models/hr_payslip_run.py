# coding: utf-8
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
import calendar
from odoo.exceptions import UserError, ValidationError

class HrPayslipRun(models.Model):
	_inherit = 'hr.payslip.run'

	tipo_pago_lote = fields.Selection([('bono', 'Bono Ayuda'),('cesta','Cesta Tiket'),('otros', 'Pagos Otros')])

	def reversar_nom(self):
		lista=self.env['hr.payslip'].search([('payslip_run_id','=',self.id)])
		if lista:
			for det in lista:
				if det.move_id:
					if det.move_id.state=='posted':
						det.move_id.filtered(lambda move: move.state == 'posted').button_draft()
					det.move_id.with_context(force_delete=True).unlink()
				det.state='draft'
				det.with_context(force_delete=True).unlink()
		self.state='draft'