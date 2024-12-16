# -*- coding: utf-8 -*-
# Modificado por Pascual Chavez
from odoo import api, models
import logging

_log = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def get_details(self, barcode):
        multi_barcode_ids = False
        check_barcode = barcode
        product_details = self.search([('barcode', '=', check_barcode)])
        if not product_details and self.env['ir.module.module'].search([('name', '=', 'sale_pos_multi_barcodes_app'),
                                                                        ('state', '=', 'installed')]):
            multi_barcode_ids = self.multi_barcode_ids.search([('multi_barcode', '=', check_barcode)])
            product_details = multi_barcode_ids.product_tmpl_id
        IrDefault = self.env['ir.default'].sudo()
        if self.user_has_groups('tis_price_checker_kiosk_sp.group_price_checker_sp'):
            if self.env.user.kiosk_pricelist_id:
                price_list = self.env.user.kiosk_pricelist_id.id
        else:
            price_list = IrDefault.get(
                'res.config.settings', "kiosk_pricelist_id")
        uom_id_show = IrDefault.get(
            'res.config.settings', "show_uom")
        if uom_id_show:
            uom_id = product_details.uom_id.name
        else:
            uom_id = False

        tax_regular = 0
        tax_off = 0
        get_price_regular = 0
        get_price_off = 0
        min_quantity = 0
        if product_details.id and price_list:
            price_list_details = self.env['product.pricelist'].search([('id', '=', price_list)])
            get_price_regular = self.env['product.pricelist'].search([('id', '=', price_list)]).get_product_price_rule(
                product_details, 1, False)
            get_price_off = self.env['product.pricelist'].search([('id', '=', price_list)]).get_product_price_rule(
                product_details, 9999999, False)
            min_quantity = self.env['product.pricelist.item'].browse(get_price_off[1]).min_quantity
            price_regular_rule_id = get_price_regular[1]
            price_off_rule_id = get_price_off[1]
            get_price_regular = get_price_regular[0]
            get_price_off = get_price_off[0]
            price_regular_compute_price = price_list_details.item_ids.search(
                [('id', '=', price_regular_rule_id)]).compute_price
            price_off_compute_price = price_list_details.item_ids.search([('id', '=', price_off_rule_id)]).compute_price
            if price_regular_compute_price == 'formula':
                if product_details.taxes_id:
                    for tax in product_details.taxes_id:
                        # if not tax.price_include:
                        if tax.amount_type == 'fixed':
                            tax_regular += tax.amount
                        if tax.amount_type == 'percent':
                            tax_regular += (get_price_regular / 100) * tax.amount
                        # else:
                        #     tax_regular = tax.amount / 100 * get_price_regular
                get_price_regular = round(get_price_regular + tax_regular, 2)
            elif price_off_compute_price == 'fixed':
                pass

            if price_off_compute_price == 'formula':
                if product_details.taxes_id:
                    for tax in product_details.taxes_id:
                        # if not tax.price_include:
                        if tax.amount_type == 'fixed':
                            tax_off += tax.amount
                        if tax.amount_type == 'percent':
                            tax_off += (get_price_off / 100) * tax.amount
                        # else:
                        #     tax_off = tax.amount / 100 * get_price_off
                get_price_off = round(get_price_off + tax_off, 2)
            elif price_off_compute_price == 'fixed':
                pass
        else:
            get_price_regular = product_details.standard_price
        barcode = product_details.barcode
        default_code = product_details.default_code
        if multi_barcode_ids:
            barcode = str(check_barcode)
            default_code = str(check_barcode)
        return product_details.id, product_details.name, get_price_regular, barcode, \
               default_code, get_price_off, product_details.currency_id.symbol, min_quantity
