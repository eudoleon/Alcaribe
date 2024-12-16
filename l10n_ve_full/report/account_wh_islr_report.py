# coding: utf-8

from odoo import models, api, _
from odoo.exceptions import UserError, Warning
from odoo import api, fields, models, _
from odoo import exceptions


class RepComprobanteIslr(models.AbstractModel):
    _name = 'report.l10n_ve_full.template_wh_islr'
    _description = 'Planilla de Retencion ISLR'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not docids:
            raise UserError("Necesita seleccionar una retencion para imprimir.")
        data = {'form': self.env['account.wh.islr.doc'].browse(docids)}
        res = dict()
        partner_id = data['form'].partner_id
        total_doc = 0
        date_ret = data['form'].date_ret
        amount_total = data['form'].invoice_ids.invoice_id.amount_total
        if date_ret:
            split_date = (str(date_ret).split('-'))
            date_ret = str(split_date[2]) + '/' + (split_date[1]) + '/' + str(split_date[0])
            period_date = (str(data['form'].date_ret).split('-'))
            period = str(period_date[1]) + '/' + str(period_date[0])
        else:
            raise Warning(_("Se necesita la Fecha para poder procesar."))
        if partner_id.company_type == 'person':
            if partner_id.vat:
                document = partner_id.vat
            else:
                if partner_id.nationality == 'V' or partner_id.nationality == 'E':
                    document = str(partner_id.nationality) + str(partner_id.identification_id)
                else:
                    document = str(partner_id.identification_id)
        else:
            document = partner_id.vat

        if data['form'].state == 'done':
            if data['form'].invoice_ids.invoice_id.currency_id.id == data['form'].company_id.currency_id.id:
                total_doc = data['form'].invoice_ids.invoice_id.amount_total
            elif data['form'].invoice_ids.invoice_id.currency_id != data['form'].company_id.currency_id.id:
                tasa = data['form'].invoice_ids.invoice_id.currency_bs_rate
                if tasa:
                    total_doc = data['form'].invoice_ids.invoice_id.amount_total * tasa
                else:
                    tasa = self.obtener_tasa(data['form'].invoice_ids.invoice_id)
                    total_doc = data['form'].invoice_ids.invoice_id.amount_total * tasa

            # code_code = ''
            # for code in data['form'].concept_ids.iwdi_id.islr_xml_id:
            #     code_code = code.concept_code
            print('data', data['form'].company_id.logo)
            return {
                'data': data['form'],
                'document': document,
                # 'code_code': code_code,
                'total_doc': total_doc,
                'model': self.env['report.l10n_ve_full.template_wh_islr'],
                'doc_model': self.env['report.l10n_ve_full.template_wh_islr'],
                'lines': res,  # self.get_lines(data.get('form')),
                'date_ret': date_ret,
                'period': period,
                'amount_total': amount_total,
            }
        else:
            raise UserError("La Retencion de ISLR debe estar en estado Realizado para poder generar su Comprobante")

    def obtener_tasa(self, invoice):
        fecha = invoice.invoice_date
        tasa_id = invoice.currency_id
        tasa = self.env['res.currency.rate'].search([('currency_id', '=', tasa_id.id), ('name', '<=', fecha)],
                                                    order='id desc', limit=1)
        if not tasa:
            raise UserError(
                "Advertencia! \nNo hay referencia de tasas registradas para moneda USD en la fecha igual o inferior de la factura %s" % (
                    invoice.name))

        return tasa.rate

    def _get_date_invoice(self, id):

        date_invoice = id[0].invoice_id.date_document
        return date_invoice

    def _get_supplier_invoice_number(self, id):

        supplier_number = id[0].invoice_id.supplier_invoice_number
        return supplier_number

    def _get_nro_ctrl(self, id):

        nro_ctrl = id[0].invoice_id.nro_ctrl
        return nro_ctrl

    def _get_islr_wh_concept(self, id):

        concept = id[0].concept_id.name

        return concept

    def _get_islr_wh_retencion_islr(self, id):

        retencion_islr_local = id[0].retencion_islr
        return retencion_islr_local

    def _get_islr_wh_doc_invoices_base(self, id):

        base_ret_local = id[0].base_amount
        return base_ret_local

    def _get_islr_wh_doc_invoice_subtract(self, id):

        subtract_local = id[0].subtract
        return subtract_local

    def _get_islr_invoice_amount_ret(self, id):

        amount_ret_local = id[0].amount
        return amount_ret_local

    def get_period(self, date):
        if not date:
            raise Warning(_("Se necesita una fecha, por favor ingresar"))
        split_date = str(date).split('-')
        return str(split_date[1]) + '/' + str(split_date[0])

    def get_date(self, date):
        if not date:
            raise Warning(_("Se necesita una fecha, por favor ingresar."))
        split_date = date.split('-')
        return str(split_date[2]) + '/' + (split_date[1]) + '/' + str(split_date[0])

    def get_direction(self, partner):
        direction = ''
        direction = ((partner.street and partner.street + ', ') or '') + \
                    ((partner.street2 and partner.street2 + ', ') or '') + \
                    ((partner.city and partner.city + ', ') or '') + \
                    ((partner.state_id.name and partner.state_id.name + ',') or '') + \
                    ((partner.country_id.name and partner.country_id.name + '') or '')
        if direction == '':
            direction = 'Sin direccion'
        return direction

    def get_tipo_doc(self, tipo=None):
        if not tipo:
            return []
        types = {'out_invoice': '1', 'in_invoice': '1', 'out_refund': '2',
                 'in_refund': '2'}
        return types[tipo]
