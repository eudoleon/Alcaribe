from odoo import models, fields, api
import base64
from io import StringIO, BytesIO
from datetime import datetime, time
from odoo.osv import osv
import math
import xlsxwriter
from docutils.nodes import row
import os
# from odoo.tools.misc import xlwt
try:
	import xlwt
	from xlwt import Borders
except ImportError:
	xlwt = None


class import_bank_statement(models.TransientModel):
	_name = 'account.tax.reports'

	from_date = fields.Date("Fecha Desde", required=True)
	to_date = fields.Date("Fecha Hasta", required=True)
	company_id = fields.Many2one("res.company", string="Company", required=True)
	datas = fields.Binary('File')
	tax_ids = fields.Many2many("account.tax", string="Impuesto",help="If you select taxes from here then it will generate only that tax related report otherwise it will generate the report that include all taxes.")
	tax_or_group = fields.Selection([('tax', 'Taxes'), ('group', 'Tax Groups')], string='Impuesto o grupo',default='tax')
	tax_group_ids = fields.Many2many("account.tax.group", string="Grupos")

	@api.model
	def default_get(self, fields):
		result = super(import_bank_statement, self).default_get(fields)
		result['from_date']=datetime.today().replace(day=1)
		result['to_date']=datetime.now()
		result['company_id']=self.env.user.company_id.id
		return result

	def create_worksheet(self, workbook):
		worksheet = workbook.add_worksheet()
		merge_format = workbook.add_format({'bold': 1, 'align': 'center'})
		merge_vat_company = workbook.add_format({'bold': 1, 'align': 'left'})
		fromdate = self.from_date.strftime('%m-%d-%Y')
		todate = self.to_date.strftime('%m-%d-%Y')
		title = "Informe de Impuestos desde %s hasta %s" % (fromdate, todate)
		if self._context.get('multi_currency',False):
			worksheet.merge_range('A1:K1', title, merge_format)
			company_name = "Compañia : " + self.company_id.name
			worksheet.merge_range('A2:K2', company_name, merge_vat_company)
			if self.company_id.vat:
				company_vat = "Nif : " + self.company_id.vat
				worksheet.merge_range('A3:K3', company_vat, merge_vat_company)
		else:
			worksheet.merge_range('A1:H1', title, merge_format)
			company_name = "Compañia : " + self.company_id.name
			worksheet.merge_range('A2:H2', company_name, merge_vat_company)
			if self.company_id.vat:
				company_vat = "Nif : " + self.company_id.vat
				worksheet.merge_range('A3:H3', company_vat, merge_vat_company)
		return worksheet

	def print_header(self, qry_dict, header, worksheet, row, col, tax_type_name, merge_header_format, headerforname,
					 headerforother):
		row += 1
		if self._context.get('multi_currency', False):
			worksheet.merge_range('A%s:K%s' % (row, row), tax_type_name, merge_header_format)
		else:
			worksheet.merge_range('A%s:H%s' % (row, row), tax_type_name, merge_header_format)
		#         row+=1
		for t in header:
			if t in ['Base', 'Impuesto']:
				worksheet.write(row, col, t, headerforname)
			else:
				worksheet.write(row, col, t, headerforother)
			col += 1
		if qry_dict == []:
			row += 2
		return row, worksheet

	# @api.multi
	def get_account_tax_report(self):
		created_file_path = '/tmp/Account Tax Report from %s to %s.xlsx' % (self.from_date, self.to_date)
		workbook = xlsxwriter.Workbook(created_file_path)
		# borders = Borders()
		multi_currency = self.env['res.config.settings'].sudo().default_get('').get('group_multi_currency')
		worksheet = self.with_context(multi_currency=multi_currency).create_worksheet(workbook)
		#         worksheet = workbook.add_sheet("Account Tax Report")
		merge_header_format = workbook.add_format({'bold': 1, 'align': 'center'})
		headerforname = workbook.add_format({'bold': 1, 'align': 'right'})
		headerforother = workbook.add_format({'bold': 1, 'align': 'left'})
		total_format = workbook.add_format({'bold': 1, 'align': 'right', 'pattern': 1, 'font_color': 'white'})
		total_label_format = workbook.add_format({'bold': 1, 'align': 'left', 'pattern': 1, 'font_color': 'white'})
		tax_or_group = self.tax_or_group

		def get_tax(aml):
			credit = aml.get('credit')
			debit = aml.get('debit')
			taxamount = debit - credit
			return taxamount

		def get_amount(aml):
			a_credit = 0
			a_debit = 0
			move_amount = self.env['account.move.line'].browse(aml)
			for line in move_amount.move_id.line_ids:
				if move_amount.tax_line_id in line.tax_ids:
					if not line.tax_line_id:
						a_credit = a_credit + line.credit
						a_debit = a_debit + line.debit
				elif not move_amount.tax_line_id in line.tax_ids:
					account_taxes = self.env['account.tax'].search(
						[('children_tax_ids', 'in', move_amount.tax_line_id.id)])
					for account_tax in account_taxes:
						if account_tax in line.tax_ids:
							if not line.tax_line_id:
								a_credit = a_credit + line.credit
								a_debit = a_debit + line.debit
			#                                 parent_tax_name=account_tax.name

			balance = a_debit - a_credit

			return balance

		def get_name(aml):
			o_name = ''
			move_name = self.env['account.move.line'].browse(aml)
			for line in move_name.move_id.line_ids:
				if move_name.tax_line_id in line.tax_ids:
					if not line.tax_line_id:
						o_name = line.name

			return o_name

		def get_partner(aml):

			move_partner = self.env['account.move.line'].browse(aml)
			partner_name = move_partner.partner_id.name
			if partner_name:
				return partner_name
			else:
				partner_name = ''
				return partner_name

		def get_ref(aml):
			move_ref = self.env['account.move.line'].browse(aml)
			ref_name = move_ref.move_id.name
			return ref_name


		def get_amount_tax_currency(aml,amt):
			move_ref = self.env['account.move.line'].browse(aml)
			amount_currency = move_ref.amount_currency
			if amount_currency==0:
				return amt
			else:
				return amount_currency

		def get_amount_currency(aml,amount):
			amt_cur = 0
			move_amount = self.env['account.move.line'].browse(aml)
			balance=amount
			if not move_amount.amount_currency==0:
				for line in move_amount.move_id.line_ids:
					if move_amount.tax_line_id in line.tax_ids:
						if not line.tax_line_id:
							amt_cur=amt_cur+line.amount_currency
					elif not move_amount.tax_line_id in line.tax_ids:
						account_taxes = self.env['account.tax'].search(
							[('children_tax_ids', 'in', move_amount.tax_line_id.id)])
						for account_tax in account_taxes:
							if account_tax in line.tax_ids:
								if not line.tax_line_id:
									amt_cur = amt_cur + line.amount_currency

				balance = amt_cur

			return balance

		def get_currency(aml):
			move_amount = self.env['account.move.line'].browse(aml)
			if move_amount.currency_id:
				return move_amount.currency_id.name
			else:
				if move_amount.move_id.currency_id:
					return move_amount.move_id.currency_id.name
				else:
					return ''

		row = 5
		at_qry = """select distinct tax_line_id from account_move_line where parent_state = 'posted' AND date BETWEEN '%s' AND '%s' AND company_id=%s and tax_line_id is not null""" % (
			self.from_date, self.to_date, self.company_id.id)
		self._cr.execute(at_qry)
		at_query = self._cr.dictfetchall()
		if tax_or_group == 'tax':
			if self.tax_ids:
				for tax in self.tax_ids:
					qry = """select aml.id,aml.date,aml.account_id,aml.credit,aml.debit,a.amount,aml.amount_currency from account_move_line  aml join account_tax a on a.id=aml.tax_line_id 
		where aml.parent_state = 'posted' AND aml.tax_line_id=%s AND aml.date BETWEEN '%s' AND '%s' AND aml.company_id=%s""" % (
					tax.id, self.from_date, self.to_date, self.company_id.id)
					self._cr.execute(qry)
					qry_dict = self._cr.dictfetchall()
					tax_type_name = tax.name

					header = ['Fecha', 'Asociado', 'Referencia', 'Descripción', 'Cuenta', 'Porc. imp.', 'Base',
							  'Impuesto']
					col = 0
					if multi_currency:
						header = ['Fecha', 'Asociado', 'Referencia', 'Descripción', 'Cuenta', 'Porc. Imp.', 'Base',
							      'Impuesto', 'Base moneda', 'Impuesto moneda', 'moneda']
					row, worksheet = self.with_context(multi_currency=multi_currency).print_header(qry_dict, header, worksheet, row, col, tax_type_name,
													   merge_header_format, headerforname, headerforother)

					amt_tax = 0.0
					amount_total = 0.0

					if qry_dict == []:
						# row += 1
						worksheet.write(row, col, "Total", total_label_format)
						worksheet.write(row, col + 1, "", total_format)
						worksheet.write(row, col + 2, "", total_format)
						worksheet.write(row, col + 3, "", total_format)
						worksheet.write(row, col + 4, "", total_format)
						worksheet.write(row, col + 5, "", total_format)
						worksheet.write(row, col + 6, "", total_format)
						worksheet.write(row, col + 7, "", total_format)
						if multi_currency:
							worksheet.write(row, col + 8, "", total_format)
							worksheet.write(row, col + 9, "", total_format)
							worksheet.write(row, col + 10, "", total_format)
						row += 2
						continue
					for aml in qry_dict:
						row += 1
						col = 0
						print('Desde el primer lugar')
						print(aml)
						o_name = get_name(aml.get('id'))
						date = aml.get('date')
						feeddate = date.strftime('%m-%d-%Y')
						worksheet.write(row, col, feeddate)
						worksheet.set_column('A:A', 10)
						worksheet.set_column('B:B', 13)
						worksheet.set_column('C:C', 15)
						worksheet.set_column('D:D', 35)
						worksheet.set_column('E:E', 20)
						worksheet.set_column('F:F', 10)
						worksheet.set_column('G:G', 15)
						worksheet.set_column('H:H', 15)
						if multi_currency:
							worksheet.set_column('I:I', 20)
							worksheet.set_column('J:J', 15)
							worksheet.set_column('K:K', 10)
						p_name = get_partner(aml.get('id'))
						r_name = get_ref(aml.get('id'))
						account_name = self.env['account.account'].browse(aml.get('account_id')).name
						amount = get_amount(aml.get('id'))

						r_name_number = self.env['account.move'].search([('name', '=', r_name), ('state', '!=', 'draft'), ('state', '!=', 'cancel')])

						if int(get_amount(aml.get('id'))) == 0:
							amount = r_name_number.amount_total
						balance = get_tax(aml)
						worksheet.write(row, col + 1, p_name)
						worksheet.write(row, col + 2, r_name)
						worksheet.write(row, col + 3, o_name)
						worksheet.write(row, col + 4, account_name)
						worksheet.write(row, col + 5, str(aml.get('amount')) + '%')
						worksheet.write(row, col + 6, round((amount), 2))
						worksheet.write(row, col + 7, round(balance, 2))
						if multi_currency:
							amt_cur = get_amount_currency(aml.get('id'), round(amount, 2))
							amt_tax_cur = get_amount_tax_currency(aml.get('id'), round(balance, 2))
							worksheet.write(row, col + 8, amt_cur)
							worksheet.write(row, col + 9, amt_tax_cur)
							worksheet.write(row, col + 10, get_currency(aml.get('id')))
						amt_tax += balance
						amount_total += amount
					row += 1
					worksheet.write(row, col, "Total", total_label_format)
					worksheet.write(row, col + 1, "", total_format)
					worksheet.write(row, col + 2, "", total_format)
					worksheet.write(row, col + 3, "", total_format)
					worksheet.write(row, col + 4, "", total_format)
					worksheet.write(row, col + 5, "", total_format)
					worksheet.write(row, col + 6, round(amount_total, 2), total_format)
					worksheet.write(row, col + 7, round(amt_tax, 2), total_format)
					if multi_currency:
						worksheet.write(row, col + 8, "", total_format)
						worksheet.write(row, col + 9, "", total_format)
						worksheet.write(row, col + 10, "", total_format)
					row += 2

			else:
				for tax in at_query:
					tax_type_name = self.env['account.tax'].browse(tax.get('tax_line_id')).name

					qry = """select aml.id,aml.date,aml.account_id,aml.credit,aml.debit,a.amount,aml.amount_currency from account_move_line  aml join account_tax a on a.id=aml.tax_line_id 
		where aml.parent_state = 'posted' AND aml.tax_line_id=%s AND aml.date BETWEEN '%s' AND '%s' AND aml.company_id=%s""" % (
					tax.get('tax_line_id'), self.from_date, self.to_date, self.company_id.id)
					print('esta es la query : ' + qry)
					self._cr.execute(qry)
					qry_dict = self._cr.dictfetchall()

					header = ['Fecha', 'Asociado', 'Referencia', 'Descripción', 'Cuenta', 'Porc. Imp.', 'Base',
							  'Impuesto']
					col = 0
					if multi_currency:
						header = ['Fecha', 'Asociado', 'Referencia', 'Descripción', 'Cuenta', 'Porc. Imp.', 'Base',
							      'Impuesto', 'Base moneda', 'Impuesto moneda', 'Moneda']
					row, worksheet = self.with_context(multi_currency=multi_currency).print_header(qry_dict, header,
																								   worksheet, row, col,
																								   tax_type_name,
																								   merge_header_format,
																								   headerforname,
																								   headerforother)
					amt_tax = 0.0
					amount_total = 0.0

					for aml in qry_dict:
						print('Desde el segundo lugar')
						print(aml)


						row += 1
						col = 0
						
						o_name = get_name(aml.get('id'))
						print('id del documento')

						date = aml.get('date')
						feeddate = date.strftime('%m-%d-%Y')
						worksheet.write(row, col, feeddate)
						worksheet.set_column('A:A', 10)
						worksheet.set_column('B:B', 13)
						worksheet.set_column('C:C', 15)
						worksheet.set_column('D:D', 35)
						worksheet.set_column('E:E', 20)
						worksheet.set_column('F:F', 10)
						worksheet.set_column('G:G', 15)
						worksheet.set_column('H:H', 15)
						if multi_currency:
							worksheet.set_column('I:I', 20)
							worksheet.set_column('J:J', 15)
							worksheet.set_column('K:K', 10)
						p_name = get_partner(aml.get('id'))
						worksheet.write(row, col + 1, p_name)
						r_name = get_ref(aml.get('id'))
	
						


						worksheet.write(row, col + 2, r_name)
						worksheet.write(row, col + 3, o_name)
						account_name = self.env['account.account'].browse(aml.get('account_id'))
						worksheet.write(row, col + 4, account_name.name)
						worksheet.write(row, col + 5, str(aml.get('amount')) + '%')
						#amount = get_amount(aml.get('id'))
						amount = get_amount(aml.get('id'))

						r_name_number = self.env['account.move'].search([('name', '=', r_name), ('state', '!=', 'draft'), ('state', '!=', 'cancel')])

						if int(get_amount(aml.get('id'))) == 0:
							amount = r_name_number.amount_total



						balance = get_tax(aml)
						#                     final_amount=amount-balance
						worksheet.write(row, col + 6, round(amount, 2))
						#                     balance=aml.get('balance')
						worksheet.write(row, col + 7, round(balance, 2))
						if multi_currency:
							amt_cur = get_amount_currency(aml.get('id'), round(amount, 2))
							amt_tax_cur = get_amount_tax_currency(aml.get('id'), round(balance, 2))
							worksheet.write(row, col + 8, amt_cur)
							worksheet.write(row, col + 9, amt_tax_cur)
							worksheet.write(row, col + 10, get_currency(aml.get('id')))
						amt_tax += balance
						amount_total += amount
					row += 1
					worksheet.write(row, col, "Total", total_label_format)
					worksheet.write(row, col + 1, "", total_format)
					worksheet.write(row, col + 2, "", total_format)
					worksheet.write(row, col + 3, "", total_format)
					worksheet.write(row, col + 4, "", total_format)
					worksheet.write(row, col + 5, "", total_format)
					worksheet.write(row, col + 6, round(amount_total, 2), total_format)
					worksheet.write(row, col + 7, round(amt_tax, 2), total_format)
					if multi_currency:
						worksheet.write(row, col + 8, "", total_format)
						worksheet.write(row, col + 9, "", total_format)
						worksheet.write(row, col + 10, "", total_format)
					row += 2
		elif tax_or_group == 'group':
			if self.tax_group_ids:
				taxes = self.env['account.tax'].search([('tax_group_id', 'in', self.tax_group_ids.ids)])
				if taxes:
					for tax in taxes:
						qry = """select aml.id,aml.date,aml.account_id,aml.credit,aml.debit,a.amount,aml.amount_currency from account_move_line  aml join account_tax a on a.id=aml.tax_line_id 
			where aml.parent_state = 'posted' AND aml.tax_line_id=%s AND aml.date BETWEEN '%s' AND '%s' AND aml.company_id=%s""" % (
						tax.id, self.from_date, self.to_date, self.company_id.id)
						print('esta es la query : ' + qry)
						self._cr.execute(qry)
						qry_dict = self._cr.dictfetchall()
						tax_type_name = tax.name
						if qry_dict == []:
							continue

						header = ['Fecha', 'Asociado', 'Referencia', 'Descripción', 'Cuenta', 'Porc. imp.', 'Base',
							      'Impuesto']
						col = 0
						if multi_currency:
							header = ['Fecha', 'Asociado', 'Referencia', 'Descripción', 'Cuenta', 'Porc. Imp.', 'Base',
							          'Impuesto', 'Base moneda', 'Impuesto moneda', 'Moneda']
						row, worksheet = self.with_context(multi_currency=multi_currency).print_header(qry_dict, header,
																									   worksheet, row,
																									   col,
																									   tax_type_name,
																									   merge_header_format,
																									   headerforname,
																									   headerforother)

						amt_tax = 0.0
						amount_total = 0.0

						for aml in qry_dict:
							print('Desde el tercer lugar')
							print(aml)


							row += 1
							col = 0
							
							o_name = get_name(aml.get('id'))
							date = aml.get('date')
							feeddate = date.strftime('%m-%d-%Y')
							worksheet.write(row, col, feeddate)
							worksheet.set_column('A:A', 10)
							worksheet.set_column('B:B', 13)
							worksheet.set_column('C:C', 15)
							worksheet.set_column('D:D', 35)
							worksheet.set_column('E:E', 20)
							worksheet.set_column('F:F', 10)
							worksheet.set_column('G:G', 15)
							worksheet.set_column('H:H', 15)
							if multi_currency:
								worksheet.set_column('I:I', 20)
								worksheet.set_column('J:J', 15)
								worksheet.set_column('K:K', 10)
							p_name = get_partner(aml.get('id'))
							r_name = get_ref(aml.get('id'))
							account_name = self.env['account.account'].browse(aml.get('account_id'))
							amount = get_amount(aml.get('id'))

							r_name_number = self.env['account.move'].search([('name', '=', r_name), ('state', '!=', 'draft'), ('state', '!=', 'cancel')])

							if int(get_amount(aml.get('id'))) == 0:
								amount = r_name_number.amount_total


							balance = get_tax(aml)
							worksheet.write(row, col + 1, p_name)
							worksheet.write(row, col + 2, r_name)
							worksheet.write(row, col + 3, o_name)
							worksheet.write(row, col + 4, account_name.name)
							worksheet.write(row, col + 5, str(aml.get('amount')) + '%')
							worksheet.write(row, col + 6, round(amount, 2))
							worksheet.write(row, col + 7, round(balance, 2))
							if multi_currency:
								amt_cur = get_amount_currency(aml.get('id'), round(amount, 2))
								amt_tax_cur = get_amount_tax_currency(aml.get('id'), round(balance, 2))
								worksheet.write(row, col + 8, amt_cur)
								worksheet.write(row, col + 9, amt_tax_cur)
								worksheet.write(row, col + 10, get_currency(aml.get('id')))
							amt_tax += balance
							amount_total += amount
						row += 1
						worksheet.write(row, col, "Total", total_label_format)
						worksheet.write(row, col + 1, "", total_format)
						worksheet.write(row, col + 2, "", total_format)
						worksheet.write(row, col + 3, "", total_format)
						worksheet.write(row, col + 4, "", total_format)
						worksheet.write(row, col + 5, "", total_format)
						worksheet.write(row, col + 6, round(amount_total, 2), total_format)
						worksheet.write(row, col + 7, round(amt_tax, 2), total_format)
						if multi_currency:
							worksheet.write(row, col + 8, "", total_format)
							worksheet.write(row, col + 9, "", total_format)
							worksheet.write(row, col + 10, "", total_format)

						row += 2
			else:
				self._cr.execute("""select distinct tax_line_id as id from account_move_line 
		where parent_state = 'posted' AND tax_line_id in (select id from account_tax where tax_group_id in (select id from account_tax_group))
		and date BETWEEN '%s' AND '%s' AND company_id=%s and tax_line_id is not null""" % (
				self.from_date, self.to_date, self.company_id.id))
				grp_taxes = self._cr.fetchall()
				for tax in grp_taxes:
					tax_type_name = self.env['account.tax'].browse(tax[0]).name
					#                 worksheet.write_merge(row,row,0,6,tax_type_name,header_bold)
					#                 row+=1
					#                 header=['Date','Partner','Reference','Name','Account Name','Amount','Tax Amount']
					#                 col=0
					#                 row,worksheet=self.print_header(header,worksheet,row,col,tax_type_name,merge_header_format,headerforname,headerforother)

					qry = """select aml.id,aml.date,aml.account_id,aml.credit,aml.debit,a.amount,aml.amount_currency from account_move_line  aml join account_tax a on a.id=aml.tax_line_id 
		where aml.parent_state = 'posted' AND aml.tax_line_id=%s AND aml.date BETWEEN '%s' AND '%s' AND aml.company_id=%s""" % (
						tax[0], self.from_date, self.to_date, self.company_id.id)
					self._cr.execute(qry)
					qry_dict = self._cr.dictfetchall()
					if qry_dict == []:
						continue

					header = ['Fecha', 'Asociado', 'Referencia', 'Descripción', 'Cuenta', 'Porc. imp.', 'Base',
							  'Impuesto']
					col = 0
					if multi_currency:
						header = ['Fecha', 'Asociado', 'Referencia', 'Descripción', 'Cuenta', 'Porc. Imp.', 'Base',
							      'Impuesto', 'Base moneda', 'Impuesto moneda', 'Moneda']
					row, worksheet = self.with_context(multi_currency=multi_currency).print_header(qry_dict, header,
																								   worksheet, row, col,
																								   tax_type_name,
																								   merge_header_format,
																								   headerforname,
																								   headerforother)

					amt_tax = 0.0
					amount_total = 0.0

					for aml in qry_dict:
						print('Desde el cuarto lugar')
						print(aml)

						row += 1
						col = 0
						
						o_name = get_name(aml.get('id'))
						date = aml.get('date')
						feeddate = date.strftime('%m-%d-%Y')
						worksheet.write(row, col, feeddate)
						worksheet.set_column('A:A', 10)
						worksheet.set_column('B:B', 13)
						worksheet.set_column('C:C', 15)
						worksheet.set_column('D:D', 35)
						worksheet.set_column('E:E', 20)
						worksheet.set_column('F:F', 10)
						worksheet.set_column('G:G', 15)
						worksheet.set_column('H:H', 15)
						if multi_currency:
							worksheet.set_column('I:I', 20)
							worksheet.set_column('J:J', 15)
							worksheet.set_column('K:K', 10)
						p_name = get_partner(aml.get('id'))
						worksheet.write(row, col + 1, p_name)
						r_name = get_ref(aml.get('id'))
						worksheet.write(row, col + 2, r_name)
						worksheet.write(row, col + 3, o_name)
						account_name = self.env['account.account'].browse(aml.get('account_id')).name
						worksheet.write(row, col + 4, account_name)
						worksheet.write(row, col + 5, str(aml.get('amount')) + '%')
						amount = get_amount(aml.get('id'))

						r_name_number = self.env['account.move'].search([('name', '=', r_name), ('state', '!=', 'draft'), ('state', '!=', 'cancel')])

						if int(get_amount(aml.get('id'))) == 0:
							amount = r_name_number.amount_total
						
						balance = get_tax(aml)
						#                     final_amount=amount-balance
						worksheet.write(row, col + 6, round(amount, 2))
						#                     balance=aml.get('balance')
						worksheet.write(row, col + 7, round(balance, 2))
						if multi_currency:
							amt_cur = get_amount_currency(aml.get('id'), round(amount, 2))
							amt_tax_cur = get_amount_tax_currency(aml.get('id'), round(balance, 2))
							worksheet.write(row, col + 8, amt_cur)
							worksheet.write(row, col + 9, amt_tax_cur)
							worksheet.write(row, col + 10, get_currency(aml.get('id')))
						amt_tax += balance
						amount_total += amount
					row += 1
					worksheet.write(row, col, "Total", total_label_format)
					worksheet.write(row, col + 1, "", total_format)
					worksheet.write(row, col + 2, "", total_format)
					worksheet.write(row, col + 3, "", total_format)
					worksheet.write(row, col + 4, "", total_format)
					worksheet.write(row, col + 5, "", total_format)
					worksheet.write(row, col + 6, round(amount_total, 2), total_format)
					worksheet.write(row, col + 7, round(amt_tax, 2), total_format)
					if multi_currency:
						worksheet.write(row, col + 8, "", total_format)
						worksheet.write(row, col + 9, "", total_format)
						worksheet.write(row, col + 10, "", total_format)
					row += 2
		workbook.close()
		file = open(created_file_path, 'rb')
		report_data_file = base64.encodebytes(file.read())
		file.close()
		self.write({'datas': report_data_file})
		return {
			'type': 'ir.actions.act_url',
			'url': '/web/binary/download_document?model=account.tax.reports&field=datas&id=%s&filename=Account Tax Report from %s to %s.xlsx' % (
				self.id, self.from_date, self.to_date),
			'target': 'self',
			#              'type': 'ir.actions.act_window_close'
		}

	# @api.multi
	def get_account_tax_report_summary(self):

		workbook = xlwt.Workbook()
		borders = Borders()
		worksheet = workbook.add_sheet("Account Tax Report")
		header_bold = xlwt.easyxf("font: bold on, height 220;alignment:horizontal center")
		headerforname = xlwt.easyxf("font: bold on, height 210; alignment:horizontal right")
		headerforother = xlwt.easyxf("font: bold on, height 210;alignment:horizontal left")
		Total_bold = xlwt.easyxf("font: bold on, height 200; pattern: pattern solid; alignment:horizontal right")
		Total_pos = xlwt.easyxf("font: bold on, height 200; pattern: pattern solid; alignment:horizontal left")
		fromdate = self.from_date.strftime('%m-%d-%Y')
		todate = self.to_date.strftime('%m-%d-%Y')
		title = "Resumen de impuesto desde %s hasta %s" % (fromdate, todate)
		worksheet.write_merge(0, 1, 0, 2, title, header_bold)
		company_name = "Compañia : " + self.company_id.name
		worksheet.write_merge(2, 2, 0, 2, company_name, headerforother)
		if self.company_id.vat:
			company_vat = "Nif : " + self.company_id.vat
			worksheet.write_merge(3, 3, 0, 2, company_vat, headerforother)
		tax_or_group = self.tax_or_group

		def get_summary_taxamount(qry_dict):
			credit = 0
			debit = 0
			taxamount = 0
			for aml in qry_dict:
				credit = aml.get('credit')
				debit = aml.get('debit')
				taxamount += (debit - credit)

			return taxamount

		def get_amount(qry_dict):

			credit = 0
			debit = 0
			amount = 0
			for aml in qry_dict:
				id = aml.get('id')
				t_credit = 0
				t_debit = 0
				move_amount = self.env['account.move.line'].browse(id)
				line_amount = 0.0
				for line in move_amount.move_id.line_ids:
					if move_amount.tax_line_id in line.tax_ids:
						if not line.tax_line_id:
							t_credit = t_credit + line.credit
							t_debit = t_debit + line.debit

					elif not move_amount.tax_line_id in line.tax_ids:
						account_taxes = self.env['account.tax'].search(
							[('children_tax_ids', 'in', move_amount.tax_line_id.id)])
						for account_tax in account_taxes:
							if account_tax in line.tax_ids:
								if not line.tax_line_id:
									t_credit = t_credit + line.credit
									t_debit = t_debit + line.debit
					line_amount = t_debit - t_credit
				amount += line_amount
			return amount

		row = 5
		col = 0

		tax_type_qry = """select distinct type_tax_use from account_tax"""
		self._cr.execute(tax_type_qry)
		tax_query = self._cr.dictfetchall()
		# Tax wise separation
		for tax_type in tax_query:

			set_tax = tax_type.get('type_tax_use')
			capital_sale = 'Impuestos de Venta'
			capital_purchase = 'Impuestos de Compra'

			if set_tax == 'sale':
				worksheet.write_merge(row, row, 0, 2, capital_sale, header_bold)
			elif set_tax == 'purchase':
				worksheet.write_merge(row, row, 0, 2, capital_purchase, header_bold)
			else:
				worksheet.write_merge(row, row, 0, 2, 'Impuestos sin tipo', header_bold)

			header = ['Nombre de Impuesto', 'Base', 'Impuesto']
			row += 1
			col = 0
			for t in header:
				if t in ['Base', 'Impuesto']:
					worksheet.write(row, col, t, headerforname)
				else:
					worksheet.write(row, col, t, headerforother)
				col += 1
			row += 1
			am = 0
			tax_am = 0
			if tax_or_group == 'tax':
				# if set_tax=='sale':
				#     worksheet.write_merge(row, row, 0, 2, capital_sale, header_bold)
				#     header = ['Tax', 'Amount', 'Tax Amount']
				#     row += 1
				#     col = 0
				#     for t in header:
				#         if t in ['Amount', 'Tax Amount']:
				#             worksheet.write(row, col, t, headerforname)
				#         else:
				#             worksheet.write(row, col, t, headerforother)
				#         col += 1
				#     row += 1
			# process if condition if user select particular tax in wizard otherwise generate the report that includes all taxes
				if self.tax_ids:
					taxes = self.env['account.tax'].search(
						[('id', 'in', self.tax_ids.ids), ('type_tax_use', '=', set_tax)])
					for tax in taxes:
						if tax.type_tax_use == set_tax:

							qry = """select id,credit,debit from account_move_line where parent_state = 'posted' AND tax_line_id=%s AND date BETWEEN '%s' AND '%s' AND company_id=%s""" % (
							tax.id, self.from_date, self.to_date, self.company_id.id)
							self._cr.execute(qry)
							qry_dict = self._cr.dictfetchall()
							tax_type_name = tax.name
							col = 0
							worksheet.write(row, col, tax_type_name)
							worksheet.col(0).width = 7500
							worksheet.col(1).width = 3500
							worksheet.col(2).width = 3500
							# call method for getting total sum of balance
							amount = get_amount(qry_dict)
							worksheet.write(row, col + 1, round(amount, 2))
							am = am + amount
							# call method for getting total sum of taxes
							taxamount = get_summary_taxamount(qry_dict)
							worksheet.write(row, col + 2, round(taxamount, 2))
							tax_am = tax_am + taxamount

							row += 1
						else:
							continue
					else:
						col = 0
						worksheet.write(row, col, "Total", Total_pos)
						worksheet.write(row, col + 1, round(am, 2), Total_bold)
						worksheet.write(row, col + 2, round(tax_am, 2), Total_bold)
						row += 2

				else:
					at_qry = """select distinct tax_line_id from account_move_line  aml join account_tax at on at.id=aml.tax_line_id
	where aml.parent_state = 'posted' AND aml.date BETWEEN '%s' AND '%s' AND aml.company_id=%s and aml.tax_line_id is not null
	and at.type_tax_use='%s'""" % (
						self.from_date, self.to_date, self.company_id.id, set_tax)
					self._cr.execute(at_qry)
					at_query = self._cr.dictfetchall()

					for tax in at_query:
						tax_type_use = self.env['account.tax'].browse(tax.get('tax_line_id')).type_tax_use
						if tax_type_use == set_tax:

							tax_type_name = self.env['account.tax'].browse(tax.get('tax_line_id')).name
							col = 0
							worksheet.write(row, col, tax_type_name)

							qry = """select id,credit,debit from account_move_line where parent_state = 'posted' AND tax_line_id=%s AND date BETWEEN '%s' AND '%s' AND company_id=%s""" % (
							tax.get('tax_line_id'), self.from_date, self.to_date, self.company_id.id)
							self._cr.execute(qry)
							qry_dict = self._cr.dictfetchall()
							worksheet.col(0).width = 7500
							worksheet.col(1).width = 3500
							worksheet.col(2).width = 3500
							# call method for getting total sum of balance
							amount = get_amount(qry_dict)
							worksheet.write(row, col + 1, round(amount, 2))
							am = am + amount
							# call method for getting total sum of taxes
							taxamount = get_summary_taxamount(qry_dict)
							worksheet.write(row, col + 2, round(taxamount, 2))
							tax_am = tax_am + taxamount
							row += 1
						else:
							continue
					else:
						col = 0
						worksheet.write(row, col, "Total", Total_pos)
						worksheet.write(row, col + 1, round(am, 2), Total_bold)
						worksheet.write(row, col + 2, round(tax_am, 2), Total_bold)
						row += 2

			elif tax_or_group == 'group':
				if self.tax_group_ids:
					taxes = self.env['account.tax'].search(
						[('tax_group_id', 'in', self.tax_group_ids.ids), ('type_tax_use', '=', set_tax)])
					for tax in taxes:
						if tax.type_tax_use == set_tax:

							qry = """select id,credit,debit from account_move_line where parent_state = 'posted' AND tax_line_id=%s AND date BETWEEN '%s' AND '%s' AND company_id=%s""" % (
								tax.id, self.from_date, self.to_date, self.company_id.id)
							self._cr.execute(qry)
							qry_dict = self._cr.dictfetchall()
							tax_type_name = tax.name
							col = 0
							worksheet.write(row, col, tax_type_name)
							worksheet.col(0).width = 7500
							worksheet.col(1).width = 3500
							worksheet.col(2).width = 3500
							# call method for getting total sum of balance
							amount = get_amount(qry_dict)
							worksheet.write(row, col + 1, round(amount, 2))
							am = am + amount
							# call method for getting total sum of taxes
							taxamount = get_summary_taxamount(qry_dict)
							worksheet.write(row, col + 2, round(taxamount, 2))
							tax_am = tax_am + taxamount

							row += 1
						else:
							continue
					else:
						col = 0
						worksheet.write(row, col, "Total", Total_pos)
						worksheet.write(row, col + 1, round(am, 2), Total_bold)
						worksheet.write(row, col + 2, round(tax_am, 2), Total_bold)
						row += 2
				else:
					self._cr.execute(
						"""select id from account_tax where tax_group_id in (select id from account_tax_group) and type_tax_use='%s'""" % (
							set_tax))
					grp_taxes = self._cr.fetchall()
					for tax in grp_taxes:
						tax_type_use = self.env['account.tax'].browse(tax[0]).type_tax_use
						if tax_type_use == set_tax:

							tax_type_name = self.env['account.tax'].browse(tax[0]).name
							col = 0
							worksheet.write(row, col, tax_type_name)

							qry = """select id,credit,debit from account_move_line where parent_state = 'posted' AND tax_line_id=%s AND date BETWEEN '%s' AND '%s' AND company_id=%s""" % (
								tax[0], self.from_date, self.to_date, self.company_id.id)
							self._cr.execute(qry)
							qry_dict = self._cr.dictfetchall()
							worksheet.col(0).width = 7500
							worksheet.col(1).width = 3500
							worksheet.col(2).width = 3500
							# call method for getting total sum of balance
							amount = get_amount(qry_dict)
							worksheet.write(row, col + 1, round(amount, 2))
							am = am + amount
							# call method for getting total sum of taxes
							taxamount = get_summary_taxamount(qry_dict)
							worksheet.write(row, col + 2, round(taxamount, 2))
							tax_am = tax_am + taxamount
							row += 1
						else:
							continue
					else:
						col = 0
						worksheet.write(row, col, "Total", Total_pos)
						worksheet.write(row, col + 1, round(am, 2), Total_bold)
						worksheet.write(row, col + 2, round(tax_am, 2), Total_bold)
						row += 2
		fp = BytesIO()
		workbook.close(fp)
		fp.seek(0)
		report_data_file = base64.encodebytes(fp.read())
		fp.close()
		self.write({'datas': report_data_file})
		return {
			'type': 'ir.actions.act_url',
			'url': '/web/binary/download_document?model=account.tax.reports&field=datas&id=%s&filename=Account Summary Report from %s to %s.xls' % (
			self.id, self.from_date, self.to_date),
			'target': 'self',
		}