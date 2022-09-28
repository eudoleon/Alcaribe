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

from . import models
from . import report
from . import wizard

from odoo import api, SUPERUSER_ID, _

def _create_shop(env):
    """ This hook is used to add a shop on existing companies
    when module l10n_pe_edi_odoofact is installed.
    """
    company_ids = env['res.company'].search([]).filtered(lambda r: r.country_id.code == 'PE')
    company_with_shop = env['l10n_pe_edi.shop'].search([]).mapped('company_id')
    company_without_shop = company_ids - company_with_shop
    for company in company_without_shop:
        env['l10n_pe_edi.shop'].create({
            'name': '%s (%s)' % (company.name, _('Shop')),
            'code': '0000',
            'company_id': company.id,
            'partner_id': company.partner_id.id,
        })

def _create_journal_debit(env):
    """ This hook is used to add a Journal 'Debit note' for existing companies
    when module l10n_pe_edi_odoofact is installed.
    """
    company_ids = env['res.company'].search([]).filtered(lambda r: r.country_id.code == 'PE')
    # Set default E-invoice on Sale journals
    for journal in env['account.journal'].search([('type','=','sale'),('company_id','in',company_ids.ids)]):
        journal.write({
                    'l10n_pe_edi_is_einvoice': True, 
                    'l10n_latam_document_type_id': env.ref('l10n_pe_edi_odoofact.document_type01').id,
                    'l10n_pe_edi_shop_id': journal.company_id.l10n_pe_edi_shop_ids and journal.company_id.l10n_pe_edi_shop_ids[0].id or False,
                    'sequence_override_regex': r'^(?P<prefix1>.*?)(?P<seq>\d*)(?P<suffix>\D*?)$',
                    })
    # Create journal for Debit note
    company_with_debit_note_journal = env['account.journal'].search([('l10n_latam_document_type_id','=',env.ref('l10n_pe_edi_odoofact.document_type08').id)]).mapped('company_id')
    company_without_debit_note_journal = company_ids - company_with_debit_note_journal
    for company in company_without_debit_note_journal:
        env['account.journal'].create({
                        'name': _('Debit note'), 
                        'code': _('DEB'),
                        'type': 'sale',
                        'l10n_pe_edi_is_einvoice': True, 
                        'l10n_latam_document_type_id': env.ref('l10n_pe_edi_odoofact.document_type08').id,
                        'l10n_pe_edi_shop_id': company.l10n_pe_edi_shop_ids and company.l10n_pe_edi_shop_ids[0].id or False,
                        'sequence_override_regex': r'^(?P<prefix1>.*?)(?P<seq>\d*)(?P<suffix>\D*?)$',
                        'sequence': 6,
                        'company_id': company.id,
                        'show_on_dashboard': True,                        
                        'color': 11,
                    })
        
def _write_journal_regex(env):
    """ This hook is used to add a sequence on existing journal
    when module l10n_pe_edi_odoofact is installed. '^(?P<prefix1>.*?)(?P<seq>\d*)(?P<suffix>\D*?)$'
    """
    company_ids = env['res.company'].search([]).filtered(lambda r: r.country_id.code == 'PE')
    for journal in env['account.journal'].search([('company_id','in',company_ids.ids),('type','=','sale')]):
        journal.write({
                    'sequence_override_regex': r'^(?P<prefix1>.*?)(?P<seq>\d*)(?P<suffix>\D*?)$',
                    })

def _change_values_paperformat_a4(env):
    paperformat_id = env.ref("base.paperformat_euro", False)
    if paperformat_id:
        paperformat_id.write({
            "margin_top": 30,
            "margin_bottom": 20,
            "header_spacing": 25,
        })

def _l10n_pe_edi_odoofact_init(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _create_shop(env)
    _create_journal_debit(env)
    _write_journal_regex(env)
    _change_values_paperformat_a4(env)
