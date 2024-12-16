# -*- coding: utf-8 -*-

import base64
import locale
import xlwt
from datetime import date, datetime
from io import BytesIO

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


class RetentionIVA(models.Model):
    _name = 'account.wh.iva.list'
    _description = 'Listado Retención IVA'

    company = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, readonly=True, store=True)
    start_date = fields.Date(required=True, default=fields.Datetime.now)
    end_date = fields.Date(required=True, default=fields.Datetime.now)
    supplier = fields.Boolean(default=False)
    customer = fields.Boolean(default=False)
    partner_id = fields.Many2one('res.partner')

    state = fields.Selection([('choose', 'choose'), ('get', 'get')], default='choose')
    report = fields.Binary('Descargar xls', filters='.xls', readonly=True)
    name = fields.Char('File Name', size=32)

    def generate_retention_iva_pdf(self):
        b = []
        name = []
        data = {
            'ids': self.ids,
            'model': 'report.l10n_ve_full.report_retention_iva',
            'form': {
                'date_start': self.start_date,
                'date_stop': self.end_date,
                'company': self.company.id,
                'supplier': self.supplier,
                'partner_id': self.partner_id.id,
                'customer': self.customer,
            },
        }
        #print(data)
        return self.env.ref('l10n_ve_full.action_report_retention_iva').report_action(self, data=data)

    @staticmethod
    def separador_cifra(valor):
        monto = '{0:,.2f}'.format(valor).replace('.', '-')
        monto = monto.replace(',', '.')
        monto = monto.replace('-', ',')
        return monto


class ReportRetentionIVA(models.AbstractModel):
    _name = 'report.l10n_ve_full.report_retention_iva_list'

    @api.model
    def _get_report_values(self, docids, data=None):
        date_start = data['form']['date_start']
        end_date = data['form']['date_stop']
        company_id = data['form']['company']
        supplier = data['form']['supplier']
        partner_id = data['form']['partner_id']
        customer = data['form']['customer']
        today = date.today()

        company = self.env['res.company'].search([('id', '=', company_id)])
        #print(company)
        doc_iva_ids = self.env['account.wh.iva'].search([('company_id', '=', company_id),
                                                                  ('type', 'in', ['in_invoice','in_refund']),
                                                                  ('state', '=', 'done'),
                                                                  ('date_ret', '>=', date_start),
                                                                  ('date_ret', '<=', end_date)])

        if not doc_iva_ids:
            raise UserError('No hay retenciones en estatus Realizado y el periodo seleccionado')

        docs = []
        total_amount = 0

        for iva in doc_iva_ids:
            for line in iva.wh_lines:
                fecha_factura = line.invoice_id.date
                fecha_inicio = fecha_factura.strftime('%d-%m-%Y')
                total_amount += line.amount_tax_ret
                documento = ''
                if line.invoice_id.partner_id.company_type == 'person':
                    if line.invoice_id.partner_id.rif:
                        documento = line.invoice_id.partner_id.rif
                    elif line.invoice_id.partner_id.nationality == 'V' or line.invoice_id.partner_id.nationality == 'E':
                        documento = str(line.invoice_id.partner_id.nationality) + str(line.invoice_id.partner_id.identification_id)
                    else:
                        documento = str(line.invoice_id.partner_id.identification_id)
                else:
                    documento = line.invoice_id.partner_id.rif


                docs.append({
                    'fecha': fecha_inicio,
                    'documento': line.retention_id.number,
                    'proveedor': line.invoice_id.partner_id.name,
                    'rif': documento,
                    'factura': line.invoice_id.supplier_invoice_number,
                    'control': line.invoice_id.nro_ctrl,
                    'monto_suj_retencion': self.separador_cifra(line.base_ret),
                    'tasa_porc': line.wh_iva_rate,
                    'impuesto_retenido': self.separador_cifra(line.amount_tax_ret),
                })




        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'end_date': end_date,
            'start_date': date_start,
            'today': today,
            'company': company,
            'docs': docs,
            'total_amount': self.separador_cifra(total_amount)
        }

    @staticmethod
    def separador_cifra(valor):
        monto = '{0:,.2f}'.format(valor).replace('.', '-')
        monto = monto.replace(',', '.')
        monto = monto.replace('-', ',')
        return monto
