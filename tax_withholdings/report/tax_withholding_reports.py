# -*- coding: utf-8 -*-

from datetime import datetime
from functools import partial
from itertools import groupby

from odoo import _, api, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Datetime
from odoo.tools.misc import formatLang


class QueryDict(dict):
    def __getattr__(self, attr):
        try:
            return self.__getitem__(attr)
        except KeyError:
            return super(QueryDict, self).__getattr__(attr)

    def __setattr__(self, attr, value):
        self.__setitem__(attr, value)


class MixinTaxWithholdingReport(models.AbstractModel):
    _name = 'report.tax_withholdings.mixin'
    _description = 'Tax Withholding Mixin Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        objs = self.env['account.move'].browse(docids)
        return {
            'f': partial(formatLang, self.env),
            'data': self.get_data(objs),
            'now': self.now()
        }

    def validate_record(self, record):
        if not record.invoice_date:
            raise ValidationError(_(
                "Invoice/Reimbursement date is required to validate this document"
            ))

        if not record.reference_number:
            raise ValidationError(_("Withholding requires the Invoice Number"))

        if not record.invoice_control_number:
            raise ValidationError(_("Withholding requires the Invoice Control Number"))

    def now(self):
        return Datetime.context_timestamp(self, datetime.now())

    _name_data_default = (
        'company_name',
        'company_vat',
        'vendor_name',
        'vendor_vat',
        'accounting_date',
        'tsc_tax_withholding_date',
        'number_withholding',
        'company_street',
    )

    def _funckey(self, value: dict):
        return tuple(value.get(name) for name in self._name_data_default)

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
                record.name if record.state == "posted" else _("To be defined")
            )
        }

    def extract_data(self, record):
        raise NotImplementedError(
            "You must implement this method in your report"
        )

    def get_validated_data(self, record):
        self.validate_record(record)
        data = self.extract_data(record) or {}
        data.update(self.extract_data_by_default(record))
        return QueryDict(data)

    def get_data(self, records):
        return [
            QueryDict(
                zip(self._name_data_default, index),
                invoices=list(values)
            ) for index, values in groupby(
                sorted(
                    map(self.get_validated_data, records),
                    key=self._funckey
                ),
                self._funckey
            )
        ]


class TaxWithholdingIVAReport(models.AbstractModel):
    _name = 'report.tax_withholdings.template_tax_withholding_iva'
    _description = 'Tax Withholding IVA Report'
    _inherit = 'report.tax_withholdings.mixin'

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
        if record.sequence_withholding_iva:
            data["number_withholding"] = record.withholding_number
        else:
            data["number_withholding"] = _('To be defined')
        data["company_street"] = ' '.join([
            self.env.company.street or '',
            self.env.company.street2 or ''
        ]).upper().strip()
        return data

    def validate_record(self, record):
        super().validate_record(record)
        if (record.withholding_iva or 0.0) >= 0.0:
            raise UserError(_("This invoice has no withholding tax"))


class TaxWithholdingISLRReport(models.AbstractModel):
    _name = 'report.tax_withholdings.template_tax_withholding_islr'
    _description = 'Tax Withholding ISLR Report'
    _inherit = 'report.tax_withholdings.mixin'

    def extract_data(self, record):
        # Buscar líneas que contengan "SUSTRAENDO" en su descripción
        sustraendo_amount = 0.0
        for line in record.invoice_line_ids:
            if line.name and 'SUSTRAENDO' in line.name.upper():
                sustraendo_amount += line.price_total
        
        data = {
            "amount_base": record.amount_untaxed - record.vat_exempt_amount_islr,
            "amount_total": record.amount_total_islr,
            "amount_withholding": record.withholding_opp_islr,
            "total_purchase": record.amount_total_purchase,
            "percentage": record.withholding_percentage_islr,
            "subtracting": sustraendo_amount if sustraendo_amount > 0 else record.subtracting,
            "total_withheld": record.total_withheld,
            "code": record.withholding_code_islr
        }

        if record.sequence_withholding_islr:
            date = record.date or record.invoice_date
            data["number_withholding"] = f"{date:%Y%m}{record.sequence_withholding_islr:>08}"
        else:
            data["number_withholding"] = _('To be defined')

        return data

    def validate_record(self, record):
        super().validate_record(record)

        if not record.withholding_code_islr:
            raise ValidationError(_("Withholding requires the Withholding Code"))

        if (record.withholding_islr or 0.0) >= 0.0:
            raise UserError(_("This invoice has no withholding tax"))
