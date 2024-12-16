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
################################################################
from odoo import api, fields, models


class ScrapMoveReport(models.AbstractModel):
    """ Scrap Move Report."""
    _name = "report.scrap_move_report.scrap_pdf_report"
    _description = "Scrap Move pdf Report"

    @api.model
    def _get_report_values(self, docids, data):
        """Get the values for the stock scrap report."""
        start_date = data['start_date']
        end_date = data['end_date']
        query = """SELECT s.name as reference,
        s.create_date as date_created,
        t.name as product_name,
        scrap_qty,l.name as loc,
        s.product_id,p.id as prod_id,m.product_qty as qty
        FROM stock_scrap s
        INNER JOIN product_product p on s.product_id = p.id
        INNER JOIN product_template t on p.product_tmpl_id = t.id
        INNER JOIN stock_location l on s.location_id = l.id
        INNER JOIN stock_move m on m.scrap_ids in s.id
        LEFT JOIN product_attribute_product_template_rel v on s.product_id = 
        v.product_attribute_id
        LEFT JOIN product_attribute_value var on v.product_template_id = var.id
        WHERE """
        if data['location'] and data['product']:
            query += """s.location_id = %s and s.product_id = %s and 
            s.create_date between %s and %s and  m.company_id = %s"""
            filter = data['location'], data[
                'product'], start_date, end_date, self.env.user.company_id.id
            self._cr.execute(query, filter)
            record = self._cr.dictfetchall()
        elif data['location']:
            query += """s.location_id = %s and s.create_date between %s and %s
             and m.company_id = %s"""
            filter = data[
                'location'], start_date, end_date, self.env.user.company_id.id
            self._cr.execute(query, filter)
            record = self._cr.dictfetchall()
        elif data['product']:
            query += """s.create_date between %s and %s and p.id = %s and
             m.company_id = %s"""
            filter = start_date, end_date, data[
                'product'], self.env.user.company_id.id
            self._cr.execute(query, filter)
            record = self._cr.dictfetchall()
        else:
            query += """s.create_date between %s and %s and m.company_id = %s"""
            filter = start_date, end_date, self.env.user.company_id.id
            self._cr.execute(query, filter)
            record = self._cr.dictfetchall()
        for val in record:
            product_id = self.env['product.product'].browse(val['prod_id'])
            val.update({
                'price': product_id.standard_price
            })
            val['display_name'] = self.env['product.product'].browse(
                val['product_id']).display_name
            val['date_create'] = str(val['date_created']).split()[0]
        return {
            'docs': record,
            'created_date': str(fields.Date.today()),
            'start_date': data['start_date'],
            'end_date': data['end_date']
        }
