# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Anagha S (odoo@cybrosys.com)
#
#    This program is under the terms of the Odoo Proprietary License v1.0 (OPL-1)
#    It is forbidden to publish, distribute, sublicense, or sell copies of the
#    Software or modified copies of the Software.
#
#    THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#    FITNESS FOR A PARTICULAR PURPOSE AND NON INFRINGEMENT. IN NO EVENT SHALL
#    THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,DAMAGES OR OTHER
#    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,ARISING
#    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#    DEALINGS IN THE SOFTWARE.
#
###############################################################################
import io
import json
from odoo import fields, models
from odoo.exceptions import ValidationError
from odoo.tools import date_utils
try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class ScrapMoveReport(models.TransientModel):
    """Create scrap move report"""
    _name = "scrap.move.report"
    _description = "Scrap Move Report"

    start_date = fields.Datetime(string="Start Date",
                                 default=fields.datetime.now(),
                                 required=True,
                                 help="Starting date of scrap moves.")
    end_date = fields.Datetime(string="End Date",
                               default=fields.datetime.now(), required=True,
                               help="End date of scrap moves.")
    location_id = fields.Many2one('stock.location', string="Location",
                                  help="Locations of scrap moves.")
    product_id = fields.Many2one('product.product', string="Product",
                                 help="Select a product to view its scrap "
                                      "moves.")

    def action_print_pdf(self):
        """Prints pdf report of scrap move."""
        if self.start_date > self.end_date:
            raise ValidationError('Start Date must be less than End Date')
        data = {
            'start_date': self.start_date,
            'end_date': self.end_date,
            'location': self.location_id.id,
            'product': self.product_id.id
        }
        return self.env.ref(
            'scrap_move_report.scrap_move_report_pdf_action').\
            report_action(self, data=data)

    def action_print_xlsx(self):
        """Prints excel report of scrap move."""
        if self.start_date > self.end_date:
            raise ValidationError('Start Date must be less than End Date')
        data = {
            'start_date': self.start_date,
            'end_date': self.end_date,
            'location': self.location_id.id,
            'product': self.product_id.id
        }
        query = """SELECT s.name as reference,t.name as product_name,p.id as 
                tmpl_id, scrap_qty,l.name as complete_name,s.create_date,
                scrap_location_id,s.product_id,m.product_qty as qty
                FROM stock_scrap s
                INNER JOIN product_product p on s.product_id = p.id
                INNER JOIN product_template t on p.product_tmpl_id = t.id
                INNER JOIN stock_location l on s.location_id = l.id
                INNER JOIN stock_location k on s.scrap_location_id = k.id
                INNER JOIN stock_move m on m.scrap_id = s.id
                LEFT JOIN product_attribute_product_template_rel v on 
                s.product_id = v.product_attribute_id LEFT JOIN 
                product_attribute_value var on 
                v.product_template_id = var.id WHERE """
        if data['location'] and data['product']:
            query += """s.location_id = %s and s.product_id = %s and 
                    s.create_date between %s and %s and  m.company_id = %s"""
            filter_values = (data['location'], data['product'],
                             data['start_date'], data['end_date'],
                             self.env.user.company_id.id)
            self._cr.execute(query, filter_values)
            record = self._cr.dictfetchall()
        elif data['location']:
            query += """s.location_id = %s and s.create_date between %s and %s 
                    and m.company_id = %s"""
            filter_values = (data['location'], data['start_date'],
                             data['end_date'], self.env.user.company_id.id)
            self._cr.execute(query, filter_values)
            record = self._cr.dictfetchall()
        elif data['product']:
            query += """s.create_date between %s and %s and p.id = %s and
                     m.company_id = %s"""
            filter_values = data['start_date'], data['end_date'], data[
                'product'], self.env.user.company_id.id
            self._cr.execute(query, filter_values)
            record = self._cr.dictfetchall()
        else:
            query += """s.create_date between %s and %s and m.company_id = %s"""
            filter_values = (data['start_date'], data['end_date'],
                             self.env.user.company_id.id)
            self._cr.execute(query, filter_values)
            record = self._cr.dictfetchall()
        for val in record:
            product_id = self.env['product.product'].browse(val['tmpl_id'])
            val.update({
                'price': product_id.standard_price
            })
            val['display_name'] = self.env['product.product'].search(
                [('id', '=', val['product_id'])]).display_name
            val['date_create'] = str(val['create_date']).split()[0]
        data['record'] = record
        return {
            'type': 'ir.actions.report',
            'data': {'model': 'scrap.move.report',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'output_format': 'xlsx',
                     'report_name': 'Scrap Move Excel Report',
                     },
            'report_type': 'scrap_move_report_xlsx'
        }

    def action_get_xlsx_report(self, data, response):
        """ Get xlsx report values """
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        sheet.set_paper(9)
        sheet.set_default_row(18)
        sheet.set_column('C:D', 12)
        sheet.set_column('E:E', 25)
        sheet.set_column('G:H', 12)
        cell_format = workbook.add_format({'font_size': '12px'})
        cell_format_red = workbook.add_format(
            {'font_color': 'red', 'align': 'center', 'bold': True})
        format1 = workbook.add_format({'font_size': '10px', 'align': 'left'})
        head = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '15px'})
        txt = workbook.add_format({'font_size': '12px'})
        total = workbook.add_format({'align': 'right', 'font_size': '10px'})
        # HEADINGS
        sheet.merge_range('B2:I3', 'ADVANCED SCRAP REPORT', head)
        sheet.write('B6', 'From:', cell_format)
        sheet.merge_range('C6:D6', data['start_date'], txt)
        sheet.write('F6', 'To:', cell_format)
        sheet.merge_range('G6:H6', data['end_date'], txt)
        sheet.write('B8', 'S NO', cell_format)
        sheet.write('C8', 'REFERENCE', cell_format)
        sheet.write('D8', 'CREATE DATE', cell_format)
        sheet.write('E8', 'PRODUCT', cell_format)
        sheet.write('F8', 'QUANTITY', cell_format)
        sheet.write('G8', 'LOCATION', cell_format)
        sheet.write('H8', 'TOTAL', cell_format)
        currency = self.env.user.company_id.currency_id.symbol
        col_num, row_num, j, s_no = 1, 9, 10, 1
        record_list = data['record'].copy()
        if not record_list:
            sheet.merge_range('D10:F10', 'NO RECORD FOUND !', cell_format_red)
        for data in record_list:
            sheet.write(row_num, col_num, s_no, format1)
            sheet.write(row_num, col_num + 1, data['reference'], txt)
            sheet.write(row_num, col_num + 2, data['date_create'], txt)
            sheet.write(row_num, col_num + 3, data['display_name'], txt)
            sheet.write(row_num, col_num + 4, data['scrap_qty'], txt)
            sheet.write(row_num, col_num + 5, data['complete_name'], txt)
            sheet.write(row_num, col_num + 6,
                        currency + str(data['price'] * data['qty']), total)
            s_no += 1
            row_num += 1
            j += 1
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
