# -*- coding: utf-8 -*-
from logging import exception
from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from pytz import timezone
import base64
import io
import xlsxwriter
import math
from itertools import groupby


class AccountPaymentCe(models.Model):
	_inherit = 'account.payment.ce'

	def get_excel_report(self):
		filename = 'Programacion de pagos banco {}-{}.xlsx'.format(self.journal_id.name, str(self.date))
		stream = io.BytesIO()
		book = xlsxwriter.Workbook(stream, {'in_memory': True})
		sheet = book.add_worksheet('Facturas De Proveedores')
		sheet_2 = book.add_worksheet('Egresos Proveedores')
		columns = [
			'Empresa', 
			'Identificacion', 
			'Proveedore/Tercero', 
			'Documento Adeudado', 
			'Referencias Proveedores',
			'Fecha de Documento', 
			'Fecha de Vencimiento', 
			'Monto Adeudado',  
			'Monto Adeudado En Otra Moneda', 
			'Moneda De Documento',  
			'Monto Pagado', 
			'Moneda de Pago',
			'Cuenta Analitica'
		]
		columns_ce = [
			'Empresa', 
			'Identificacion', 
			'Proveedore/Tercero',
			'Forma de pago',
			'Metodo de Pago',
			'Banco Abonado',
			'Referencia', 
			'Fecha de Documento', 
			'Monto Pagado',   
			'Moneda De Documento',  
			'Estado',
		]
		# Agregar textos al excel
		text_title = 'Programacion De Pagos'
		text_title_1 = 'Comprobante De Egreso'
		text_generate = 'Informe generado el %s' % (datetime.now(timezone(self.env.user.tz)))
		cell_format_title = book.add_format({'bold': True, 'align': 'left'})
		cell_format_title.set_font_name('Calibri')
		cell_format_title.set_font_size(15)
		cell_format_title.set_bottom(5)
		cell_format_title.set_bottom_color('#1F497D')
		cell_format_title.set_font_color('#1F497D')
		sheet.merge_range('A1:M1', text_title, cell_format_title)
		sheet_2.merge_range('A1:K1', text_title_1, cell_format_title)
		cell_format_text_generate = book.add_format({'bold': False, 'align': 'left'})
		cell_format_text_generate.set_font_name('Calibri')
		cell_format_text_generate.set_font_size(10)
		cell_format_text_generate.set_bottom(5)
		cell_format_text_generate.set_bottom_color('#1F497D')
		cell_format_text_generate.set_font_color('#1F497D')
		sheet.merge_range('A2:M2', text_generate, cell_format_text_generate)
		sheet_2.merge_range('A2:K2', text_generate, cell_format_text_generate)
		# Formato para fechas
		date_format = book.add_format({'num_format': 'dd/mm/yyyy'})
		money = book.add_format({'num_format':'$#,##0.00'})
		# Agregar columnas
		aument_columns = 0
		for column in columns:
			sheet.write(2, aument_columns, column)
			sheet.set_column(aument_columns, aument_columns, len(str(column)) + 10)
			aument_columns = aument_columns + 1
		# Agregar columnas 2
		aument_columns_2 = 0
		for column_2 in columns_ce:
			sheet_2.write(2, aument_columns_2, column_2)
			sheet_2.set_column(aument_columns_2, aument_columns_2, len(str(column_2)) + 10)
			aument_columns_2 = aument_columns_2 + 1
		# Agregar valores
		sorted_lines = sorted(self.payment_lines, key=lambda x: x.partner_id.id)
		grouped_lines = groupby(sorted_lines, key=lambda x: x.partner_id.id)
		aument_rows = 3
		totals_by_partner = {}
		total_general = 0

		for partner_id, lines in grouped_lines:
			subtotal_partner = 0
			for item in lines:
				sheet.write(aument_rows, 0, item.company_id.name)
				sheet.write(aument_rows, 1, item.partner_id.vat_co or "")
				sheet.write(aument_rows, 2, item.partner_id.name)
				sheet.write(aument_rows, 3, item.move_line_id.move_name)
				sheet.write(aument_rows, 4, item.move_line_id.name or item.name or item.move_line_id.move_id.ref or "SIN REFERENCIA")
				sheet.write(aument_rows, 5, item.move_line_id.date, date_format)
				sheet.write(aument_rows, 6, item.date_maturity, date_format)
				sheet.write(aument_rows, 7, item.amount_residual, money)
				sheet.write(aument_rows, 8, item.amount_residual_currency, money)
				sheet.write(aument_rows, 9, item.move_line_id.currency_id.name)
				sheet.write(aument_rows, 10, item.payment_amount, money)
				sheet.write(aument_rows, 11, item.payment_currency_id.name)
				sheet.write(aument_rows, 12, item.analytic_account_id.name)
				aument_rows = aument_rows + 1

				subtotal_partner += item.payment_amount
				total_general += item.payment_amount

			# Totalizar por partner_id
			totals_by_partner[partner_id] = subtotal_partner

		# Agregar total general
		sheet.write(aument_rows, 10, 'Total General', cell_format_title)
		sheet.write(aument_rows, 11, total_general, money)

		# Agregar tabla de totales por partner
		sheet_totals = book.add_worksheet('Totales por Partner')
		columns_totals = ['Partner ID', 'Total']
		aument_columns_totals = 0
		for column_totals in columns_totals:
			sheet_totals.write(0, aument_columns_totals, column_totals)
			sheet_totals.set_column(aument_columns_totals, aument_columns_totals, len(str(column_totals)) + 10)
			aument_columns_totals += 1

		aument_rows_totals = 1
		for partner_id, total in totals_by_partner.items():
			sheet_totals.write(aument_rows_totals, 0, partner_id)
			sheet_totals.write(aument_rows_totals, 1, total, money)
			aument_rows_totals += 1

		# Agregar tabla de totales por partner
		sheet_totals.add_table(0, 0, aument_rows_totals - 1, len(columns_totals) - 1,
							{'style': 'Table Style Medium 2', 'columns': [{'header': column} for column in columns_totals]})

		book.close()

		self.write({
			'excel_file': base64.encodebytes(stream.getvalue()).decode(),
			'excel_file_name': filename,
		})

		action = {
			'name': 'Export Seguridad Social',
			'type': 'ir.actions.act_url',
			'url': "web/content/?model=account.payment.ce&id=" + str(
				self.id) + "&filename_field=excel_file_name&field=excel_file&download=true&filename=" + self.excel_file_name,
			'target': 'self',
		}
		return action