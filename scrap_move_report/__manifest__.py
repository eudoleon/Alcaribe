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
{
    'name': 'Advanced Scrap Move Report',
    'version': '17.0.1.0.0',
    'category': 'Warehouse',
    'summary': """provides scrap product reports in XLSX and PDF formats.""",
    'description': """This module helps you to print detailed inventory scrap 
     move report both in PDF and XLSX format.""",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'depends': ['stock'],
    'data': [
        'security/ir.model.access.csv',
        'report/scrap_move_reports.xml',
        'report/scrap_move_report_templates.xml',
        'wizard/scrap_move_report_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'scrap_move_report/static/src/js/scrap_move_report.js'
        ],
    },
    'images': ['static/description/banner.jpg'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
}
