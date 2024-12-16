# coding: utf-8
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
import calendar
from odoo.exceptions import UserError, ValidationError


class HrRequisiciones(models.Model):
    _name = 'hr.requisiciones'

    name = fields.Char(default='/',tracking=True)
    fecha = fields.Date()
    departamento_solicitante = fields.Many2one('hr.department',tracking=True)
    jefe_compras_id = fields.Many2one('hr.employee',tracking=True)
    motivo = fields.Text()
    requisicion_line_ids = fields.One2many('hr.requisiciones.line', 'requisicion_id', string='Requisiciones',tracking=True)
    company_id = fields.Many2one('res.company','Company',default=lambda self: self.env.company.id)
    state=fields.Selection(selection=[('draft','En Borrador'),('posted','Confirmada')],default='draft',tracking=True)
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def confirmar(self):
        self.state="posted"
        if self.name=="/":
            self.name=self.get_nro_requisicion()

    def cancel(self):
        self.state="draft"

    def unlink(self):
        for vat in self:
            if vat.state=='posted':
                raise UserError(_("No se puede eliminar en estado Confirmado"))
        return super(HrRequisiciones,self).unlink()

    def get_nro_requisicion(self):
        '''metodo que crea el Nombre del asiento contable si la secuencia no esta creada, crea una con el
        nombre: 'l10n_ve_cuenta_retencion_iva'''

        self.ensure_one()
        SEQUENCE_CODE = 'secuencia_codigo_requisicion_uniformes'+str(self.company_id.id)
        company_id = self.env.company.id
        IrSequence = self.env['ir.sequence'].with_context(force_company=self.env.company.id)
        name = IrSequence.next_by_code(SEQUENCE_CODE)

        # si aún no existe una secuencia para esta empresa, cree una
        if not name:
            IrSequence.sudo().create({
                'prefix': 'REQ/',
                'name': 'Localización Venezolana Recepciones Uniformes %s' % self.env.company.name,
                'code': SEQUENCE_CODE,
                'implementation': 'no_gap',
                'padding': 8,
                'number_increment': 1,
                'company_id': self.env.company.id,#loca14
            })
            name = IrSequence.next_by_code(SEQUENCE_CODE)
        return name


class HrRequisicionesLine(models.Model):
    _name = 'hr.requisiciones.line'

    requisicion_id = fields.Many2one('hr.requisiciones', string='Lineas de Requisiciones')
    cantidad = fields.Float(defaul=0)
    descripcion = fields.Char()
