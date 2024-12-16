# coding: utf-8
##############################################################################
#    Company: Tecvemar, c.a.
#    Author: Juan V. Márquez L.
#    Creation Date: 26/11/2012
#    Version: 0.0.0.0
#
#    Description: Gets a CSV file from data collector and import it to
#                 sale order
#
##############################################################################
# from datetime import datetime
import base64
import functools
import io
import logging

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _
from odoo import sys
from io import BytesIO

# from openerp.addons.decimal_precision import decimal_precision as dp
import time
# import workflow
import csv

FIELDNAMES = [
    'RifRetenido',
    'NumeroFactura',
    'NumeroControl',
    'CodigoConcepto',
    'FechaOperacion',
    'MontoOperacion',
    'PorcentajeRetencion']

class EmployeeIncomeWh(models.TransientModel):

    _name = 'employee.income.wh'

    _description = ''

    logger = logging.getLogger('employee.income.wh')

    def _parse_csv_employee_income_wh(self, csv_file):
        data_file = io.StringIO(csv_file.decode("utf-8"))
        data_file.seek(0)
        file_reader = []
        csv_reader = csv.reader(data_file, delimiter=';')
        file_reader.extend(csv_reader)

        if not file_reader[0] == FIELDNAMES:
            raise UserError("Error! El archivo no contiene la estructura correcta")
        del file_reader[0]
        return file_reader

    def _clear_xml_employee_income_wh(self):
        context = self._context or {}
        if self._context['active_id']:
            unlink_ids = self.env['account.wh.islr.xml.line'].search(
                [('islr_xml_wh_doc', '=', self._context['active_id']),
                 ('type', '=', 'employee')])
            if unlink_ids:
                unlink_ids.unlink()
        return True

    def _get_xml_employee_income_wh(self, xml_list):

        def memoize(func):
            cache = {}

            @functools.wraps(func)
            def wrapper(*args):
                if args in cache:
                    return cache[args]
                result = func(*args)
                cache[args] = result
                return result
            return wrapper

        @memoize
        def find_data(obj, field, operator, value):
            ids = obj.search( [(field, operator, value)])
            if len(ids) == 1:
                return ids[0]
            return False

        context = self._context or {}
        field_map = {'RifRetenido': 'partner_vat',
                     'NumeroFactura': 'invoice_number',
                     'NumeroControl': 'control_number',
                     'CodigoConcepto': 'concept_code',
                     'FechaOperacion': 'date_ret',
                     'MontoOperacion': 'base',
                     'PorcentajeRetencion': 'porcent_rete',
                     }
        obj_pnr = self.env['res.partner']
        obj_irt = self.env['account.wh.islr.rates']
        valid = []
        invalid = []
        for item in xml_list:
            data = {}
            i = 0
            for key, data_key in field_map.items():
                data[data_key] = item[i]
                i += 1
            pnr_id = find_data(obj_pnr, 'rif', '=', '%s' % data.get('partner_vat'))
            if pnr_id:
                data.update({'partner_id': pnr_id.id})
            else:
                raise UserError("Error! No se encuentra un contacto con cédula %s" % data.get('partner_vat'))

            if not pnr_id.people_type_individual:
                raise UserError("Error! El contacto con cédula %s no tiene asignado el tipo de persona." % data.get('partner_vat'))

            irt_id = self.env['account.wh.islr.rates'].search([('code','=',data.get('concept_code')),('name','=',pnr_id.people_type_individual.upper())])
            if irt_id:
                data.update({'concept_id': irt_id.concept_id.id,
                             'rate_id': irt_id.id})
            else:
                raise UserError("Error! No se encuentra el concepto de retención %s" % data.get('concept_code'))

            date_ret = time.strptime(data['date_ret'], '%d/%m/%Y')
            date_ret = time.strftime('%Y-%m-%d', date_ret)

            data.update({
                'wh': float(data['base']) * float(data['porcent_rete']) / 100,
                'date_ret': date_ret,
                'islr_xml_wh_doc': self._context['active_id'],
                'type': 'employee',
            })

            if pnr_id and irt_id:
                valid.append(data)
            else:
                invalid.append(data)

        return valid, invalid

    # --------------------------------------------------------- function fields


    name = fields.Char('File name', size=128, readonly=True)
    type = fields.Selection([
            ('csv', 'CSV File'),
            ], string='File Type', required=True, default='csv')
    obj_file= fields.Binary('XML file', required=True,
                                  help=("XML file name with employee income "
                                        "withholding data"))

    def process_employee_income_wh(self):

        eiw_file = self.obj_file
        invalid = []
        xml_file = base64.decodebytes(eiw_file)
        if self.type == 'xml':
            # try:
            #     unicode(xml_file, 'utf8') #unicode
            # except UnicodeDecodeError:
            #     # If we can not convert to UTF-8 maybe the file
            #     # is codified in ISO-8859-15: We convert it.
            #     xml_file = sys.setdefaultencoding(xml_file, 'iso-8859-15').encode('utf-8')
            # values = self._parse_xml_employee_income_wh(
            #     xml_file)
            pass
        elif self.type == 'csv':
            values = self._parse_csv_employee_income_wh(xml_file)
        if values:
            self._clear_xml_employee_income_wh()
            valid, invalid = self._get_xml_employee_income_wh(values)
            line_create = [(5, 0, 0)]
            for data in valid:
                line_employee = self.env['account.wh.islr.xml.line'].create(data)
                if line_employee:
                    line_create.append((4, line_employee.id))

            islr_xml = self.env['account.wh.islr.xml'].browse(self._context['active_id'])
            if islr_xml:
                islr_xml.employee_xml_ids = line_create
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
