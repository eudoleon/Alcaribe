# -*- coding: utf-8 -*-
###############################################################################
#
#    Copyright (C) 2019-TODAY OPeru.
#    Author      :  Grupo Odoo S.A.C. (<http://www.operu.pe>)
#
#    This program is copyright property of the author mentioned above.
#    You can`t redistribute it and/or modify it.
#
###############################################################################

import logging

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ResCompany(models.Model):
    _inherit = 'res.company'
    
    l10n_pe_edi_ose_url = fields.Char('URL')
    l10n_pe_edi_ose_token = fields.Char('Token')
    l10n_pe_edi_ose_id = fields.Many2one('l10n_pe_edi.supplier', string='PSE / OSE Supplier')   
    l10n_pe_edi_ose_code = fields.Char('Code of PSE / OSE supplier', related='l10n_pe_edi_ose_id.code')
    l10n_pe_edi_resume_url = fields.Char('Resume URL')
    l10n_pe_edi_multishop = fields.Boolean('Multi-Shop')
    l10n_pe_edi_send_invoice = fields.Boolean('Send Invoices to PSE/OSE')
    l10n_pe_edi_shop_ids = fields.One2many('l10n_pe_edi.shop','company_id', string='Shops')
    l10n_pe_edi_send_invoice_interval_unit = fields.Selection([
        ('hourly', 'Hourly'),
        ('daily', 'Daily')],
        default='daily', string='Interval Unit for sending')
    l10n_pe_edi_send_invoice_next_execution_date = fields.Datetime(string="Next Execution")

    @api.model
    def run_send_invoice(self):
        """ This method is called from a cron job to send the invoices to PSE/OSE.
        """
        records = self.search([('l10n_pe_edi_send_invoice_next_execution_date', '<=', fields.Datetime.now())])
        if records:
            to_update = self.env['res.company']
            for record in records:
                if record.l10n_pe_edi_send_invoice_interval_unit == 'hourly':
                    next_update = relativedelta(hours=+1)
                elif record.l10n_pe_edi_send_invoice_interval_unit == 'daily':
                    next_update = relativedelta(days=+1)
                else:
                    record.l10n_pe_edi_send_invoice_next_execution_date = False
                    return
                record.l10n_pe_edi_send_invoice_next_execution_date = datetime.now() + next_update
                to_update += record
            to_update.l10n_pe_edi_send_invoices()
    
    def l10n_pe_edi_send_invoices(self):
        for company in self:
            if not company.l10n_pe_edi_send_invoice:
                _logger.info('Send Invoices to PSE/OSE is not active')
                continue
            invoice_ids = self.env['account.move'].search([
                ('l10n_pe_edi_is_einvoice','=',True),
                ('state','not in',['draft','cancel']),
                ('l10n_pe_edi_ose_accepted','=',False),
                ('move_type','in',['out_invoice','out_refund']),
                ('company_id','=', company.id),
                ('l10n_pe_edi_cron_count','>',1)]).sorted('invoice_date')
            # l10n_pe_edi_cron_count starts in 5
            # Try until reaches 1
            # 0: Ok
            # 1: issue after max retry
            for move in invoice_ids:
                try:
                    move.action_document_send()                    
                    if move.l10n_pe_edi_ose_accepted:
                        move.l10n_pe_edi_cron_count = 0
                    else:
                        move.l10n_pe_edi_cron_count -= 1
                    self.env.cr.commit()
                    _logger.debug('Batch of Electronic invoices is sent')
                except Exception:
                    self.env.cr.rollback()
                    move.l10n_pe_edi_cron_count -= 1
                    self.env.cr.commit()
                    _logger.exception('Something went wrong on Batch of Electronic invoices')
    
    def get_doc_types(self): #----------
        return ['01','03','07','08']
    
    def get_moves_dict(self, ids): #----------
        moves = self.env['account.move'].browse(ids)
        return [{
            'shop': move.l10n_pe_edi_shop_id and move.l10n_pe_edi_shop_id.name or '',
            'date': move.invoice_date,
            'type_code': move.l10n_latam_document_type_id and move.l10n_latam_document_type_id.code or '',
            'type': move.l10n_latam_document_type_id and move.l10n_latam_document_type_id.name or '',
            'name': move.name,
            'ose': move.l10n_pe_edi_ose_accepted,
            'sunat': move.l10n_pe_edi_sunat_accepted,
            'error': move.l10n_pe_edi_response,
        } for move in moves]
    
    def get_data_dict(self, edi_requests): #----------
        data = []
        if edi_requests:
            move_edi_requests = [x for x in edi_requests if x['type'] == 'invoice']
            move_ids = [x['res_id'] for x in move_edi_requests]
            data = self.get_moves_dict(move_ids)
        return data
    
    def replace_body_html(self, body_html, days, date, type_count): #----------
        body_html = body_html.replace('--days--', str(days))
        body_html = body_html.replace('--date--', str(date))
        body_html = body_html.replace('--lines--', str(self.get_email_template_lines()))
        body_html = body_html.replace('--01_count--', str(type_count['01']))
        body_html = body_html.replace('--03_count--', str(type_count['03']))
        body_html = body_html.replace('--07_count--', str(type_count['07']))
        body_html = body_html.replace('--08_count--', str(type_count['08']))
        return body_html

    def get_email_template_lines(self): #----------
        return _("""
            <li>(--01_count--) INVOICES NOT SENT AND / OR NOT ACCEPTED</li>
            <li>(--03_count--) BOLETAS NOT SENT AND / OR NOT ACCEPTED</li>
            <li>(--07_count--) CREDIT NOTES NOT SENT AND / OR NOT ACCEPTED</li>
            <li>(--08_count--) DEBIT NOTES NOT SENT AND / OR NOT ACCEPTED</li>
        """)
