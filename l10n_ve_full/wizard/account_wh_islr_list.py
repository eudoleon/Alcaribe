# -*- coding: utf-8 -*-

import base64
import locale
import xlwt
from datetime import date, datetime
from io import BytesIO

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


class RetentionISLR(models.Model):
    _name = 'account.wh.islr.list'
    _description = 'Open Retention ISLR'

    company = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, readonly=True, store=True)
    start_date = fields.Date(required=True, default=fields.Datetime.now)
    end_date = fields.Date(required=True, default=fields.Datetime.now)
    supplier = fields.Boolean(default=False)
    customer = fields.Boolean(default=False)
    partner_id = fields.Many2one('res.partner')
    clientes = fields.Many2one('res.partner')
    concepto = fields.Boolean(default=True)
    todos = fields.Boolean(default=True)
    concept = fields.Many2many('account.wh.islr.concept')

    state = fields.Selection([('choose', 'choose'), ('get', 'get')], default='choose')
    report = fields.Binary('Descargar xls', filters='.xls', readonly=True)
    name = fields.Char('File Name', size=32)

    def generate_retention_islr_xls(self):
        hoy = date.today()
        format_new = "%d/%m/%Y"
        hoy_date = datetime.strftime(hoy, format_new)
        start_date = datetime.strftime(datetime.strptime(str(self.start_date), DEFAULT_SERVER_DATE_FORMAT), format_new)
        end_date = datetime.strftime(datetime.strptime(str(self.end_date), DEFAULT_SERVER_DATE_FORMAT), format_new)
        locale.setlocale(locale.LC_ALL, '')

        self.ensure_one()
        fp = BytesIO()
        wb = xlwt.Workbook(encoding='utf-8')
        writer = wb.add_sheet('Nombre de hoja')

        # retention_islr = [], pnre = [], unico = [], repetido = [], retention_islr_asc = [], pnre_asc = []
        # suma_base = 0, suma_imp_ret = 0, suma_total_base = 0, suma_total_imp_ret = 0

        islr_concept = []
        partner = []
        concept_id = []
        lista_nueva_partner = []
        islr_concept_id = None
        total_amount = 0

        concept = self.concept.id
        if self.todos:
            concepts = self.env['account.wh.islr.concept'].search([('id', '!=', 0)])
            concept = []
            for i in concepts:
                concept.append(i.id)
        if self.supplier and not self.customer:
            islr_concept_id = self.env['account.wh.islr.doc'].search([('company_id', '=', self.company.id),
                                                              ('type', '=', 'in_invoice'),
                                                              ('state', '=', 'done'),
                                                              ('date_ret', '>=', self.start_date),
                                                              ('date_ret', '<=', self.end_date)])

        if not self.supplier and self.customer:
            islr_concept_id = self.env['account.wh.islr.doc'].search([('company_id', '=', self.company.id),
                                                              ('type', '=', 'out_invoice'),
                                                              ('state', '=', 'done'),
                                                              ('date_ret', '>=', self.start_date),
                                                              ('date_ret', '<=', self.end_date)])

        if not self.supplier and not self.customer:
            todo_supplier = self.env['res.partner'].search(['|', ('customer_rank', '>', 0), ('supplier_rank', '>', 0)])
            for y in todo_supplier:
                partner.append(y.id)

            for i in partner:
                if i not in lista_nueva_partner:
                    lista_nueva_partner.append(i)
            type = ['out_invoice', 'in_invoice']
            islr_concept_id = self.env['account.wh.islr.doc'].search([('company_id', '=', self.company.id),
                                                              ('type', 'in', type),
                                                              ('state', '=', 'done'),
                                                              ('date_ret', '>=', self.start_date),
                                                              ('date_ret', '<=', self.end_date)])

        for a in islr_concept_id:
            islr_concept.append(a.id)

        islr_concept_line = self.env['account.wh.islr.doc.line'].search([('concept_id', '=', concept),
                                                                 ('islr_wh_doc_id', '=', islr_concept)])
        if islr_concept_line:
            for i in islr_concept_line:
                concept_id.append(i.concept_id.name)
            concept_id.sort()
        else:
            raise UserError('No hay retenciones en estado Hecho')

        # header_content_style = xlwt.easyxf("font: name Helvetica size 80 px, bold 1, height 200;")
        # sub_header_style = xlwt.easyxf("font: name Helvetica size 10 px, bold 1, height 170; "
        #                                "borders: left thin, right thin, top thin, bottom thin;")
        # line_content_style_totales = xlwt.easyxf("font: name Helvetica size 10 px, bold 1, height 170; "
        #                                          "borders: left thin, right thin, top thin, bottom thin; "
        #                                          "align: horiz right;")
        sub_header_style_bold = xlwt.easyxf("font: name Helvetica size 10 px, bold 1, height 170;")
        sub_header_content_style = xlwt.easyxf("font: name Helvetica size 10 px, height 170;")
        line_content_style = xlwt.easyxf("font: name Helvetica, height 170; align: horiz right;")
        line_content_style_2 = xlwt.easyxf("font: name Helvetica, height 170;")

        row = 1

        # writer.write_merge(row, row, 0, header_cols, "Información de contactos",)

        writer.write_merge(row, row, 1, 2, str(self.company.name), sub_header_content_style)
        writer.write_merge(row, row, 11, 12, "Fecha de Impresión:", sub_header_style_bold)
        writer.write_merge(row, row, 13, 13, hoy_date, sub_header_content_style)
        row += 1

        writer.write_merge(row, row, 1, 2, "R.I.F:", sub_header_style_bold)
        writer.write_merge(row, row, 3, 4, str(self.company.vat), sub_header_content_style)
        row += 1

        writer.write_merge(row, row, 1, 6, "*RELACIÓN DETALLADA DE I.S.L.R. RETENIDO*",
                           sub_header_style_bold)
        row += 1

        writer.write_merge(row, row, 1, 2, "Fecha Desde:", sub_header_style_bold)
        writer.write_merge(row, row, 3, 3, start_date, sub_header_content_style)
        writer.write_merge(row, row, 5, 6, "Fecha Hasta:", sub_header_style_bold)
        writer.write_merge(row, row, 7, 7, end_date, sub_header_content_style)
        row += 1

        # ENCABEZADO DEL REPORTE
        writer.write_merge(row, row, 1, 1, "FECHA", sub_header_style_bold)
        writer.write_merge(row, row, 2, 3,  "PROVEEDOR", sub_header_style_bold)
        writer.write_merge(row, row, 4, 4, "DOCUMENTO IDENT/RIF:", sub_header_style_bold)
        writer.write_merge(row, row, 5, 5, "FACTURA:", sub_header_style_bold)
        writer.write_merge(row, row, 6, 6, "CONTROL:", sub_header_style_bold)
        writer.write_merge(row, row, 7, 7, "CONCEPTO", sub_header_style_bold)
        writer.write_merge(row, row, 8, 8, "CODIGO CONCEPTO", sub_header_style_bold)
        writer.write_merge(row, row, 9, 9, "MONTO SUJETO A RETENCION", sub_header_style_bold)
        writer.write_merge(row, row, 10, 10, "TASA PORC", sub_header_style_bold)
        writer.write_merge(row, row, 11, 11, "IMPUESTO RETENIDO", sub_header_style_bold)
        row += 1

        # CUERPO DEL REPORTE DE XLS
        for concept_line in islr_concept_line:
            if concept_line.invoice_id.partner_id.company_type == 'person':
                if concept_line.invoice_id.partner_id.rif:
                    document = concept_line.invoice_id.partner_id.rif
                elif concept_line.invoice_id.partner_id.nationality == 'V' or concept_line.invoice_id.partner_id.nationality == 'E':
                    document = str(concept_line.invoice_id.partner_id.nationality) + str(
                        concept_line.invoice_id.partner_id.identification_id)
                else:
                    document = str(concept_line.invoice_id.partner_id.identification_id)
            else:
                document = concept_line.invoice_id.partner_id.rif

            if concept_line.invoice_id.nro_ctrl:
                nro_control = concept_line.invoice_id.nro_ctrl
            else:
                nro_control = concept_line.invoice_id.nro_ctrl

            total_amount += concept_line.amount
            fecha = concept_line.invoice_id.date
            fecha_inicio = fecha.strftime('%d-%m-%Y')
            cod_concepto = None
            for cod in concept_line.concept_id.rate_ids:
                if cod.wh_perc == concept_line.retencion_islr:
                    cod_concepto = cod.code
            writer.write_merge(row, row, 1, 1,   fecha_inicio, line_content_style_2)
            writer.write_merge(row, row, 2, 3,    concept_line.invoice_id.partner_id.name, line_content_style_2)
            writer.write_merge(row, row, 4, 4,   document, line_content_style_2)
            writer.write_merge(row, row, 5, 5,   concept_line.invoice_id.supplier_invoice_number, line_content_style_2)
            writer.write_merge(row, row, 6, 6,   nro_control, line_content_style_2)
            writer.write_merge(row, row, 7, 7,   concept_line.concept_id.display_name, line_content_style_2)
            writer.write_merge(row, row, 8, 8,  cod_concepto, line_content_style_2)
            writer.write_merge(row, row, 9, 9,  self.separador_cifra(concept_line.base_amount), line_content_style)
            writer.write_merge(row, row, 10, 10,  concept_line.retencion_islr, line_content_style)
            writer.write_merge(row, row, 11, 11, self.separador_cifra(concept_line.amount), line_content_style)
            row += 1
        row += 1
        writer.write_merge(row, row, 10, 10, "TOTAL IMPUESTO RETENIDO", sub_header_style_bold)
        writer.write_merge(row, row, 11, 11, self.separador_cifra(total_amount), line_content_style)

        wb.save(fp)

        out = base64.encodebytes(fp.getvalue())
        self.write({'state': 'get', 'report': out, 'name': 'Detalle_De_Ret_de_ISLR.xls'})

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.wh.islr.list',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }

    def generate_retention_islr_pdf(self):
        b = []
        name = []
        for a in self.concept:
            b.append(a.id)
            name.append(a.name)
        data = {
            'ids': self.ids,
            'model': 'report.l10n_ve_full.report_retention_islr1',
            'form': {
                'date_start': self.start_date,
                'date_stop': self.end_date,
                'company': self.company.id,
                'supplier': self.supplier,
                'partner_id': self.partner_id.id,
                'customer': self.customer,
                'clientes': self.clientes.id,
                'concept': b,
                'concept_name': name,
                'todos': self.todos,
            },
        }

        return self.env.ref('l10n_ve_full.action_report_retention_islr').report_action(self, data=data)

    @staticmethod
    def separador_cifra(valor):
        monto = '{0:,.2f}'.format(valor).replace('.', '-')
        monto = monto.replace(',', '.')
        monto = monto.replace('-', ',')
        return monto


class ReportRetentionISLR(models.AbstractModel):
    _name = 'report.l10n_ve_full.report_retention_islr1'

    @api.model
    def _get_report_values(self, docids, data=None):
        date_start = data['form']['date_start']
        end_date = data['form']['date_stop']
        company_id = data['form']['company']
        supplier = data['form']['supplier']
        partner_id = data['form']['partner_id']
        customer = data['form']['customer']
        clientes = data['form']['clientes']
        concept = data['form']['concept']
        todos = data['form']['todos']
        today = date.today()
        cod_concepto = ' '
        islr_concept = []
        concept_id = []
        partner = []
        lista_nueva_partner = []
        # concept_name = data['form']['concept_name'], retention_islr = [], pnre = [], unico = [], repetido = []
        # retention_islr_asc = [], pnre_asc = []

        if todos:
            concepts = self.env['account.wh.islr.concept'].search([('id', '!=', 0)])
            concept = []
            for i in concepts:
                concept.append(i.id)

        company = self.env['res.company'].search([('id', '=', company_id)])
        islr_concept_id = None
        date_ret1 = datetime.strptime(date_start, '%Y-%m-%d').date()
        date_ret2 = datetime.strptime(end_date, '%Y-%m-%d').date()



        if supplier and not customer:
            lista_nueva_partner = []
            todo_supplier = self.env['res.partner'].search([('supplier_rank', '>', 0)])
            for y in todo_supplier:
                partner.append(y.id)

            for i in partner:
                if i not in lista_nueva_partner:
                    lista_nueva_partner.append(i)

            islr_concept_id = self.env['account.wh.islr.doc'].search([('company_id', '=', company_id),
                                                             ('partner_id', 'in', lista_nueva_partner),
                                                              ('type', '=', 'in_invoice'),
                                                              ('state', '=', 'done'),
                                                              ('date_ret', '>=', date_ret1),
                                                              ('date_ret', '<=', date_ret2)])

        if not supplier and customer:
            lista_nueva_partner = []
            todo_supplier = self.env['res.partner'].search([('customer_rank', '>', 0)])
            for y in todo_supplier:
                partner.append(y.id)

            for i in partner:
                if i not in lista_nueva_partner:
                    lista_nueva_partner.append(i)
            islr_concept_id = self.env['account.wh.islr.doc'].search([('company_id', '=', company_id),
                                                              ('partner_id', 'in', lista_nueva_partner),
                                                              ('type', '=', 'out_invoice'),
                                                              ('state', '=', 'done'),
                                                              ('date_ret', '>=', date_ret1),
                                                              ('date_ret', '<=', date_ret2)])

        if supplier and customer:
            lista_nueva_partner = []
            todo_supplier = self.env['res.partner'].search(['|', ('customer_rank', '>', 0), ('supplier_rank', '>', 0)])
            for y in todo_supplier:
                partner.append(y.id)

            for i in partner:
                if i not in lista_nueva_partner:
                    lista_nueva_partner.append(i)

            type = ['out_invoice', 'in_invoice']
            islr_concept_id = self.env['account.wh.islr.doc'].search([('company_id', '=', company_id),
                                                              ('partner_id', 'in', lista_nueva_partner),
                                                              ('type', '=', type),
                                                              ('state', '=', 'done'),
                                                              ('date_ret', '>=', date_ret1),
                                                              ('date_ret', '<=', date_ret2)])

        if not supplier and not customer:
            todo_supplier = self.env['res.partner'].search(['|', ('customer_rank', '>', 0), ('supplier_rank', '>', 0)])
            for y in todo_supplier:
                partner.append(y.id)

            for i in partner:
                if i not in lista_nueva_partner:
                    lista_nueva_partner.append(i)
            type = ['out_invoice', 'in_invoice']


            islr_concept_id = self.env['account.wh.islr.doc'].search([('company_id', '=', company_id),
                                                              ('partner_id', 'in', lista_nueva_partner),
                                                              ('type', 'in', type),
                                                              ('state', '=', 'done'),
                                                              ('date_ret', '>=', date_ret1),
                                                              ('date_ret', '<=', date_ret2)
                                                              ])
        if islr_concept_id:
            for a in islr_concept_id:
                islr_concept.append(a.id)

        islr_concept_line = self.env['account.wh.islr.doc.line'].search([('concept_id', 'in', concept),
                                                                 ('islr_wh_doc_id', 'in', islr_concept)])

        if islr_concept_line:
            for i in islr_concept_line:
                concept_id.append(i.concept_id.name)
            concept_id.sort()
        else:
            raise UserError('No hay retenciones en estado Realizado')

        docs = []
        total_amount = 0

        for concept_line in islr_concept_line:
            if concept_line.invoice_id:
                if concept_line.invoice_id.nro_ctrl:
                    nro_control = concept_line.invoice_id.nro_ctrl
                else:
                    nro_control = concept_line.invoice_id.nro_ctrl
                total_amount += concept_line.amount
                fecha = concept_line.invoice_id.date
                fecha_inicio = fecha.strftime('%d-%m-%Y')
                for cod in concept_line.concept_id.rate_ids:
                    if cod.wh_perc == concept_line.retencion_islr:
                        cod_concepto = cod.code
                if concept_line.invoice_id.partner_id.company_type == 'person':
                    if concept_line.invoice_id.partner_id.rif:
                        document = concept_line.invoice_id.partner_id.rif
                    elif concept_line.invoice_id.partner_id.nationality == 'V' or concept_line.invoice_id.partner_id.nationality == 'E':
                        document = str(concept_line.invoice_id.partner_id.nationality) + str(concept_line.invoice_id.partner_id.identification_id)
                    else:
                        document = str(concept_line.invoice_id.partner_id.identification_id)
                else:
                    document = concept_line.invoice_id.partner_id.rif

                docs.append({
                    'fecha': fecha_inicio,
                    'name': concept_line.concept_id.display_name,
                    'proveedor': concept_line.invoice_id.partner_id.name,
                    'rif': document,
                    'factura': concept_line.invoice_id.supplier_invoice_number,
                    'control': nro_control,
                    'cod_concepto': cod_concepto,
                    'monto_suj_retencion': self.separador_cifra(concept_line.base_amount),
                    'tasa_porc': concept_line.retencion_islr,
                    'sustraendo': concept_line.xml_ids[0].rate_id.subtract,
                    'impusto_retenido': self.separador_cifra(concept_line.amount),
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
