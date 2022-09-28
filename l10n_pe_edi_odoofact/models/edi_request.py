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

import json, requests
import urllib3
from datetime import datetime, date, timedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError, RedirectWarning

class EdiRequest(models.Model):
    _name = 'l10n_pe_edi.request'
    _description = 'EDI PE Request'
    _check_company_auto = True
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Description', size=128, index=True, required=True, default='New')
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, default=lambda self: self.env.company)
    document_date = fields.Date(string='Document date')    
    document_number = fields.Char(string='Document number')
    l10n_pe_edi_multishop = fields.Boolean('Multi-Shop', related='company_id.l10n_pe_edi_multishop')   
    l10n_pe_edi_shop_id = fields.Many2one('l10n_pe_edi.shop', string='Shop')
    link_document= fields.Char('Invoice link', compute='compute_request_data', store=True) 
    link_pdf = fields.Char('PDF link', compute='compute_request_data', store=True)
    link_xml = fields.Char('XML link', compute='compute_request_data', store=True)
    link_cdr = fields.Char('CDR link', compute='compute_request_data', store=True)
    log_ids = fields.One2many('l10n_pe_edi.request.log','request_id', string='EDI log', copy=False)
    model = fields.Char(string='Model Name')
    ose_accepted = fields.Boolean('Sent to PSE/OSE', compute='compute_request_data', store=True, tracking=True)  
    res_id = fields.Integer(string='Record ID', help="ID of the target record in the database")
    reference = fields.Char(string='Reference', compute='_compute_reference', readonly=True, store=False)     
    response = fields.Text('Response', compute='compute_request_data', store=True, tracking=True)   
    type = fields.Selection([('invoice','Invoice')], string='Document ype')
    sunat_accepted = fields.Boolean('Accepted by SUNAT', compute='compute_request_data', store=True, tracking=True)       
    state = fields.Selection(
        string='State',
        selection=[('draft', 'New'), ('sent', 'Sent to PSE/OSE'),('accepted','Accepted by SUNAT')], 
        default='draft',
        tracking=True,
        compute='_compute_state',
        store=True
    )        

    @api.depends('model', 'res_id')
    def _compute_reference(self):
        for res in self:
            res.reference = "%s,%s" % (res.model, res.res_id)

    @api.depends('ose_accepted','sunat_accepted')
    def _compute_state(self):
        for request in self:
            if request.sunat_accepted:
                request.state = 'accepted'
                continue
            if request.ose_accepted:
                request.state = 'sent'
            else:
                request.state = 'draft'

    @api.depends('log_ids')
    def compute_request_data(self):
        for req in self:
            log_id = False
            log_id_ose_accepted = False
            if req.log_ids:
                log_id = req.log_ids.sorted('date', reverse = True)[0]
                log_id_ose_accepted = req.log_ids.filtered(lambda r: r.ose_accepted).sorted('date', reverse = True)
            # Getting the OSE status considering all data log. It will used for checking the cancel status in invoice 
            if self._context.get('check_cancel', False):
                req.ose_accepted = log_id and log_id.ose_accepted or False
            else:
                req.ose_accepted = log_id_ose_accepted and log_id_ose_accepted[0].ose_accepted or False
            req.sunat_accepted = log_id_ose_accepted and log_id_ose_accepted[0].sunat_accepted or False
            req.link_document = log_id_ose_accepted and log_id_ose_accepted[0].link_document or ''
            req.link_pdf = log_id_ose_accepted and log_id_ose_accepted[0].link_pdf or ''
            req.link_xml = log_id_ose_accepted and log_id_ose_accepted[0].link_xml or ''            
            req.link_cdr = log_id_ose_accepted and log_id_ose_accepted[0].link_cdr or ''            
            req.response = log_id and log_id.response or ''
    
    def action_document_send(self):
        """ 
        This method creates the request to PSE/OSE provider 
        """
        for doc in self:
            model = doc.model
            res_id = doc.res_id
            if model and res_id:
                self.env[model].browse(res_id).action_document_send()

    def action_document_check(self):
        """
        Send the request for Checking status for electronic documents
        """
        for doc in self:
            model = doc.model
            res_id = doc.res_id
            if model and res_id:
                self.env[model].browse(res_id).action_document_check()
            
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('l10n_pe_edi.request') or '/'
        return super(EdiRequest, self).create(vals)

    def _get_ose_supplier(self):
        if not self.company_id.vat or not self.company_id.l10n_pe_edi_ose_id:
            action = self.env.ref('base.action_res_company_form')
            msg = _('Can not send the electronic document until you configure your company name, VAT and the PSE/OSE supplier. Company: %s')% (self.company_id.name)
            raise RedirectWarning(msg, action.id, _('Go to Companies'))
        return self.company_id.l10n_pe_edi_ose_id.code
    
    def action_api_connect(self, vals):        
        ose_supplier = self._get_ose_supplier()
        getattr(self,'api_connector_%s' % ose_supplier)(vals)
        # Commit the change
        self.env.cr.commit()
        return True
    
    #PSE / OSE connector
    def api_connector_odoofact(self, vals):        
        data = json.dumps(vals)  
        company = self.env['res.company'].browse(vals['company_id'])
        l10n_pe_edi_shop_id = vals.get('l10n_pe_edi_shop_id', False)
        url = '' 
        authorization = '' 
        if company.l10n_pe_edi_multishop and l10n_pe_edi_shop_id:
            shop_id = self.env['l10n_pe_edi.shop'].browse(l10n_pe_edi_shop_id)
            url = shop_id.l10n_pe_edi_ose_url
            authorization = shop_id.l10n_pe_edi_ose_token
            if not url or not authorization:
                raise UserError(_("Review URL settings and token for the shop: %s")% (shop_id.name))
        else:
            if company.l10n_pe_edi_ose_url:    
                url = company.l10n_pe_edi_ose_url
            if company.l10n_pe_edi_ose_token: 
                authorization = company.l10n_pe_edi_ose_token
        headers = {'Content-type': 'application/json', 'Authorization': authorization}
        try:
            r = requests.post(url, data, headers=headers, verify=True)
        except requests.exceptions.RequestException as e:  # This is the correct syntax
            raise UserError(_("Review URL settings and token for billing. \n %s")% (e))
        response = r.text
        response = response.replace("'", "\'")
        response = json.loads(response)
        ose_accepted = False
        if response.get('errors',False):
            ose_accepted = False
        else:
            ose_accepted = True
        json_invoice = json.loads(data)
        values_log = {
            'request_id': self.id,
            'json_sent': json.dumps(json_invoice, indent=4, sort_keys=True),
            'json_response': json.dumps(response, indent=4, sort_keys=True),
            'link_document': response.get('enlace',''),
            'link_cdr': response.get('enlace_del_cdr',''),
            'link_pdf': response.get('enlace_del_pdf',''),
            'link_xml': response.get('enlace_del_xml',''),
            'operation_type': vals.get('operacion', ''),
            'ose_accepted': ose_accepted,
            'response': response.get('errors',False),            
            'sunat_accepted': response.get('aceptada_por_sunat', False), 
            'sunat_description': response.get('sunat_description',''),                       
            'sunat_note': response.get('sunat_note',''),
            'sunat_responsecode': response.get('sunat_responsecode',''),
            'sunat_soap_error': response.get('sunat_soap_error','')}
        #~ Register log
        self.env['l10n_pe_edi.request.log'].create(values_log)
        # If response code is 23 ("Documento ya existe") ----------------
        if int(response.get("codigo", 0)) == 23:
            self.action_document_check()
        return True
    
    def action_open_edi_request(self):
        """ 
        This method opens the EDI request 
        """
        self.ensure_one()
        model = self.model
        res_id = self.res_id
        if model and res_id:
            self.env[model].browse(res_id).action_document_send()
            return {
                'name': _('EDI Request'),
                'view_mode': 'form',
                'res_model': 'l10n_pe_edi.request',
                'res_id': self.id,
                'type': 'ir.actions.act_window',
            }
        return True
    
    def action_open_document(self):
        """ 
        This method opens the related electronic document
        """
        self.ensure_one()
        model = self.model
        res_id = self.res_id
        if model and res_id:
            self.env[model].browse(res_id).action_document_send()
            return {
                'name': _('Electronic document'),
                'view_mode': 'form',
                'res_model': model,
                'res_id': res_id,
                'type': 'ir.actions.act_window',
            }
        return True

    @api.model
    def cron_send_resume(self):
        days_before = (date.today()-timedelta(days=3))
        request_ids = self.env['l10n_pe_edi.request'].search([
            ('document_date','=', days_before)]) 
        company_ids = request_ids.mapped('company_id')
        for company in company_ids:
            company_request_ids = request_ids.filtered(lambda r: r.company_id.id == company.id)
            for type in company_request_ids.mapped('type'):
                resume_request_ids = company_request_ids.filtered(lambda r: r.type == type)
                line = {
                    'name':company.name, 
                    'vat': company.vat, 
                    'email': company.email, 
                    'date': days_before.strftime("%Y-%m-%d"), 
                    'type': type, 
                    'created': len(resume_request_ids),
                    'sent': len(resume_request_ids.filtered(lambda r: r.ose_accepted == True)),
                    'accepted': len(resume_request_ids.filtered(lambda r: r.sunat_accepted == True)),
                    'version': '14.0'}
                if company.l10n_pe_edi_ose_id and company.l10n_pe_edi_ose_id.resume_url:   
                    url = company.l10n_pe_edi_ose_id.resume_url
                    try:
                        r = requests.post(url, data=line)
                    except requests.exceptions.RequestException as e:  # This is the correct syntax
                        raise UserError(_("Review URL settings. \n %s")% (e))
                    response = r.text
                    response = response.replace("'", "\'")
        return True
    
    @api.model
    def cron_check_documents_state(self):
        doc_ids = self.env['l10n_pe_edi.request'].search([
            ('ose_accepted','=',True),
            ('sunat_accepted','=',False),
            ('document_date','>=',(date.today() - timedelta(days=30))),
            ('document_date','<=',(date.today() - timedelta(days=3)))])
        for doc in doc_ids:
            try:
                doc.action_document_check()
                self.env.cr.commit()
            except Exception:
                self.env.cr.rollback()            

class L10nPeEdiRequestLog(models.Model):
    _name = 'l10n_pe_edi.request.log'
    _description = 'Log response'
    _order = 'date desc'
    
    date = fields.Datetime('Date', default=fields.Datetime.now, required=True)
    einvoice_sunat_note = fields.Text('Notes by SUNAT')  
    json_sent = fields.Html('JSON sent')
    json_response = fields.Html('JSON response')  
    link_document = fields.Char('Document link')
    link_cdr = fields.Char('CDR link')    
    link_pdf = fields.Char('PDF link')
    link_xml = fields.Char('XML link')
    operation_type = fields.Char('Operation type')
    ose_accepted = fields.Boolean('Accepted by PSE/OSE')
    request_id = fields.Many2one('l10n_pe_edi.request', string='EDI request')
    response = fields.Text(string='Response')
    sunat_description = fields.Char('SUNAT error description')
    sunat_note = fields.Char('SUNAT note')
    sunat_responsecode = fields.Char('SUNAT Response code')
    sunat_soap_error = fields.Char('SUNAT SOAP error')
    sunat_accepted = fields.Boolean('Accepted by SUNAT')      

class L10nPeEdiSupplier(models.Model):
    _name = 'l10n_pe_edi.supplier'
    _description = 'PSE/OSE Supplier'

    code = fields.Char(string='Code', required=True)
    name = fields.Char(string='Name', size=128, index=True, required=True)
    control_url = fields.Char(string='URL for searching electronic documents')
    resume_url = fields.Char(string='URL for resume documents')
    authorization_message = fields.Html(string='Authorization Message', help="The message will be printed on the invoice", translate=True, sanitize=False)
