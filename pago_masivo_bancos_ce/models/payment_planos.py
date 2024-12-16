from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import os
from datetime import datetime
import base64
import requests
from odoo.tools.float_utils import float_round
import xlwt
import io
import xlsxwriter
import math
import logging
_logger = logging.getLogger(__name__)

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

TIPO_CUENTA_DAVIVIENDA = {
	'A': 'CA',
	'C': 'CC',
    'OP': 'OP',
    'DP': 'DP',
    'TP': 'TP',
}

TIPO_CUENTA_BANCOITAU = {
	'A': 'AHO',
	'C': 'CTE',
    'DP': 'DEP',
}

TIPO_CUENTA_BANCOBOGOTA = {
	'A': '02',
	'C': '01',
}
class AccountPayment(models.Model):
    _inherit = 'account.payment.ce'

    type_file = fields.Selection([
        ('1', 'Archivo Plano'),
        ('2', 'Excel')
    ], string='Archivo a generar', required=True, default='1')
    format_file = fields.Selection([('bancolombia', 'Bancolombia SAP'),
                                    ('bancolombia_pab', 'Bancolombia PAB'),
                                    ('davivienda', 'Banco Davivienda'),
                                    ('bbva', 'Banco BBVA'),
                                    ('bogota', 'Banco Bogota'),
                                    ('agrario', 'Banco Agrario'),
                                    ('itau', 'Banco itau'),
                                    ('occired', 'Occired')
                                    ], string='Tipo de plano', required=True, default='bancolombia')

    vat_payer = fields.Char(string='NIT Pagador', store=True, readonly=True,
                            related='journal_id.company_id.partner_id.vat', change_default=True)
    payment_type_bnk = fields.Selection([
                                        ('220', 'Pago a Proveedores'),
                                        ('225', 'Pago de Nómina'),
                                        ('238', 'Pagos a Terceros'),
                                        ('239', 'Abono Obligatorio con el Bco'),
                                        ('240', 'Pagos Cuenta Maestra'),
                                        ('320', 'Credipago a Proveedores'),
                                        ], string='Tipo de pago', required=True, default='220')
    application = fields.Selection([
        ('I', 'Inmediata'),
        ('M', 'Medio día'),
        ('N', 'Noche')
    ], string='Aplicación', required=True)
    sequence = fields.Char(string='Secuencia de envío', size=2, required=True)
    account_debit = fields.Char(string='Nro. Cuenta a debitar', store=True, readonly=True,
                                related='journal_id.bank_account_id.acc_number', change_default=True)
    account_type_debit = fields.Selection([
        ('S', 'Ahorros'),
        ('D', 'Corriente')
    ], string='Tipo de cuenta a debitar', required=True)
    description = fields.Char(
        string='Descripción del pago', size=10, required=True)

    # Retonar columnas

    def get_columns_encab(self):
        columns = 'NIT PAGADOR,TIPO DE PAGO,APLICACIÓN,SECUENCIA DE ENVÍO,NRO CUENTA A DEBITAR,TIPO DE CUENTA A DEBITAR,DESCRIPCIÓN DEL PAGO'
        _columns = columns.split(",")
        return _columns

    def get_columns_detail(self):
        columns = 'Tipo Documento Beneficiario,Nit Beneficiario,Nombre Beneficiario,Tipo Transaccion,Código Banco,No Cuenta Beneficiario,Email,Documento Autorizado,Referencia,OficinaEntrega,ValorTransaccion,Fecha de aplicación,Digito de Verificación'
        _columns = columns.split(",")
        return _columns

    def get_columns_detail_davivienda(self):
        columns = 'Tipo de identificación,Número de identificación,Nombre,Apellido,Código del Banco,Tipo de Producto o Servicio,Número del Producto o Servicio,Valor del pago o de la recarga,Referencia,Correo Electrónico,Descripción o Detalle'
        _columns = columns.split(",")
        return _columns
    # Ejecutar consulta SQL

    def run_sql(self):

        # Fecha actual
        date_today = fields.Date.context_today(self)

        # Obtener Pagos
        payments_ids = ''
        for payment_id in self.payment_ids:
            id = payment_id.id
            if payments_ids == '':
                payments_ids = str(id)
            else:
                payments_ids = payments_ids+','+str(id)

        #raise ValidationError(_(payments_ids))

        # Consulta final
        query = '''
            SELECT distinct coalesce(case when t.l10n_co_document_code = '12' then '4' --Tarjeta de Identidad
                            when t.l10n_co_document_code = 'id_document'  then '1'  --Cedula de ciudadania
                            when t.l10n_co_document_code = 'national_citizen_id' then '1' --Cedula de ciudadania
                            when t.l10n_co_document_code = 'foreign_id_card' then '2' --Cdeula de extranjeria
                            when t.l10n_co_document_code = 'rut' then '3' --NIT
                            when t.l10n_co_document_code = 'id_card' then '4' 
                            when t.l10n_co_document_code = 'passport' then '5' --Pasaporte
                            when t.l10n_co_document_code = 'foreign_resident_card' then '2' --Cdeula de extranjeria
                    else '' end,'') as TipoDocumentoBeneficiario,
                    coalesce(b.vat_co,'') AS NitBeneficiario,
                    coalesce(substring(b."name" from 1 for 30),'') AS NombreBeneficiario,
                    coalesce(case WHEN f.type_account = 'C' then '27'WHEN f.type_account = 'A' then '37'else null end,'') AS TipoTransaccion,
                    coalesce(d.bic,coalesce(g.bic,'')) AS Banco,
                    coalesce(f.acc_number,'') AS NoCuentaBeneficiario,
                    coalesce(b.email,''),
                    coalesce(substring(a.num_autorizaciones from 6 for 21),'') AS DocumentoAutorizado,
                    coalesce(substring(m.ref from 1 for 21),'') AS Referencia,'' AS OficinaEntrega,
                    coalesce(a.amount,0) AS ValorTransaccion,
                    coalesce(cast(extract(year from m.date) AS varchar) || lpad(extract(month from m.date)::text, 2, '0') ||  lpad(extract(day from m.date)::text, 2, '0'),'') AS FechaAplicacion,
                    coalesce(cast(b.dv AS varchar),'') AS DigitoNitBeneficiario
            FROM account_payment a
            INNER join res_partner b on a.partner_id = b.id
            LEFT join account_move m on a.move_id = m.id
            LEFT join res_partner_bank c on a.partner_bank_id = c.id 
            LEFT join res_bank d on c.bank_id = d.id
            LEFT join res_partner_bank f on b.id = f.partner_id and f.is_main = true and f.company_id = %s 
            LEFT join res_bank g on f.bank_id = g.id
            LEFT join l10n_latam_identification_type t on b.l10n_latam_identification_type_id = t.id
            WHERE partner_type = 'supplier' and a.id in (%s)
        ''' % (self.env.company.id, payments_ids)

        self._cr.execute(query)
        _res = self._cr.dictfetchall()
        return _res

    def validate_info_bank(self, vat_co, name, bank):
        if bank == '':
            raise ValidationError(
                _(f'El tercero {vat_co}-{name} no tiene información bancaria o no esta marcada como principal para la compañía {self.env.company.name}, por favor verificar.'))

    # Actualizar Pagos
    def update_payments(self):
        pass
        # values_update = {
        # 'x_payment_file' : True
        # }
        # for payment in self.payment_ids:
        #     payment.update(values_update)

    # Lógica de bancolombia SAP
    def get_excel_bancolombia(self):

        if self.payment_type_bnk != '220':
            raise ValidationError(
                _('El tipo de pago seleccionado no esta desarrollado por ahora, seleccione otro por favor.'))

        result_columns_encab = self.get_columns_encab()
        result_columns_detail = self.get_columns_detail()
        result_query = self.run_sql()

        # Logica Archivo Plano
        if self.type_file == '1':
            filename = 'Archivo de Pago '+str(self.description)+'.txt'
            filler = ' '

            def left(s, amount):
                return s[:amount]

            def right(s, amount):
                return s[-amount:]

            # Encabezado - parte 1
            tipo_registro_encab = '1'
            vat_payer = str(self.vat_payer).split("-")
            nit_entidad_originadora = right('0'*10+vat_payer[0], 10)
            #aplicaicon = self.application
            #filler_one = 15*filler
            name_company = left(self.journal_id.company_id.name+16*filler, 16)
            clase_de_transaccion = self.payment_type_bnk
            descripcion_proposito = left(self.description+10*filler, 10)

            date_today = fields.Date.context_today(self)
            fecha_transmision = right('0000'+str(date_today.year), 2)+right(
                '00'+str(date_today.month), 2)+right('00'+str(date_today.day), 2)

            secuencia_envio = left(self.sequence+filler, 1)
            fecha_aplicacion = fecha_transmision
            numero_registro = 'NumRegs'
            sumatoria_debitos = '0'*12
            sumatoria_creditos = 'SumatoriaCreditos'
            cuenta_cliente = right(
                '00000000000'+str(self.account_debit).replace("-", ""), 11)
            tipo_cuenta = self.account_type_debit

            encab_content_txt = '''%s%s%s%s%s%s%s%s%s%s%s%s%s''' % (tipo_registro_encab, nit_entidad_originadora, name_company, clase_de_transaccion, descripcion_proposito,
                                                                    fecha_transmision, secuencia_envio, fecha_aplicacion, numero_registro, sumatoria_debitos, sumatoria_creditos, cuenta_cliente, tipo_cuenta)

            # Detalle
            det_content_txt = ''''''
            tipo_registro_det = '6'
            indicador_lugar = 'S'
            numero_fax = 15*filler
            numero_identificacion_autorizado = 15*filler
            filler_three = 27*filler

            columns = 0
            cant_detalle = 0
            total_valor_transaccion = 0.0
            # Agregar query
            for query in result_query:
                cant_detalle = cant_detalle + 1
                for row in query.values():
                    if columns == 0:
                        TipoDocumentoBeneficiario = right('0'*1+row, 1)
                    if columns == 1:
                        nit_beneficiario = right('0'*15+row, 15)
                    if columns == 2:
                        nombre_beneficiario = left(row+18*filler, 18)
                    if columns == 3:
                        tipo_transaccion = right('  '+row, 2)
                    if columns == 4:
                        self.validate_info_bank(
                            nit_beneficiario, nombre_beneficiario, row)
                        banco_destino = right('000000000'+row, 9)
                    if columns == 5:
                        no_cuenta_beneficiario = right('0'*17+row, 17)
                    if columns == 6:
                        email = left(row+80*filler, 80)
                    if columns == 7:
                        documento_autorizado = row
                    if columns == 8:
                        referencia = left(row+21*filler, 21)
                    if columns == 9:
                        oficina_entrega = '0'*5
                    if columns == 10:
                        total_valor_transaccion = total_valor_transaccion + row
                        parte_decimal, parte_entera = math.modf(row)
                        parte_entera = str(parte_entera).split(".")
                        parte_decimal = str(parte_decimal).split(".")
                        # +left(str(parte_decimal[1])+'00',2)
                        valor_transaccion = right(
                            '0'*10+str(parte_entera[0]), 10)
                    if columns == 11:
                        fecha_aplicacion = row

                    columns = columns + 1
                columns = 0

                content_line = '''%s%s%s%s%s%s%s%s%s%s%s''' % (TipoDocumentoBeneficiario, tipo_registro_det, nit_beneficiario, nombre_beneficiario,
                                                               banco_destino, no_cuenta_beneficiario, indicador_lugar, tipo_transaccion, valor_transaccion, referencia, filler)
                if cant_detalle == 1:
                    det_content_txt = content_line
                else:
                    det_content_txt = det_content_txt + '\n' + content_line

            # Encabezado - parte 2
            encab_content_txt = encab_content_txt.replace(
                "NumRegs", right('000000000'+str(cant_detalle), 6))
            parte_decimal, parte_entera = math.modf(total_valor_transaccion)
            parte_entera = str(parte_entera).split(".")
            parte_decimal = str(parte_decimal).split(".")
            encab_content_txt = encab_content_txt.replace("SumatoriaCreditos", right(
                '0'*12+str(parte_entera[0]), 12))  # +left(str(parte_decimal[1])+'00',2)

            # Unir Encabezado y Detalle
            content_txt = encab_content_txt + '\n' + det_content_txt

            # Crear archivo
            self.write({
                'txt_file': base64.encodebytes((content_txt).encode()),
                'txt_file_name': filename,
            })

            action = {
                'name': 'ArchivoPagos',
                        'type': 'ir.actions.act_url',
                        'url': "web/content/?model=account.payment.ce&id=" + str(self.id) + "&filename_field=txt_file_name&field=txt_file&download=true&filename=" + self.txt_file_name,
                        'target': 'self',
            }
            return action

        # Logica Excel
        if self.type_file == '2':
            filename = 'Archivo de Pago '+str(self.description)+'.xlsx'
            stream = io.BytesIO()
            book = xlsxwriter.Workbook(stream, {'in_memory': True})
            sheet = book.add_worksheet('FORMATOPAB')

            # Estilos - https://xlsxwriter.readthedocs.io/format.html

            ##Encabezado - Encab
            cell_format_header = book.add_format(
                {'bold': True, 'font_color': 'white'})
            cell_format_header.set_bg_color('#34839b')
            cell_format_header.set_font_name('Calibri')
            cell_format_header.set_font_size(11)
            cell_format_header.set_align('center')
            cell_format_header.set_align('vcenter')

            ##Detalle - Encab
            cell_format_det = book.add_format()
            cell_format_det.set_font_name('Calibri')
            cell_format_det.set_font_size(11)

            # Campos númericos monetarios
            number_format = book.add_format({'num_format': '#,##'})
            number_format.set_font_name('Calibri')
            number_format.set_font_size(11)

            # Campos tipo número
            number = book.add_format()
            number.set_num_format(0)
            number.set_font_name('Calibri')
            number.set_font_size(11)

            # Agregar columnas - Encab
            aument_columns = 0
            for columns in result_columns_encab:
                sheet.write(0, aument_columns, columns, cell_format_header)
                aument_columns = aument_columns + 1

            # Agregar fila - Encab
            vat_payer = str(self.vat_payer).split("-")
            sheet.write(1, 0, vat_payer[0], number)
            sheet.write(1, 1, self.payment_type_bnk, number)
            sheet.write(1, 2, self.application, cell_format_det)
            sheet.write(1, 3, self.sequence, cell_format_det)
            sheet.write(1, 4, str(self.account_debit).replace("-", ""), number)
            sheet.write(1, 5, self.account_type_debit, cell_format_det)
            sheet.write(1, 6, self.description, cell_format_det)

            # Agregar columnas - Detail
            aument_columns = 0
            for columns in result_columns_detail:
                sheet.write(2, aument_columns, columns, cell_format_header)
                aument_columns = aument_columns + 1

            # Agregar query
            aument_columns = 0
            aument_rows = 3
            for query in result_query:
                for row in query.values():
                    if aument_columns == 2 or aument_columns == 8:
                        row = str(row).replace("/", "")
                        row = str(row).replace(".", "")
                        row = str(row).replace(",", "")
                        row = str(row).replace(":", "")
                        row = str(row).replace(";", "")

                    if aument_columns == 10:
                        sheet.write(aument_rows, aument_columns,
                                    row, number_format)
                    else:
                        sheet.write(aument_rows, aument_columns,
                                    row, cell_format_det)
                    aument_columns = aument_columns + 1
                aument_rows = aument_rows + 1
                aument_columns = 0

            # Tamaño columnas
            sheet.set_column('A:B', 25)
            sheet.set_column('C:C', 30)
            sheet.set_column('D:D', 25)
            sheet.set_column('E:F', 40)
            sheet.set_column('G:G', 50)
            sheet.set_column('H:L', 25)

            book.close()

            # Actualizar pagos
            self.update_payments()

            # Crear archivo
            self.write({
                'excel_file': base64.encodebytes(stream.getvalue()),
                'excel_file_name': filename,
            })

            action = {
                'name': 'ArchivoPagos',
                        'type': 'ir.actions.act_url',
                        'url': "web/content/?model=account.payment.ce&id=" + str(self.id) + "&filename_field=excel_file_name&field=excel_file&download=true&filename=" + self.excel_file_name,
                        'target': 'self',
            }
            return action

    # Lógica de bancolombia PAB
    def get_excel_bancolombia_pab(self):

        if self.payment_type_bnk != '220':
            raise ValidationError(
                _('El tipo de pago seleccionado no esta desarrollado por ahora, seleccione otro por favor.'))

        result_columns_encab = self.get_columns_encab()
        result_columns_detail = self.get_columns_detail()
        result_query = self.run_sql()

        # Logica Archivo Plano
        if self.type_file == '1':
            filename = 'Archivo de Pago '+str(self.description)+'.txt'
            filler = ' '

            def left(s, amount):
                return s[:amount]

            def right(s, amount):
                return s[-amount:]

            # Encabezado - parte 1
            tipo_registro_encab = '1'
            vat_payer = str(self.vat_payer).split("-")
            nit_entidad_originadora = right('0'*15+vat_payer[0], 15)
            application = self.application
            filler_one = 15*filler
            clase_de_transaccion = self.payment_type_bnk
            descripcion_proposito = left(self.description+10*filler, 10)
            date_today = fields.Date.context_today(self)
            fecha_transmision = right('0000'+str(date_today.year), 4)+right(
                '00'+str(date_today.month), 2)+right('00'+str(date_today.day), 2)
            secuencia_envio = right('00'+self.sequence, 2)
            fecha_aplicacion = fecha_transmision
            num_registros = 'NumRegs'  # Mas adelante se reeemplaza con el valor correcto
            sum_debitos = 17*'0'
            sum_creditos = 'SumCreditos'  # Mas adelante se reeemplaza con el valor correcto
            cuenta_cliente = right(
                11*'0'+str(self.account_debit).replace("-", ""), 11)
            tipo_cuenta = self.account_type_debit
            filler_two = filler*149

            encab_content_txt = '%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s' % (tipo_registro_encab, nit_entidad_originadora, application, filler_one, clase_de_transaccion,
                                                                    descripcion_proposito, fecha_transmision, secuencia_envio, fecha_aplicacion, num_registros, sum_debitos, sum_creditos, cuenta_cliente, tipo_cuenta, filler_two)

            # Detalle
            det_content_txt = ''
            tipo_registro_det = '6'
            indicador_lugar = 'S'
            numero_fax = 15*filler
            numero_identificacion_autorizado = 15*filler
            filler_three = 27*filler

            columns = 0
            cant_detalle = 0
            total_valor_transaccion = 0.0
            # Agregar query
            for query in result_query:
                cant_detalle = cant_detalle + 1
                for row in query.values():
                    if columns == 0:
                        tipo_documento = row
                    if columns == 1:
                        nit_beneficiario = left(row+15*filler, 15)
                    if columns == 2:
                        nombre_beneficiario = left(row+30*filler, 30)
                    if columns == 3:
                        tipo_transaccion = right('  '+row, 2)
                    if columns == 4:
                        self.validate_info_bank(
                            nit_beneficiario, nombre_beneficiario, row)
                        banco_destino = right('000000000'+row, 9)
                    if columns == 5:
                        no_cuenta_beneficiario = left(row+' '*17, 17)
                    if columns == 6:
                        email = left(row+80*filler, 80)
                    if columns == 7:
                        documento_autorizado = row
                    if columns == 8:
                        referencia = left(row+21*filler, 21)
                    if columns == 9:
                        oficina_entrega = '0'*5
                    if columns == 10:
                        total_valor_transaccion = total_valor_transaccion + row
                        parte_decimal, parte_entera = math.modf(row)
                        parte_entera = str(parte_entera).split(".")
                        parte_decimal = str(parte_decimal).split(".")
                        # left(str(parte_decimal[0])+'00',2)
                        valor_transaccion = right(
                            '0'*15+str(parte_entera[0]), 15)+'00'
                    if columns == 11:
                        fecha_aplicacion = row

                    columns = columns + 1
                columns = 0

                content_line = '%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s' % (tipo_registro_det, nit_beneficiario, nombre_beneficiario, banco_destino, no_cuenta_beneficiario, indicador_lugar,
                                                                     tipo_transaccion, valor_transaccion, fecha_aplicacion, referencia, tipo_documento, oficina_entrega, numero_fax, email, numero_identificacion_autorizado, filler_three)

                if cant_detalle == 1:
                    det_content_txt = content_line
                else:
                    det_content_txt = det_content_txt + '\n' + content_line

            # Encabezado - parte 2
            encab_content_txt = encab_content_txt.replace(
                "NumRegs", right(6*'0'+str(cant_detalle), 6))
            parte_decimal, parte_entera = math.modf(total_valor_transaccion)
            parte_entera = str(parte_entera).split(".")
            parte_decimal = str(parte_decimal).split(".")
            encab_content_txt = encab_content_txt.replace("SumCreditos", right(
                '0'*15+str(parte_entera[0]), 15)+'00')  # left(str(parte_decimal[0])+'00',2)

            # Unir Encabezado y Detalle
            content_txt = encab_content_txt + '\n' + det_content_txt

            # Actualizar pagos
            self.update_payments()

            # Crear archivo
            self.write({
                'txt_file': base64.encodebytes((content_txt).encode()),
                # base64.encodebytes((content).encode()).decode().strip()
                'txt_file_name': filename,
            })

            action = {
                'name': 'ArchivoPagos',
                        'type': 'ir.actions.act_url',
                        'url': "web/content/?model=account.payment.ce&id=" + str(self.id) + "&filename_field=txt_file_name&field=txt_file&download=true&filename=" + self.txt_file_name,
                        'target': 'self',
            }
            return action

        # Logica Excel
        if self.type_file == '2':
            raise ValidationError(
                _('El formato Bancolombia PAB no posee vista de excel.'))

    # Lógica de occired
    def get_excel_occired(self):

        if self.payment_type_bnk != '220':
            raise ValidationError(
                _('El tipo de pago seleccionado no esta desarrollado por ahora, seleccione otro por favor.'))

        result_columns_encab = self.get_columns_encab()
        result_columns_detail = self.get_columns_detail()
        result_query = self.run_sql()

        # Logica Archivo Plano
        if self.type_file == '1':
            filename = 'Archivo de Pago '+str(self.description)+'.txt'
            filler = ' '

            def left(s, amount):
                return s[:amount]

            def right(s, amount):
                return s[-amount:]

            # Encabezado - parte 1
            tipo_registro_encab = '1'
            consecutivo = '0000'
            date_today = self.payment_date
            fecha_pago = str(date_today.year)+right('00' +
                                                    str(date_today.month), 2)+right('00'+str(date_today.day), 2)
            numero_registro = 'NumRegs'
            valor_total = 'ValTotal'
            cuenta_principal = right(
                16*'0'+str(self.account_debit).replace("-", ""), 16)
            identificacion_del_archivo = 6*'0'
            ceros = 142*'0'
            encab_content_txt = '''%s%s%s%s%s%s%s%s''' % (
                tipo_registro_encab, consecutivo, fecha_pago, numero_registro, valor_total, cuenta_principal, identificacion_del_archivo, ceros)
            # Detalle
            det_content_txt = ''''''
            tipo_registro_det = '2'
            columns = 0
            cant_detalle = 0
            total_valor_transaccion = 0.0
            # Agregar query
            for query in result_query:
                cant_detalle = cant_detalle + 1
                consecutivo = right('0000'+str(cant_detalle), 4)
                # 1: Pago en Cheque  2: Pago abono a cuenta  - Banco de Occidente  3: Abono a cuenta otras entidades
                forma_de_pago = '3'
                for row in query.values():
                    if columns == 0:
                        tipo_documento = row
                    if columns == 1:
                        nit_beneficiario = right(11*'0'+row, 11)
                    if columns == 2:
                        nombre_beneficiario = left(row+30*filler, 30)
                    if columns == 3:
                        tipo_transaccion = 'A' if row == '37' else 'A'
                        tipo_transaccion = 'C' if row == '27' else tipo_transaccion
                    if columns == 4:
                        self.validate_info_bank(
                            nit_beneficiario, nombre_beneficiario, row)
                        banco_destino = '0'+right(3*'0'+row, 3)
                        forma_de_pago = '2' if row == '1023' else forma_de_pago
                    if columns == 5:
                        no_cuenta_beneficiario = left(
                            str(row).replace("-", "")+filler*16, 16)
                    if columns == 6:
                        email = left(row+80*filler, 80)
                    if columns == 7:
                        numbers = [temp for temp in row.split(
                            "/") if temp.isdigit()]
                        documento_autorizado = ''
                        for i in numbers:
                            documento_autorizado = documento_autorizado + \
                                str(i)
                        documento_autorizado = right(
                            filler*12+documento_autorizado, 12)
                    if columns == 8:
                        referencia = left(row+80*filler, 80)
                    if columns == 9:
                        oficina_entrega = '0'*5
                    if columns == 10:
                        total_valor_transaccion = total_valor_transaccion + \
                            round(row, 0)
                        parte_decimal, parte_entera = math.modf(round(row, 0))
                        parte_entera = str(parte_entera).split(".")
                        parte_decimal = str(parte_decimal).split(".")
                        # left(str(parte_decimal[1])+'00',2)
                        valor_transaccion = right(
                            13*'0'+str(parte_entera[0]), 13)+'00'
                    if columns == 11:
                        fecha_aplicacion = row
                    if columns == 12:
                        digito_verificacion = str(row)
                        if str(tipo_documento) == '3':
                            nit_beneficiario = right(
                                11*'0'+str(nit_beneficiario)+str(digito_verificacion), 11)

                    columns = columns + 1
                columns = 0

                content_line = '''%s%s%s%s%s%s%s%s%s%s%s%s%s''' % (tipo_registro_det, consecutivo, cuenta_principal, nombre_beneficiario, nit_beneficiario,
                                                                   banco_destino, fecha_pago, forma_de_pago, valor_transaccion, no_cuenta_beneficiario, documento_autorizado, tipo_transaccion, referencia)
                if cant_detalle == 1:
                    det_content_txt = content_line
                else:
                    det_content_txt = det_content_txt + '\n' + content_line

            # Encabezado - parte 2
            encab_content_txt = encab_content_txt.replace(
                "NumRegs", right('0000'+str(cant_detalle), 4))
            parte_decimal, parte_entera = math.modf(total_valor_transaccion)
            parte_entera = str(parte_entera).split(".")
            parte_decimal = str(parte_decimal).split(".")
            encab_content_txt = encab_content_txt.replace("ValTotal", right(
                16*'0'+str(parte_entera[0]), 16)+'00')  # left(str(parte_decimal[1])+'00',2))

            # Totales
            tipo_registro_tot = '3'
            secuencia = '9999'
            numero_registro = right('0000'+str(cant_detalle), 4)
            parte_decimal, parte_entera = math.modf(total_valor_transaccion)
            parte_entera = str(parte_entera).split(".")
            parte_decimal = str(parte_decimal).split(".")
            # left(str(parte_decimal[1])+'00',2)
            valor_total = right(16*'0'+str(parte_entera[0]), 16)+'00'
            ceros = 172*'0'

            tot_content_txt = '''%s%s%s%s%s''' % (
                tipo_registro_tot, secuencia, numero_registro, valor_total, ceros)

            # Unir Encabezado, Detalle y Totales
            content_txt = encab_content_txt + '\n' + \
                det_content_txt + '\n' + tot_content_txt

            # Actualizar pagos
            self.update_payments()

            # Crear archivo
            self.write({
                'txt_file': base64.encodebytes((content_txt).encode()),
                # base64.encodebytes((content).encode()).decode().strip()
                'txt_file_name': filename,
            })

            action = {
                'name': 'ArchivoPagos',
                        'type': 'ir.actions.act_url',
                        'url': "web/content/?model=account.payment.ce&id=" + str(self.id) + "&filename_field=txt_file_name&field=txt_file&download=true&filename=" + self.txt_file_name,
                        'target': 'self',
            }
            return action

        # Logica Excel
        if self.type_file == '2':
            raise ValidationError(
                _('El formato Occired no posee vista de excel.'))

    # Ejecutar consulta SQL
    def run_sql_davivienda(self):

        # Fecha actual
        date_today = fields.Date.context_today(self)

        # Obtener Pagos
        payments_ids = ''
        for payment_id in self.payment_ids:
            id = payment_id.id
            if payments_ids == '':
                payments_ids = str(id)
            else:
                payments_ids = payments_ids+','+str(id)
        query = '''
            SELECT distinct coalesce(case when t.l10n_co_document_code = '12' then '4' --Tarjeta de Identidad
                            when t.l10n_co_document_code = 'id_document'  then '02'  --Cedula de ciudadania
                            when t.l10n_co_document_code = 'national_citizen_id' then '02' --Cedula de ciudadania
                            when t.l10n_co_document_code = 'foreign_id_card' then '04' --Cdeula de extranjeria
                            when t.l10n_co_document_code = 'rut' then '01' --NIT
                            when t.l10n_co_document_code = 'id_card' then '03' --NIT
                            when t.l10n_co_document_code = 'passport' then '05' --Pasaporte
                            when t.l10n_co_document_code = 'foreign_resident_card' then '04' --Cdeula de extranjeria
                    else '' end,'') as TipoDocumentoBeneficiario,
                coalesce(b.vat_co,'' ) AS NitBeneficiario,
                coalesce(b.name,'') AS NombreBeneficiario,
                coalesce(b.last_name,'') AS ApellidoBenef,
                coalesce(d.bic,coalesce(g.bic,'')) AS Banco,
                coalesce(case WHEN f.type_account = 'C' then 'CC' 
                                WHEN f.type_account = 'A' then 'CA'
                                WHEN f.type_account = 'OP' then 'OP'
                                WHEN f.type_account = 'DP' then 'DP'
                                WHEN f.type_account = 'TP' then 'TP'
                                else null end,'') AS TipoTransaccion,
                coalesce(f.acc_number,'') AS NoCuentaBeneficiario,
                coalesce(pay.amount,2) AS ValorTransaccion,
                coalesce(pay.id) AS Referencia,
                coalesce(b.email,'') AS Email,
                coalesce(m.ref,'') AS DocumentoAutorizado
            from account_payment pay
            INNER join res_partner b on pay.partner_id = b.id
            LEFT join account_move m on pay.move_id = m.id
            LEFT join res_partner_bank c on pay.partner_bank_id = c.id 
            LEFT join res_bank d on c.bank_id = d.id
            LEFT join res_partner_bank f on b.id = f.partner_id and f.is_main = true and f.company_id = %s 
            LEFT join res_bank g on f.bank_id = g.id
            LEFT join l10n_latam_identification_type t on b.l10n_latam_identification_type_id = t.id
            WHERE partner_type = 'supplier' and pay.id in (%s)
        ''' % (self.env.company.id, payments_ids)

        self._cr.execute(query)
        _res = self._cr.dictfetchall()
        return _res

    def get_excel_davivienda(self):

        if self.payment_type_bnk != '220':
            raise ValidationError(
                _('El tipo de pago seleccionado no esta desarrollado por ahora, seleccione otro por favor.'))

        result_columns_encab = self.get_columns_encab()
        result_columns_detail = self.get_columns_detail_davivienda()
        result_query = self.run_sql_davivienda()

        # Logica Archivo Plano
        if self.type_file == '1':
            filename = 'Archivo de Pago '+str(self.description)+'.txt'
            filler = ' '

            def left(s, amount):
                return s[:amount]

            def right(s, amount):
                return s[-amount:]

            # Encabezado - parte 1
            tipo_registro_encab = 'RC'
            vat_payer = str(self.vat_payer).split("-")
            nit_entidad_originadora = (vat_payer[0]).rjust(16, "0")
            tipo_operacion = 'PROV'
            tipo_de_cueta = TIPO_CUENTA_DAVIVIENDA.get(self.journal_id.bank_account_id.type_account)
            codigo_de_banco = self.journal_id.bank_account_id.bank_id.bic.rjust(6, "0")
            sum_total = sum(rec.amount for rec in self)
            sum_tolal_format = f"{sum_total:.2f}".replace(".", "").rjust(18, "0")
            numero_total = str(len(self)).rjust(6, "0")
            fecha = datetime.now().strftime('%Y-%m-%d').replace('-', '')
            hora = datetime.now().strftime('%H:%M:%S').replace(':', '')
            cuenta_bnk = (self.account_debit).replace("-", "")
            cuenta_cliente = str(cuenta_bnk).rjust(16, "0")
            operador = '0000'
            Códigono_procesado = '9999'
            fecha_generacion = '00000000'
            hora_generacion = '000000'
            indicador = '00'
            tipo_documento = (TIPO_DOCUMENT0_DAVIVIENDA.get(self.company_id.partner_id.l10n_latam_identification_type_id.l10n_co_document_code))
            relleno = (('0').rjust(56, "0"))
                                    
            encab_content_txt = '''%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s''' % (
                                                                    tipo_registro_encab, #1
                                                                    nit_entidad_originadora, #2
                                                                    tipo_operacion,#3
                                                                    tipo_operacion,#18
                                                                    cuenta_cliente,#4
                                                                    tipo_de_cueta,#5
                                                                    codigo_de_banco,#6
                                                                    sum_tolal_format,#7
                                                                    numero_total,#8
                                                                    fecha,#9
                                                                    hora,#10
                                                                    operador,#11
                                                                    Códigono_procesado,#12
                                                                    fecha_generacion,#13
                                                                    hora_generacion,#14
                                                                    indicador,#15
                                                                    tipo_documento,#16
                                                                    relleno,#17
                                                                    )
            _logger.info('\n\n %r \n\n', encab_content_txt)
            # Detalle
            det_content_txt = ''''''
            tipo_registro_det = '6'
            indicador_lugar = 'S'
            numero_fax = 15*filler
            numero_identificacion_autorizado = 15*filler
            filler_three = 27*filler

            columns = 0
            content_line = ''
            cant_detalle = 0
            total_valor_transaccion = 0.0
            # Agregar query
            for payment_id in self.payment_ids:
                cant_detalle = cant_detalle + 1
                tipo_de_registro = "TR"
                Nit_16 = (payment_id.partner_id.vat_co).rjust(16, "0")
                referencia_16 = (('0').rjust(16, "0"))
                producto_16 = (payment_id.partner_bank_id.acc_number).rjust(16, "0")
                tipo_de_producto_2 = TIPO_CUENTA_DAVIVIENDA.get(payment_id.partner_bank_id.type_account)
                codigo_de_banco_6 = (payment_id.partner_bank_id.bank_id.bic).rjust(6, "0")
                sum_total = payment_id.amount
                sum_tolal_format_18 = f"{sum_total:.2f}".replace(".", "").rjust(18, "0")
                talon = '000000'
                tipo_documento_2 = (TIPO_DOCUMENT0_DAVIVIENDA.get(payment_id.partner_id.l10n_latam_identification_type_id.l10n_co_document_code))
                ach = '1'
                result = '9999'
                relleno_81 = (('0').rjust(81, "0"))
                content_line = '''%s%s%s%s%s%s%s%s%s%s%s%s''' % (tipo_de_registro,
                                                                Nit_16, 
                                                                referencia_16, 
                                                                producto_16,
                                                                tipo_de_producto_2, 
                                                                codigo_de_banco_6, 
                                                                sum_tolal_format_18, 
                                                                talon,
                                                                tipo_documento_2,
                                                                ach,
                                                                result,
                                                                relleno_81,
                                                                )
                if cant_detalle == 1:
                    det_content_txt = content_line
                else:
                    det_content_txt = det_content_txt + '\n' + content_line

            # Unir Encabezado y Detalle
            content_txt = encab_content_txt + '\n' + det_content_txt

            # Crear archivo
            self.write({
                'txt_file': base64.encodebytes((content_txt).encode()),
                'txt_file_name': filename,
            })

            action = {
                'name': 'ArchivoPagos',
                        'type': 'ir.actions.act_url',
                        'url': "web/content/?model=account.payment.ce&id=" + str(self.id) + "&filename_field=txt_file_name&field=txt_file&download=true&filename=" + self.txt_file_name,
                        'target': 'self',
            }
            return action

        # Logica Excel
        if self.type_file == '2':
            filename = 'Archivo de Pago '+str(self.description)+'.xlsx'
            stream = io.BytesIO()
            book = xlsxwriter.Workbook(stream, {'in_memory': True})
            sheet = book.add_worksheet('Banco Davivienda')

            ##Encabezado - Encab
            cell_format_header = book.add_format(
                {'bold': True, 'font_color': 'white'})
            cell_format_header.set_bg_color('#34839b')
            cell_format_header.set_font_name('Calibri')
            cell_format_header.set_font_size(11)
            cell_format_header.set_align('center')
            cell_format_header.set_align('vcenter')

            ##Detalle - Encab
            cell_format_det = book.add_format()
            cell_format_det.set_font_name('Calibri')
            cell_format_det.set_font_size(11)

            # Campos númericos monetarios
            number_format = book.add_format({'num_format': '#,##0.00'})
            number_format.set_font_name('Calibri')
            number_format.set_font_size(11)

            # Campos tipo número
            number = book.add_format({'num_format' : '#,##0.00'})
            number.set_num_format(0)
            number.set_font_name('Calibri')
            number.set_font_size(11)

            # Agregar columnas - Encab
            # aument_columns = 0
            # for columns in result_columns_encab:
            #     sheet.write(0, aument_columns, columns, cell_format_header)
            #     aument_columns = aument_columns + 1

            # #Agregar fila - Encab
            # vat_payer = str(self.vat_payer).split("-")
            # sheet.write(1, 0, vat_payer[0], number)
            # sheet.write(1, 1, self.payment_type_bnk, number)
            # sheet.write(1, 2, self.application, cell_format_det)
            # sheet.write(1, 3, self.sequence, cell_format_det)
            # sheet.write(1, 4, str(self.account_debit).replace("-",""), number)
            # sheet.write(1, 5, self.account_type_debit, cell_format_det)
            # sheet.write(1, 6, self.description, cell_format_det)

            # #Agregar columnas - Detail
            aument_columns = 0
            for columns in result_columns_detail:
                sheet.write(0, aument_columns, columns, cell_format_header)
                aument_columns = aument_columns + 1

            # Agregar query
            aument_columns = 0
            aument_rows = 1
            for query in result_query:
                for row in query.values():
                    if aument_columns == 2 or aument_columns == 8:
                        row = str(row).replace("/", "")
                        row = str(row).replace(".", "")
                        row = str(row).replace(",", "")
                        row = str(row).replace(":", "")
                        row = str(row).replace(";", "")

                    if aument_columns == 7:
                        sheet.write(aument_rows, aument_columns,
                                    row, number_format)
                    else:
                        sheet.write(aument_rows, aument_columns,
                                    row, cell_format_det)
                    aument_columns = aument_columns + 1
                aument_rows = aument_rows + 1
                aument_columns = 0

            # Tamaño columnas
            sheet.set_column('A:B', 25)
            sheet.set_column('C:C', 30)
            sheet.set_column('D:D', 25)
            sheet.set_column('E:F', 40)
            sheet.set_column('G:G', 50)
            sheet.set_column('H:L', 25)

            book.close()

            # Crear archivo
            self.write({
                'excel_file': base64.encodebytes(stream.getvalue()),
                'excel_file_name': filename,
            })

            action = {
                'name': 'ArchivoPagos',
                        'type': 'ir.actions.act_url',
                        'url': "web/content/?model=account.payment.ce&id=" + str(self.id) + "&filename_field=excel_file_name&field=excel_file&download=true&filename=" + self.excel_file_name,
                        'target': 'self',
            }
            return action

    def get_excel_bancobogota(self):
    
        if self.payment_type_bnk != '220':
            raise ValidationError(
                _('El tipo de pago seleccionado no esta desarrollado por ahora, seleccione otro por favor.'))

        result_columns_detail = self.get_columns_detail_davivienda()
        result_query = self.run_sql_davivienda()

        # Logica Archivo Plano
        if self.type_file == '1':
            filename = 'Archivo de Pago '+str(self.description)+'.txt'
            
            # Encabezado - parte 1
            tipo_registro_encab = '1'
            fecha = datetime.now().strftime('%Y-%m-%d').replace('-', '')
            void = "0".ljust(23, "0")
            tipo_de_cueta = TIPO_CUENTA_BANCOBOGOTA.get(self.journal_id.bank_account_id.type_account).rjust(2, "0")
            acc_number = self.journal_id.bank_account_id.acc_number.zfill(17)
            company_name = self.journal_id.bank_account_id.company_id.name.ljust(40)
            vat_payer = str(self.vat_payer).split("-")
            nit_entidad_originadora = (self.company_id.partner_id.vat_co).rjust(16, "0")
            city = self.company_id.partner_id.city_id.code[-4:].rjust(4, "0")
            acc_number_code = self.journal_id.bank_account_id.acc_number[0:3]
            tipo_documento = (TIPO_DOCUMENT0_BANCO_BOGOTA.get(self.company_id.partner_id.l10n_latam_identification_type_id.l10n_co_document_code))
            relleno = (''.ljust(129))
            encab_content_txt = '''%s%s%s%s%s%s%s%s%s%s%s%s%s''' % (
                                                                    tipo_registro_encab, #1
                                                                    fecha,#2
                                                                    void, #3
                                                                    tipo_de_cueta, #4
                                                                    acc_number, #5
                                                                    company_name, #6
                                                                    nit_entidad_originadora, #7
                                                                    "002", #8
                                                                    city, #9
                                                                    fecha, #10
                                                                    acc_number_code, #11
                                                                    tipo_documento, #12
                                                                    relleno #13
                                                                    )
            _logger.info('\n\n %r \n\n', encab_content_txt)
            # Detalle
            det_content_txt = ''''''

            columns = 0
            content_line = ''
            cant_detalle = 0
            
            # Agregar query
            for payment_id in self.payment_ids:
                cant_detalle = cant_detalle + 1
                tipo_de_registro = "2"
                tipo_id_benefit = TIPO_DOCUMENT0_BANCO_BOGOTA.get(payment_id.partner_id.l10n_latam_identification_type_id.l10n_co_document_code)
                nit = (payment_id.partner_id.vat_co).ljust(11, "0")
                name= (payment_id.partner_id.name).ljust(40)
                tipo_de_producto = TIPO_CUENTA_BANCOBOGOTA.get(payment_id.partner_bank_id.type_account)
                producto = (payment_id.partner_bank_id.acc_number).ljust(17)
                relleno = (f"{payment_id.amount:.2f}".replace(".", "").rjust(18, "0"))
                codigo_de_banco = (payment_id.partner_bank_id.bank_id.bic).rjust(3, "0")
                mensaje = payment_id.company_id.name + " PAGO"
                mensaje = mensaje.ljust(79)

                content_line = '''%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s''' % (
                                                                tipo_de_registro, #1
                                                                tipo_id_benefit, #2
                                                                nit, #3
                                                                name,
                                                                tipo_de_producto, #4
                                                                producto, #5
                                                                relleno, #6
                                                                "A", #7
                                                                "000",  #8
                                                                codigo_de_banco, #9
                                                                "0000", #10
                                                                mensaje, #11
                                                                "0", #12
                                                                "0000000000", #13
                                                                "N", #14
                                                                "".ljust(48), #15
                                                                "N", #16
                                                                "".ljust(10) #17
                                                                )
                if cant_detalle == 1:
                    det_content_txt = content_line
                else:
                    det_content_txt = det_content_txt + '\n' + content_line

            # Unir Encabezado y Detalle
            content_txt = encab_content_txt + '\n' + det_content_txt

            # Crear archivo
            self.write({
                'txt_file': base64.encodebytes((content_txt).encode()),
                'txt_file_name': filename,
            })

            action = {
                'name': 'ArchivoPagos',
                        'type': 'ir.actions.act_url',
                        'url': "web/content/?model=account.payment.ce&id=" + str(self.id) + "&filename_field=txt_file_name&field=txt_file&download=true&filename=" + self.txt_file_name,
                        'target': 'self',
            }
            return action

        # Logica Excel
        if self.type_file == '2':
            raise ValidationError(
                _('El tipo de pago seleccionado no esta desarrollado por ahora, seleccione otro por favor.'))

            # filename = 'Archivo de Pago '+str(self.description)+'.xlsx'
            # stream = io.BytesIO()
            # book = xlsxwriter.Workbook(stream, {'in_memory': True})
            # sheet = book.add_worksheet('Banco De Bogota')

            # ##Encabezado - Encab
            # cell_format_header = book.add_format(
            #     {'bold': True, 'font_color': 'white'})
            # cell_format_header.set_bg_color('#34839b')
            # cell_format_header.set_font_name('Calibri')
            # cell_format_header.set_font_size(11)
            # cell_format_header.set_align('center')
            # cell_format_header.set_align('vcenter')

            # ##Detalle - Encab
            # cell_format_det = book.add_format()
            # cell_format_det.set_font_name('Calibri')
            # cell_format_det.set_font_size(11)

            # # Campos númericos monetarios
            # number_format = book.add_format({'num_format': '#,##0.00'})
            # number_format.set_font_name('Calibri')
            # number_format.set_font_size(11)

            # # Campos tipo número
            # number = book.add_format({'num_format' : '#,##0.00'})
            # number.set_num_format(0)
            # number.set_font_name('Calibri')
            # number.set_font_size(11)

            # # Agregar columnas - Encab
            # # aument_columns = 0
            # # for columns in result_columns_encab:
            # #     sheet.write(0, aument_columns, columns, cell_format_header)
            # #     aument_columns = aument_columns + 1

            # # #Agregar fila - Encab
            # # vat_payer = str(self.vat_payer).split("-")
            # # sheet.write(1, 0, vat_payer[0], number)
            # # sheet.write(1, 1, self.payment_type_bnk, number)
            # # sheet.write(1, 2, self.application, cell_format_det)
            # # sheet.write(1, 3, self.sequence, cell_format_det)
            # # sheet.write(1, 4, str(self.account_debit).replace("-",""), number)
            # # sheet.write(1, 5, self.account_type_debit, cell_format_det)
            # # sheet.write(1, 6, self.description, cell_format_det)

            # # #Agregar columnas - Detail
            # aument_columns = 0
            # for columns in result_columns_detail:
            #     sheet.write(0, aument_columns, columns, cell_format_header)
            #     aument_columns = aument_columns + 1

            # # Agregar query
            # aument_columns = 0
            # aument_rows = 1
            # for query in result_query:
            #     for row in query.values():
            #         if aument_columns == 2 or aument_columns == 8:
            #             row = str(row).replace("/", "")
            #             row = str(row).replace(".", "")
            #             row = str(row).replace(",", "")
            #             row = str(row).replace(":", "")
            #             row = str(row).replace(";", "")

            #         if aument_columns == 7:
            #             sheet.write(aument_rows, aument_columns,
            #                         row, number_format)
            #         else:
            #             sheet.write(aument_rows, aument_columns,
            #                         row, cell_format_det)
            #         aument_columns = aument_columns + 1
            #     aument_rows = aument_rows + 1
            #     aument_columns = 0

            # # Tamaño columnas
            # sheet.set_column('A:B', 25)
            # sheet.set_column('C:C', 30)
            # sheet.set_column('D:D', 25)
            # sheet.set_column('E:F', 40)
            # sheet.set_column('G:G', 50)
            # sheet.set_column('H:L', 25)

            # book.close()

            # # Crear archivo
            # self.write({
            #     'excel_file': base64.encodebytes(stream.getvalue()),
            #     'excel_file_name': filename,
            # })

            # action = {
            #     'name': 'ArchivoPagos',
            #             'type': 'ir.actions.act_url',
            #             'url': "web/content/?model=account.payment.ce&id=" + str(self.id) + "&filename_field=excel_file_name&field=excel_file&download=true&filename=" + self.excel_file_name,
            #             'target': 'self',
            # }
            # return action

    def get_excel_bancoagrario(self):
    
        if self.payment_type_bnk != '220':
            raise ValidationError(
                _('El tipo de pago seleccionado no esta desarrollado por ahora, seleccione otro por favor.'))

        result_columns_encab = self.get_columns_encab()
        result_columns_detail = self.get_columns_detail_davivienda()
        result_query = self.run_sql_davivienda()

        # Logica Archivo Plano
        if self.type_file == '1':
            filename = 'Archivo de Pago '+str(self.description)+'.txt'
            
            # Detalle
            det_content_txt = ''''''

            columns = 0
            content_line = ''
            cant_detalle = 0
            
            # Agregar query
            for payment_id in self.payment_ids:
                codigo_de_banco = (payment_id.partner_bank_id.bank_id.bic).rjust(4, "0")
                nit = (payment_id.partner_id.vat_co).rjust(15, " ")
                tipo_id_benefit = TIPO_DOCUMENT0_BANCO_BOGOTA.get(payment_id.partner_id.l10n_latam_identification_type_id.l10n_co_document_code)
                producto = (payment_id.partner_bank_id.acc_number).rjust(17, " ")
                tipo_de_producto = TIPO_DOCUMENT0_BANCO_BOGOTA.get(payment_id.partner_bank_id.type_account)
                name= payment_id.partner_id.name[0:30].ljust(30)
                relleno = (f"{payment_id.amount:.2f}".replace(".", ",").rjust(15, "0"))
                mensaje = "PAGO".ljust(42)

                content_line = '''%s%s%s%s%s%s%s%s''' % (
                                                                codigo_de_banco,
                                                                nit,
                                                                tipo_id_benefit,
                                                                producto,
                                                                tipo_de_producto,
                                                                name,
                                                                relleno,
                                                                mensaje
                                                                )
                if cant_detalle == 1:
                    det_content_txt = content_line
                else:
                    det_content_txt = det_content_txt + '\n' + content_line

            # Unir Encabezado y Detalle
            content_txt = det_content_txt

            # Crear archivo
            self.write({
                'txt_file': base64.encodebytes((content_txt).encode()),
                'txt_file_name': filename,
            })

            action = {
                'name': 'ArchivoPagos',
                        'type': 'ir.actions.act_url',
                        'url': "web/content/?model=account.payment.ce&id=" + str(self.id) + "&filename_field=txt_file_name&field=txt_file&download=true&filename=" + self.txt_file_name,
                        'target': 'self',
            }
            return action

        # Logica Excel
        if self.type_file == '2':
            filename = 'Archivo de Pago '+str(self.description)+'.xlsx'
            stream = io.BytesIO()
            book = xlsxwriter.Workbook(stream, {'in_memory': True})
            sheet = book.add_worksheet('Banco De Bogota')

            ##Encabezado - Encab
            cell_format_header = book.add_format(
                {'bold': True, 'font_color': 'white'})
            cell_format_header.set_bg_color('#34839b')
            cell_format_header.set_font_name('Calibri')
            cell_format_header.set_font_size(11)
            cell_format_header.set_align('center')
            cell_format_header.set_align('vcenter')

            ##Detalle - Encab
            cell_format_det = book.add_format()
            cell_format_det.set_font_name('Calibri')
            cell_format_det.set_font_size(11)

            # Campos númericos monetarios
            number_format = book.add_format({'num_format': '#,##0.00'})
            number_format.set_font_name('Calibri')
            number_format.set_font_size(11)

            # Campos tipo número
            number = book.add_format({'num_format' : '#,##0.00'})
            number.set_num_format(0)
            number.set_font_name('Calibri')
            number.set_font_size(11)

            # Agregar columnas - Encab
            # aument_columns = 0
            # for columns in result_columns_encab:
            #     sheet.write(0, aument_columns, columns, cell_format_header)
            #     aument_columns = aument_columns + 1

            # #Agregar fila - Encab
            # vat_payer = str(self.vat_payer).split("-")
            # sheet.write(1, 0, vat_payer[0], number)
            # sheet.write(1, 1, self.payment_type_bnk, number)
            # sheet.write(1, 2, self.application, cell_format_det)
            # sheet.write(1, 3, self.sequence, cell_format_det)
            # sheet.write(1, 4, str(self.account_debit).replace("-",""), number)
            # sheet.write(1, 5, self.account_type_debit, cell_format_det)
            # sheet.write(1, 6, self.description, cell_format_det)

            # #Agregar columnas - Detail
            aument_columns = 0
            for columns in result_columns_detail:
                sheet.write(0, aument_columns, columns, cell_format_header)
                aument_columns = aument_columns + 1

            # Agregar query
            aument_columns = 0
            aument_rows = 1
            for query in result_query:
                for row in query.values():
                    if aument_columns == 2 or aument_columns == 8:
                        row = str(row).replace("/", "")
                        row = str(row).replace(".", "")
                        row = str(row).replace(",", "")
                        row = str(row).replace(":", "")
                        row = str(row).replace(";", "")

                    if aument_columns == 7:
                        sheet.write(aument_rows, aument_columns,
                                    row, number_format)
                    else:
                        sheet.write(aument_rows, aument_columns,
                                    row, cell_format_det)
                    aument_columns = aument_columns + 1
                aument_rows = aument_rows + 1
                aument_columns = 0

            # Tamaño columnas
            sheet.set_column('A:B', 25)
            sheet.set_column('C:C', 30)
            sheet.set_column('D:D', 25)
            sheet.set_column('E:F', 40)
            sheet.set_column('G:G', 50)
            sheet.set_column('H:L', 25)

            book.close()

            # Crear archivo
            self.write({
                'excel_file': base64.encodebytes(stream.getvalue()),
                'excel_file_name': filename,
            })

            action = {
                'name': 'ArchivoPagos',
                        'type': 'ir.actions.act_url',
                        'url': "web/content/?model=account.payment.ce&id=" + str(self.id) + "&filename_field=excel_file_name&field=excel_file&download=true&filename=" + self.excel_file_name,
                        'target': 'self',
            }
            return action

    def get_excel_bancobbva(self):
    
        if self.payment_type_bnk != '220':
            raise ValidationError(
                _('El tipo de pago seleccionado no esta desarrollado por ahora, seleccione otro por favor.'))

        result_columns_detail = self.get_columns_detail_davivienda()
        result_query = self.run_sql_davivienda()

        # Logica Archivo Plano
        if self.type_file == '1':
            filename = 'Archivo de Pago '+str(self.description)+'.txt'
            
            # Detalle
            det_content_txt = ''''''

            columns = 0
            content_line = ''
            cant_detalle = 0
            
            # Agregar query
            for payment_id in self.payment_ids:
                tipo_id_benefit = TIPO_DOCUMENT0_BANCO_BOGOTA.get(payment_id.partner_id.l10n_latam_identification_type_id.l10n_co_document_code)
                nit = (payment_id.partner_id.vat_co).rjust(16, " ")
                codigo_de_banco = (payment_id.partner_bank_id.bank_id.bic).rjust(4, "0")
                
                content_line = str(tipo_id_benefit)+str(nit)+str(codigo_de_banco)
                
                if payment_id.partner_bank_id.bank_id.bic == '013':
                    office_code = payment_id.partner_bank_id.office_code.rjust(4, "0")
                    tipo_de_producto = TIPO_DOCUMENT0_BANCO_BOGOTA.get(payment_id.partner_bank_id.type_account)
                    producto = payment_id.partner_bank_id.acc_number[-6:].rjust(6, "0")                    
                    
                    content_line += str(office_code)+"00"+str(tipo_de_producto)+str(producto)+"00"
                else:
                    tipo_de_producto = TIPO_DOCUMENT0_BANCO_BOGOTA.get(payment_id.partner_bank_id.type_account)[0:2]
                    content_line += "0".rjust(16, "0")+str(tipo_de_producto)
                    
                producto = payment_id.partner_bank_id.acc_number.rjust(17, "0")
                relleno = (f"{payment_id.amount:.2f}".replace(".", "").rjust(15, "0"))
                name= payment_id.partner_id.name[0:36].rjust(36)
                                
                content_line += str(producto)+str(relleno)+"00000000"+"0000"+str(name)+"".rjust(36)+"".rjust(48)+"PAGO".ljust(40)+"".rjust(48)+"".rjust(840)
                                
                if cant_detalle == 1:
                    det_content_txt = content_line
                else:
                    det_content_txt = det_content_txt + '\n' + content_line

            # Unir Encabezado y Detalle
            content_txt = det_content_txt

            # Crear archivo
            self.write({
                'txt_file': base64.encodebytes((content_txt).encode()),
                'txt_file_name': filename,
            })

            action = {
                'name': 'ArchivoPagos',
                        'type': 'ir.actions.act_url',
                        'url': "web/content/?model=account.payment.ce&id=" + str(self.id) + "&filename_field=txt_file_name&field=txt_file&download=true&filename=" + self.txt_file_name,
                        'target': 'self',
            }
            return action

        # Logica Excel
        if self.type_file == '2':
            filename = 'Archivo de Pago '+str(self.description)+'.xlsx'
            stream = io.BytesIO()
            book = xlsxwriter.Workbook(stream, {'in_memory': True})
            sheet = book.add_worksheet('Banco De Bogota')

            ##Encabezado - Encab
            cell_format_header = book.add_format(
                {'bold': True, 'font_color': 'white'})
            cell_format_header.set_bg_color('#34839b')
            cell_format_header.set_font_name('Calibri')
            cell_format_header.set_font_size(11)
            cell_format_header.set_align('center')
            cell_format_header.set_align('vcenter')

            ##Detalle - Encab
            cell_format_det = book.add_format()
            cell_format_det.set_font_name('Calibri')
            cell_format_det.set_font_size(11)

            # Campos númericos monetarios
            number_format = book.add_format({'num_format': '#,##0.00'})
            number_format.set_font_name('Calibri')
            number_format.set_font_size(11)

            # Campos tipo número
            number = book.add_format({'num_format' : '#,##0.00'})
            number.set_num_format(0)
            number.set_font_name('Calibri')
            number.set_font_size(11)

            # Agregar columnas - Encab
            # aument_columns = 0
            # for columns in result_columns_encab:
            #     sheet.write(0, aument_columns, columns, cell_format_header)
            #     aument_columns = aument_columns + 1

            # #Agregar fila - Encab
            # vat_payer = str(self.vat_payer).split("-")
            # sheet.write(1, 0, vat_payer[0], number)
            # sheet.write(1, 1, self.payment_type_bnk, number)
            # sheet.write(1, 2, self.application, cell_format_det)
            # sheet.write(1, 3, self.sequence, cell_format_det)
            # sheet.write(1, 4, str(self.account_debit).replace("-",""), number)
            # sheet.write(1, 5, self.account_type_debit, cell_format_det)
            # sheet.write(1, 6, self.description, cell_format_det)

            # #Agregar columnas - Detail
            aument_columns = 0
            for columns in result_columns_detail:
                sheet.write(0, aument_columns, columns, cell_format_header)
                aument_columns = aument_columns + 1

            # Agregar query
            aument_columns = 0
            aument_rows = 1
            for query in result_query:
                for row in query.values():
                    if aument_columns == 2 or aument_columns == 8:
                        row = str(row).replace("/", "")
                        row = str(row).replace(".", "")
                        row = str(row).replace(",", "")
                        row = str(row).replace(":", "")
                        row = str(row).replace(";", "")

                    if aument_columns == 7:
                        sheet.write(aument_rows, aument_columns,
                                    row, number_format)
                    else:
                        sheet.write(aument_rows, aument_columns,
                                    row, cell_format_det)
                    aument_columns = aument_columns + 1
                aument_rows = aument_rows + 1
                aument_columns = 0

            # Tamaño columnas
            sheet.set_column('A:B', 25)
            sheet.set_column('C:C', 30)
            sheet.set_column('D:D', 25)
            sheet.set_column('E:F', 40)
            sheet.set_column('G:G', 50)
            sheet.set_column('H:L', 25)

            book.close()

            # Crear archivo
            self.write({
                'excel_file': base64.encodebytes(stream.getvalue()),
                'excel_file_name': filename,
            })

            action = {
                'name': 'ArchivoPagos',
                        'type': 'ir.actions.act_url',
                        'url': "web/content/?model=account.payment.ce&id=" + str(self.id) + "&filename_field=excel_file_name&field=excel_file&download=true&filename=" + self.excel_file_name,
                        'target': 'self',
            }
            return action
    def get_excel_bancoitau(self):
        def truncar_codigo_bancario(codigo):
            """
            Función para truncar el código bancario según la lógica especificada.
            """
            # Verificar si el código es mayor a 1000 y no es 1007
            codigo = int(codigo)
            if codigo >= 1000:
                codigo = codigo % 1000
            return codigo

        filename = f'Cuentas {self.journal_id.name}-{self.date}.xlsx'
        stream = io.BytesIO()
        book = xlsxwriter.Workbook(stream, {'in_memory': True})
        sheet = book.add_worksheet('Facturas De Proveedores')
        columns = [
            'Fecha de envio',
            'Tipo de Identificacion',
            'Numero de Identificacion del Proveedor/tercero',
            'Nombre del tercero',
            'Codigo del banco del tercero',
            'Tipo de cuenta del tercero',
            'Numero de cuenta del tercero',
            'Valor',
            'Referencia',
            'Observacion',
            'E-mail del tercero',
            'Tipo de Cuenta Origen del cliente',
            'Numero de Cuenta Origen del cliente',
        ]

        # Configuraciones de formato
        cell_format_title = book.add_format({'bold': True, 'align': 'left', 'font_name': 'Calibri', 'font_size': 15, 'bottom': 5, 'bottom_color': '#1F497D', 'font_color': '#1F497D'})
        cell_format_text_generate = book.add_format({'bold': False, 'align': 'left', 'font_name': 'Calibri', 'font_size': 10, 'bottom': 5, 'bottom_color': '#1F497D', 'font_color': '#1F497D'})
        date_format = book.add_format({'num_format': 'dd/mm/yyyy'})
        money = book.add_format({'num_format':'$#,##0.00'})

        # Agregar columnas al Excel
        for i, column in enumerate(columns):
            sheet.write(0, i, column, cell_format_title)  # Ajuste aquí: i en lugar de aument_columns
            sheet.set_column(i, i, len(column) + 10)

        # Suponiendo la existencia y estructura de 'self.payment_ids', 'TIPO_DOCUMENT0_BANCOLOMBIA', y 'TIPO_CUENTA_BANCOITAU'
        sorted_lines = sorted(self.payment_ids, key=lambda x: x.partner_id.id)
        for row_num, lines in enumerate(sorted_lines, start=1): 
            sheet.write(row_num, 0, lines.date,date_format)
            sheet.write(row_num, 1, TIPO_DOCUMENT0_BANCOLOMBIA.get(lines.partner_id.l10n_latam_identification_type_id.l10n_co_document_code, ''))
            sheet.write(row_num, 2, lines.partner_id.vat_co or "")
            sheet.write(row_num, 3, lines.partner_id.name)
            sheet.write(row_num, 4, truncar_codigo_bancario(lines.partner_bank_id.bank_id.bic))
            sheet.write(row_num, 5, TIPO_CUENTA_BANCOITAU.get(lines.partner_bank_id.acc_type, ''))
            sheet.write(row_num, 6, lines.partner_bank_id.acc_number)
            sheet.write(row_num, 7, lines.amount)
            sheet.write(row_num, 8, lines.ref)
            sheet.write(row_num, 9, self.description)
            sheet.write(row_num, 10, lines.partner_id.email)
            sheet.write(row_num, 11, "AHO" if self.account_type_debit == "s" else "CTE")
            sheet.write(row_num, 12, self.account_debit)

        book.close()

        self.write({
            'excel_file': base64.encodebytes(stream.getvalue()).decode(),
            'excel_file_name': filename,
        })

        action = {
            'name': 'Export Seguridad Social',
            'type': 'ir.actions.act_url',
            'url': f"web/content/?model=account.payment.ce&id={self.id}&filename_field=excel_file_name&field=excel_file&download=true&filename={filename}",
            'target': 'self',
        }
        return action
    def get_excel(self):
        if self.format_file == 'bancolombia':
            return self.get_excel_bancolombia()
        if self.format_file == 'bancolombia_pab':
            return self.get_excel_bancolombia_pab()
        if self.format_file == 'occired':
            return self.get_excel_occired()
        if self.format_file == 'davivienda':
            return self.get_excel_davivienda()
        if self.format_file == 'bogota':
            return self.get_excel_bancobogota()
        if self.format_file == 'agrario':
            return self.get_excel_bancoagrario()
        if self.format_file == 'bbva':
            return self.get_excel_bancobbva()
        if self.format_file == 'itau':
            return self.get_excel_bancoitau()

    def _generate_files(self):
        for inv in self.payment_ids:
            partner = inv.partner_id
            company = self.company_id.partner_id
            proveedor_nit = partner.vat_co
            company_nit = company.vat_co
            proveedor_name = partner.name
            company_name = company.name
            proveedor_dv = partner.dv
            company_dv = company.dv
            proveedor_bank = inv.partner_bank_id.acc_number
            proveedor_tipo_id = partner.l10n_latam_identification_type_id.l10n_co_document_code
            company_tipo_id = company.l10n_latam_identification_type_id.l10n_co_document_code
            ref = inv.ref
            monto = inv.amount
            cod_bnk = inv.journal_id.bank_account_id.bank_id.bic


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    type_account = fields.Selection([('A', 'Ahorros'),
                                    ('C', 'Corriente'),
                                    ('OP', 'Otros Pagos'),
                                    ('DP', 'Daviplata'),
                                    ('TP', 'Tarjeta Prepago Maestro'), ], 'Tipo de Cuenta', required=True, default='A')
    is_main = fields.Boolean('Es Principal')


class ResBank(models.Model):
    _inherit = 'res.bank'

    city_id = fields.Many2one('res.city', string="City of Address")
    bank_code = fields.Char(string='Bank Code')
    
class ResCity(models.Model):
    _inherit = 'res.city'
    
    code = fields.Char(string='Code')


