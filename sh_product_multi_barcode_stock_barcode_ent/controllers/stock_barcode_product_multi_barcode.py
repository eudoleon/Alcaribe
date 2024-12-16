# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies

from collections import defaultdict

from odoo import http
from odoo.http import request
from odoo.osv import expression
from odoo.addons.stock_barcode.controllers.stock_barcode import StockBarcodeController


class StockBarcodeMultiBarcodeSupport(StockBarcodeController):
    @http.route()
    def get_specific_barcode_data(self, barcode, model_name, domains_by_model=False):
        nomenclature = request.env.company.nomenclature_id
        # Adapts the search parameters for GS1 specifications.
        operator = '='
        limit = None if nomenclature.is_gs1_nomenclature else 1
        if nomenclature.is_gs1_nomenclature:
            try:
                # If barcode is digits only, cut off the padding to keep the original barcode only.
                barcode = str(int(barcode))
                operator = 'ilike'
            except ValueError:
                pass  # Barcode isn't digits only.

        domains_by_model = domains_by_model or {}
        barcode_field_by_model = self._get_barcode_field_by_model()
        result = defaultdict(list)
        model_names =[model_name] if model_name else list(barcode_field_by_model.keys())

        for model in model_names:
            domain = [(barcode_field_by_model[model], operator, barcode),
                      ('company_id', 'in', [False, *self._get_allowed_company_ids()])]

            # Softhealer Custom Code
            # Multi barcode domain added
            if model == "product.product":
                domain = [('company_id', 'in', [False, *self._get_allowed_company_ids()]),
                          '|',
                          (barcode_field_by_model[model], operator, barcode),
                          ('barcode_line_ids.name', operator, barcode),]
            # Softhealer Custom Code

            domain_for_this_model = domains_by_model.get(model)
            if domain_for_this_model:
                domain = expression.AND([domain, domain_for_this_model])
            record = request.env[model].with_context(
                display_default_code=False).search(domain, limit=limit)
            if record:
                # Softhealer Custom Code
                vals_list = record.read(
                    request.env[model]._get_fields_stock_barcode(), load=False)
                if model == "product.product" and vals_list:
                    # add products multi barcodes value on product results list of dictatory.
                    copy_vals = vals_list[0].copy()
                    for m_barcode in record.barcode_line_ids:
                        copy_vals.update({"barcode": m_barcode.name})
                        vals_list.append(copy_vals.copy())

                result[model] += vals_list
                if hasattr(record, '_get_stock_barcode_specific_data'):
                    additional_result = record._get_stock_barcode_specific_data()
                    for key in additional_result:
                        result[key] += additional_result[key]
        return result
