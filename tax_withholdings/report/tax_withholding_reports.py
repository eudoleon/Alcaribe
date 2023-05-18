# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import api, models, exceptions
from odoo.fields import Datetime
from odoo.tools.misc import formatLang


class MixinTaxWithholdingReport:
    def validate_record(self, record):
        if not record.invoice_date:
            raise exceptions.ValidationError(
                "Se requiere la fecha de Facturación/Reembolso para validar este documento"
            )

        if not record.reference_number:
            raise exceptions.ValidationError(
                "La retención requiere el Número de factura"
            )

        if not record.invoice_control_number:
            raise exceptions.ValidationError(
                "La retención requiere el Número de control de factura"
            )

    def now(self):
        return Datetime.context_timestamp(self, datetime.now())

    def extract_data_by_default(self, record):
        return {
            'company_name': self.env.company.name.upper(),
            'company_vat': record.withholding_agent_vat,
            'vendor_name': record.partner_id.name.upper(),
            'vendor_vat': record.retained_subject_vat,
            'invoice_date': record.invoice_date,
            'accounting_date': record.date or record.invoice_date or self.now(),
            'tsc_tax_withholding_date': record.tsc_tax_withholding_date,
            'invoice_control_number': record.invoice_control_number or "N/A",
            'reference_number': record.reference_number or (
                record.name if record.state == "posted" else "Por definir"
            )
        }

    def get_validated_data(self, record):
        self.validate_record(record)
        data = self.extract_data(record) or {}
        data.update(self.extract_data_by_default(record))
        return type("TaxWithholdingData", (object,), data)

    def extract_data(self, record):
        pass

    def get_data(self, records):
        return list(map(self.get_validated_data, records))

    def format_lang(self, value):
        return formatLang(self.env, value)


class TaxWithholdingIVAReport(MixinTaxWithholdingReport, models.AbstractModel):
    _name = 'report.tax_withholdings.template_tax_withholding_iva'
    _description = 'Tax Withholding IVA Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        report = self.env['ir.actions.report']._get_report_from_name(
            'tax_withholdings.template_tax_withholding_iva')
        obj = self.env[report.model].browse(docids)
        return {
            'data': self.get_data(obj),
            'now': self.now()
        }

    def extract_data(self, record):
        data = {
            "aliquot": record.aliquot_iva,
            "amount_tax": record.amount_tax_iva,
            "amount_base": record.amount_untaxed - record.vat_exempt_amount_iva,
            "amount_total": record.amount_total_iva,
            "amount_withholding": record.withholding_opp_iva,
            "vat_exempt_amount": record.vat_exempt_amount_iva,
            "total_purchase": record.amount_total_purchase
        }
        data = {key: self.format_lang(value) for key, value in data.items()}
        if record.sequence_withholding_iva:
            data["number_withholding"] = record.withholding_number
        else:
            data["number_withholding"] = 'Por definir'
        data["company_street"] = ' '.join([
            self.env.company.street or '',
            self.env.company.street2 or ''
        ]).upper()
        return data

    def validate_record(self, record):
        super().validate_record(record)

        if (record.withholding_iva or 0.0) >= 0.0:
            raise exceptions.UserError(
                "Esta factura no tiene retención"
            )


class TaxWithholdingISLRReport(MixinTaxWithholdingReport, models.AbstractModel):
    _name = 'report.tax_withholdings.template_tax_withholding_islr'
    _description = 'Tax Withholding ISLR Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        report = self.env['ir.actions.report']._get_report_from_name(
            'tax_withholdings.template_tax_withholding_islr')
        obj = self.env[report.model].browse(docids)
        return {
            'data': self.get_data(obj),
            'now': self.now()
        }

    def extract_data(self, record):
        data = {
            "amount_base": record.amount_untaxed - record.vat_exempt_amount_islr,
            "amount_total": record.amount_total_islr,
            "amount_withholding": record.withholding_opp_islr,
            "total_purchase": record.amount_total_purchase,
            "percentage": record.withholding_percentage_islr,
            "subtracting": record.subtracting,
            "total_withheld": record.total_withheld
        }
        data = {key: self.format_lang(value) for key, value in data.items()}
        if record.sequence_withholding_islr:
            date = record.date or record.invoice_date
            data["number_withholding"] = f"{date:%Y%m}{record.sequence_withholding_islr:>08}"
        else:
            data["number_withholding"] = 'Por definir'
        return data

    def validate_record(self, record):
        super().validate_record(record)

        if (record.withholding_islr or 0.0) >= 0.0:
            raise exceptions.UserError(
                "Esta factura no tiene retención"
            )
