# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies

from odoo import api, models
from odoo.osv.expression import is_leaf, OR


class ShProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def search_fetch(self, domain, field_names, offset=0, limit=None, order=None):
        """
            Overrides By Softhealer Technologies

            Multi barcode domain Added.
        """
        if domain and all("barcode" in lf for lf in domain):
            new_domain = []
            for element in domain:
                if is_leaf(element) and element[0] == "barcode":
                    new_domain = [('barcode_line_ids.name', element[1], element[2])]
                    break
            if new_domain:
                domain = OR([domain, new_domain])

        return super().search_fetch(domain, field_names, offset=offset, limit=limit, order=order)
