from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import os
from datetime import datetime
import base64
import requests
from odoo.tools.float_utils import float_round

TIPO_DOCUMENT0_BANCO_BOGOTA = {
	'id_document': 'C',
	'national_citizen_id': 'C',
	'rut': 'N',
	'id_card': 'T',
	'passport': 'P',
	'foreign_id_card': 'E',
}

TIPO_DOCUMENT0_BANCOLOMBIA = {
	'id_document': '1',
	'national_citizen_id': '1',
	'rut': '3',
	'id_card': '4',
	'passport': '5',
	'foreign_id_card': '2',
}

TIPO_DOCUMENT0_DAVIVIENDA = {
	'id_document': '02',
	'national_citizen_id': '02',
	'rut': '01',
	'id_card': '03',
	'passport': '05',
	'foreign_id_card': '04',
}

TIPO_DOCUMENT0_BBVA = {
	'id_document': '01',
	'national_citizen_id': '01',
	'rut': '03',
	'id_card': '04',
	'passport': '05',
	'foreign_id_card': '02',
}

TIPO_DOCUMENT0_BANCO_AGRARIO = {
	'id_document': '1',
	'national_citizen_id': '1',
	'rut': '3',
	'id_card': '7',
	'passport': '6',
	'foreign_id_card': '2',
}

TIPO_TRANSACCION_BANCOLOMBIA = {
	'S': '37',
	'D': '27',
}

TIPO_CUENTA_DAVIVIENDA = {
	'saving': 'CA',
	'current': 'CC',
}

TIPO_CUENTA_BBVA = {
	'saving': '0200',
	'current': '0100',
}

TIPO_CUENTA_BANCOLOMBIA = {
	'saving': 'S',
	'current': 'D',
}

TIPO_CUENTA_BANCOBOGOTA = {
	'saving': '02',
	'current': '01',
}

TIPO_CUENTA_BANCO_AGRARIO = {
	'saving': '4',
	'current': '3',
}


class AccountPayment(models.Model):
	_inherit = 'account.payment.ce'

	def _get_method_codes_using_bank_account(self):
		res = super(AccountPayment, self)._get_method_codes_using_bank_account()
		res.append('manual')
		return res

	def _get_method_codes_needing_bank_account(self):
		res = super(AccountPayment, self)._get_method_codes_needing_bank_account()
		res.append('manual')
		return res

	def generar_archivo_banco(self):
		bank = []
		for rec in self:
			if rec.journal_id.type != 'bank' or not rec.journal_id.bank_account_id:
				raise UserError(_("Solo puede generar el archivo para"
								  " pagos de banco"))
			bank.append(rec.journal_id.bank_id.bic)
		for rec in self:
			if rec.partner_type == 'customer':
				raise UserError(_("Solo puede generar el archivo para"
								  " pagos de proveedor"))
		try:
			if all([x == '001' for x in bank]):
				file_path = self.banco_bogota()
			elif all([x == '007' for x in bank]):
				file_path = self.bancolombia()
			elif all([x == '051' for x in bank]):
				file_path = self.davivienda()
			elif all([x == '013' for x in bank]):
				file_path = self.bbva()
			elif all([x == '040' for x in bank]):
				file_path = self.banco_agrario()
			else:
				raise UserError(_("Verifique que los pagos seleccionados"
								  " sean del mismo banco"))

			base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', default='http://localhost:8069')
			if base_url:
				base_url += '/' + file_path['path']

			if '.txt' in file_path['name']:
				my_txt = requests.get(base_url).content
				files = self.env['ir.attachment'].search([('access_token', '=', 'APBPETI'), ('name', '=', file_path['name'])], limit=1)
				if files:
					files.write({'datas': base64.b64encode(my_txt)})
					file_id = files.id
					file_name = files.name
				else:
					file_txt = self.env['ir.attachment'].create({
						'mimetype': 'text/plain',
						'datas': base64.b64encode(my_txt),
						'name': file_path['name'],
						'type': 'binary',
						'access_token': 'APBPETI'
					})
					file_id = file_txt.id
					file_name = file_txt.name
				action = {
					'type': 'ir.actions.act_url',
					'url': "web/content/?model=ir.attachment&id=" + str(
						file_id) + "&filename_field=name&field=datas&download=true&name=" + file_name,
					'target': 'new'
				}
				return action
			else:
				return {
					'type': 'ir.actions.act_url',
					'url': base_url,
					'target': 'new',
				}
		except:
			raise UserError(_("Verifique que la información de la empresa "
							  " y de los proveedores esté correcta"
							  " (Numeros de documento, Numeros de cuenta, Direccion...)"))

	def banco_bogota(self):
		for rec in self:
			if rec.partner_type == 'customer':
				raise UserError(_("Solo puede generar el archivo para"
								  " pagos de proveedor"))
		path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
		in_module_path = 'static\\src\\file_bank\\'
		file_name = 'banco_bogota.txt'
		try:
			os.stat(os.path.join(path, in_module_path))
		except:
			os.makedirs(os.path.join(path, in_module_path))

		txt_path = os.path.join(path, (in_module_path + str(file_name)))
		file = open(txt_path, "w")
		file.write("1")
		file.write(datetime.now().strftime('%Y-%m-%d').replace('-', ''))
		file.write("0".ljust(23, "0"))
		file.write(TIPO_CUENTA_BANCOBOGOTA.get(self.journal_id.bank_account_id.accountbank_type))
		file.write(self.journal_id.bank_account_id.acc_number.zfill(17))
		file.write(self.journal_id.bank_account_id.company_id.name.ljust(40))
		file.write(self.GetNitCompany(self.journal_id.bank_account_id.company_id.partner_id.vat_co).ljust(11, "0"))
		file.write("002")
		file.write(self.journal_id.bank_account_id.company_id.city_id.code[-4:].rjust(4, "0"))
		file.write(datetime.now().strftime('%Y-%m-%d').replace('-', ''))
		file.write(self.journal_id.bank_account_id.acc_number[0:3])
		file.write(TIPO_DOCUMENT0_BANCO_BOGOTA.get(
			self.journal_id.bank_account_id.company_id.partner_id.l10n_latam_identification_type_id.l10n_co_document_code))
		file.write("".ljust(129))
		for rec in self:
			file.write("\n")
			file.write("2")
			file.write(TIPO_DOCUMENT0_BANCO_BOGOTA.get(rec.partner_id.l10n_latam_identification_type_id.l10n_co_document_code))
			file.write(rec.GetNitCompany(rec.partner_id.vat_co).ljust(11, "0"))
			file.write(rec.partner_id.name.ljust(40))
			# file.write(TIPO_CUENTA_BANCOBOGOTA.get(rec.partner_id.bank_ids.accountbank_type))
			file.write(TIPO_CUENTA_BANCOBOGOTA.get(rec.partner_bank_id.accountbank_type))
			# file.write(rec.partner_id.bank_ids.acc_number.ljust(17))
			file.write(rec.partner_bank_id.acc_number.ljust(17))
			file.write(f"{rec.amount:.2f}".replace(".", "").rjust(18, "0"))
			file.write("A")
			file.write("000")
			# file.write(rec.partner_id.bank_ids.bank_id.bic)
			file.write(rec.partner_bank_id.bank_id.bic)
			file.write("0000")
			mensaje = rec.journal_id.bank_account_id.company_id.name + " PAGO"
			file.write(mensaje.ljust(80))
			file.write("0")
			file.write("0000000000")
			file.write("N")
			file.write("".ljust(48))
			file.write("N")
			file.write("".ljust(8))

		file.close()
		file_path = 'account_bank_payment_file/static/src/file_bank/%s?download=true' % file_name
		return {'path': file_path, 'name': file_name}

	def bancolombia(self):
		for rec in self:
			if rec.partner_type == 'customer':
				raise UserError(_("Solo puede generar el archivo para"
								  " pagos de proveedor"))
		path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
		in_module_path = 'static\\src\\file_bank\\'
		file_name = 'bancolombia.txt'
		try:
			os.stat(os.path.join(path, in_module_path))
		except:
			os.makedirs(os.path.join(path, in_module_path))

		txt_path = os.path.join(path, (in_module_path + str(file_name)))
		file = open(txt_path, "w")
		file.write("1")
		file.write(self.GetNitCompany(self.journal_id.bank_account_id.company_id.partner_id.vat_co).ljust(10, "0"))
		file.write(self.journal_id.bank_account_id.company_id.name[0:16].ljust(16))
		file.write("220")
		file.write("PAGO".ljust(10))
		file.write(datetime.now().strftime('%y-%m-%d').replace('-', ''))
		file.write("A")
		file.write(datetime.now().strftime('%y-%m-%d').replace('-', ''))
		file.write(str(len(self)).rjust(6, "0"))
		file.write("0".ljust(12, "0"))
		sum_total = sum(rec.amount for rec in self)
		file.write(str(round(sum_total)).rjust(12, "0"))
		file.write(self.journal_id.bank_account_id.acc_number.zfill(11))
		file.write(TIPO_CUENTA_BANCOLOMBIA.get(self.journal_id.bank_account_id.accountbank_type))

		for rec in self:
			file.write("\n")
			file.write("6")
			file.write(rec.GetNitCompany(rec.partner_id.vat_co).rjust(15, "0"))
			file.write(rec.partner_id.name.ljust(18))
			# file.write(rec.partner_id.bank_ids.bank_id.bic.rjust(9, "0"))
			file.write(rec.partner_bank_id.bank_id.bic.rjust(9, "0"))
			# file.write(rec.partner_id.bank_ids.acc_number.rjust(17, "0"))
			file.write(rec.partner_bank_id.acc_number.rjust(17, "0"))
			file.write("S")
			# tipo_cuenta = TIPO_CUENTA_BANCOLOMBIA.get(rec.partner_id.bank_ids.accountbank_type)
			tipo_cuenta = TIPO_CUENTA_BANCOLOMBIA.get(rec.partner_bank_id.accountbank_type)
			file.write(TIPO_TRANSACCION_BANCOLOMBIA.get(tipo_cuenta))
			file.write(str(round(rec.amount)).rjust(10, "0"))
			file.write("  00000")
			file.write(TIPO_DOCUMENT0_BANCOLOMBIA.get(rec.partner_id.l10n_latam_identification_type_id.l10n_co_document_code))
			file.write(" ")
			file.write(rec.ref[0:12].ljust(12))
			file.write(" ")

		file.close()
		file_path = 'account_bank_payment_file/static/src/file_bank/%s?download=true' % file_name
		return {'path': file_path, 'name': file_name}

	def davivienda(self):
		for rec in self:
			if rec.partner_type == 'customer':
				raise UserError(_("Solo puede generar el archivo para"
								  " pagos de proveedor"))
		path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
		in_module_path = 'static\\src\\file_bank\\'
		file_name = 'davivienda.csv'
		try:
			os.stat(os.path.join(path, in_module_path))
		except:
			os.makedirs(os.path.join(path, in_module_path))

		txt_path = os.path.join(path, (in_module_path + str(file_name)))
		file = open(txt_path, "w")
		file.write("RC")
		file.write(self.GetNitCompany(self.journal_id.bank_account_id.company_id.partner_id.vat_co).rjust(16, "0"))
		file.write("PROV")
		file.write("0000")
		file.write(self.journal_id.bank_account_id.acc_number.rjust(16, "0"))
		file.write(TIPO_CUENTA_DAVIVIENDA.get(self.journal_id.bank_account_id.accountbank_type))
		file.write(self.journal_id.bank_account_id.bank_id.bic.rjust(6, "0"))
		sum_total = sum(rec.amount for rec in self)
		file.write(f"{sum_total:.2f}".replace(".", "").rjust(18, "0"))
		file.write(str(len(self)).rjust(6, "0"))
		file.write(datetime.now().strftime('%Y-%m-%d').replace('-', ''))
		file.write(datetime.now().strftime('%H:%M:%S').replace(':', ''))
		file.write("0000")
		file.write("9999")
		file.write("00000000")
		file.write("000000")
		file.write("00")
		file.write(
			TIPO_DOCUMENT0_DAVIVIENDA.get(self.journal_id.bank_account_id.company_id.partner_id.l10n_latam_identification_type_id.l10n_co_document_code))
		file.write("000000000000")
		file.write("0000")
		file.write("".rjust(40, "0"))

		for rec in self:
			file.write("\n")
			file.write("TR")
			file.write(rec.GetNitCompany(rec.partner_id.vat_co).rjust(16, "0"))
			file.write("".rjust(16, "0"))
			file.write(rec.partner_bank_id.acc_number.rjust(16, "0"))
			file.write(TIPO_CUENTA_DAVIVIENDA.get(rec.partner_bank_id.accountbank_type))
			file.write(rec.partner_bank_id.bank_id.bic.rjust(6, "0"))
			file.write(f"{rec.amount:.2f}".replace(".", "").rjust(18, "0"))
			file.write("000000")
			file.write(TIPO_DOCUMENT0_DAVIVIENDA.get(rec.partner_id.l10n_latam_identification_type_id.l10n_co_document_code))
			file.write("1")
			file.write("9999")
			file.write("".rjust(40, "0"))
			file.write("".rjust(18, "0"))
			file.write("".rjust(8, "0"))
			file.write("".rjust(4, "0"))
			file.write("".rjust(4, "0"))
			file.write("".rjust(7, "0"))

		file.close()
		file_path = 'account_bank_payment_file/static/src/file_bank/%s?download=true' % file_name
		return {'path': file_path, 'name': file_name}

	def bbva(self):
		for rec in self:
			if rec.partner_type == 'customer':
				raise UserError(_("Solo puede generar el archivo para"
								  " pagos de proveedor"))
		path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
		in_module_path = 'static\\src\\file_bank\\'
		file_name = 'bbva.csv'
		try:
			os.stat(os.path.join(path, in_module_path))
		except:
			os.makedirs(os.path.join(path, in_module_path))

		txt_path = os.path.join(path, (in_module_path + str(file_name)))
		file = open(txt_path, "w")

		for rec in self:
			file.write(TIPO_DOCUMENT0_BBVA.get(rec.partner_id.l10n_latam_identification_type_id.l10n_co_document_code))
			file.write(rec.GetNitCompany(rec.partner_id.vat_co).rjust(16, "0"))
			file.write("1")
			# file.write(rec.partner_id.bank_ids.bank_id.bic.rjust(4, "0"))
			file.write(rec.partner_bank_id.bank_id.bic.rjust(4, "0"))
			# if rec.partner_id.bank_ids.bank_id.bic == "013":
			if rec.partner_bank_id.bank_id.bic == "013":
				# file.write(rec.partner_id.bank_ids.office_code.rjust(4, "0"))
				file.write(rec.partner_bank_id.office_code.rjust(4, "0"))
				file.write("00")
				# file.write(TIPO_CUENTA_BBVA.get(rec.partner_id.bank_ids.accountbank_type))
				file.write(TIPO_CUENTA_BBVA.get(rec.partner_bank_id.accountbank_type))
				# file.write(rec.partner_id.bank_ids.acc_number[-6:].rjust(6, "0"))
				file.write(rec.partner_bank_id.acc_number[-6:].rjust(6, "0"))
				file.write("00")
			else:
				file.write("0".rjust(16, "0"))
				# file.write(TIPO_CUENTA_BBVA.get(rec.partner_id.bank_ids.accountbank_type)[0:2])
				file.write(TIPO_CUENTA_BBVA.get(rec.partner_bank_id.accountbank_type)[0:2])
			# file.write(rec.partner_id.bank_ids.acc_number.rjust(17, "0"))
			file.write(rec.partner_bank_id.acc_number.rjust(17, "0"))
			file.write(f"{rec.amount:.2f}".replace(".", "").rjust(15, "0"))
			file.write("00000000")
			file.write("0000")
			file.write(rec.partner_id.name[0:36].rjust(36))
			file.write(rec.partner_id.contact_address_complete[0:36].rjust(36))
			file.write("".rjust(36))
			file.write("".rjust(48))
			file.write("PAGO".ljust(40))
			file.write("".rjust(840))
			file.write("\n")

		file.close()
		file_path = 'account_bank_payment_file/static/src/file_bank/%s?download=true' % file_name
		return {'path': file_path, 'name': file_name}

	def banco_agrario(self):
		for rec in self:
			if rec.partner_type == 'customer':
				raise UserError(_("Solo puede generar el archivo para"
								  " pagos de proveedor"))
		path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
		in_module_path = 'static\\src\\file_bank\\'
		file_name = 'banco_agrario.txt'
		try:
			os.stat(os.path.join(path, in_module_path))
		except:
			os.makedirs(os.path.join(path, in_module_path))

		txt_path = os.path.join(path, (in_module_path + str(file_name)))
		file = open(txt_path, "w")

		for rec in self:
			# cuenta = rec.partner_id.bank_ids.filtered(lambda x: x.bank_default)
			cuenta = rec.partner_bank_id.filtered(lambda x: x.bank_default)
			# file.write(rec.partner_id.bank_ids.bank_id.bic.rjust(4, "0"))
			file.write(rec.partner_bank_id.bank_id.bic.rjust(4, "0"))
			file.write(rec.GetNitCompany(rec.partner_id.vat_co).rjust(15, " "))
			file.write(TIPO_DOCUMENT0_BANCO_AGRARIO.get(rec.partner_id.l10n_latam_identification_type_id.l10n_co_document_code))
			# file.write(rec.partner_id.bank_ids.acc_number.rjust(17, " "))
			file.write(rec.partner_bank_id.acc_number.rjust(17, " "))
			# file.write(TIPO_CUENTA_BANCO_AGRARIO.get(rec.partner_id.bank_ids.accountbank_type))
			file.write(TIPO_CUENTA_BANCO_AGRARIO.get(rec.partner_bank_id.accountbank_type))
			file.write(rec.partner_id.name[0:30].ljust(30))
			file.write(f"{rec.amount:.2f}".replace(".", ",").rjust(15, "0"))
			file.write("PAGO".ljust(42))
			file.write("\n")

		file.close()
		file_path = 'account_bank_payment_file/static/src/file_bank/%s?download=true' % file_name
		return {'path': file_path, 'name': file_name}

	def GetNitCompany(self, number):
		document = ''
		try:
			if '-' in number:
				document = number[0:number.find('-')]
			else:
				document = number
			return document
		except:
			return document

	def _get_code_city(self, city):
		code = ''
		if len(city.code) > 4:
			code = city.code[-4:]
		return code



class AccountMove(models.Model):
	_inherit = 'account.move'

	@api.onchange('partner_id')
	def _onchange_partner_id(self):
		res = super(AccountMove, self)._onchange_partner_id()
		if self.bank_partner_id.bank_ids:
			self.partner_bank_id = self.bank_partner_id.bank_ids.filtered(
				lambda m: m.bank_default == True) or self.bank_partner_id.bank_ids and self.bank_partner_id.bank_ids[0]
		return res


class ResPartnerBank(models.Model):
	_inherit = 'res.partner.bank'

	def name_get(self):
		result = []
		for bank in self:
			name = bank.acc_number + ' ' + (bank.bank_id.name if bank.bank_id.name else '')
			result.append((bank.id, name))
		return result

class ResPartner(models.Model):
	_inherit = 'res.partner'

	@api.constrains('bank_ids')
	def check_banks(self):
		for partner in self:
			default=[]
			for rec in partner.bank_ids:
				if rec.bank_default:
					default.append(rec.bank_default)
			if len(default) > 1:
				raise UserError(_("Solo puede tener una cuenta bancaria predeterminada"))

class ResPartnerBank(models.Model):
	_inherit = 'res.partner.bank'

	office_code = fields.Char(string='Codigo Oficina', Help='Codigo de la oficina receptora solo aplica BBVA')
	bank_default = fields.Boolean(string='Cuenta predeterminada',
								  Help='Esta cuenta se usara de manera predeterminada para los pagos')
