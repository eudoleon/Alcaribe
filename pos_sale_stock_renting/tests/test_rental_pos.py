# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from freezegun import freeze_time

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo import fields
from datetime import timedelta
from odoo.tests import Form
from odoo.tests.common import tagged


@tagged('post_install', '-at_install')
class TestPoSRental(TestPointOfSaleHttpCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        if 'sale_order_line_id' not in cls.env['pos.order.line']:
            cls.skipTest(cls, "`pos_sale` is not installed")

    def test_rental_with_lots(self):
        """ Test rental product with lots """
        self.tracked_product_id = self.env['product.product'].create({
            'name': 'Test2',
            'categ_id': self.env.ref('product.product_category_all').id,  # remove category if possible?
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'uom_po_id': self.env.ref('uom.product_uom_unit').id,
            'available_in_pos': True,
            'rent_ok': True,
            'type': 'product',
            'tracking': 'serial',
        })

        # Set Stock quantities

        self.lot_id1 = self.env['stock.lot'].create({
            'product_id': self.tracked_product_id.id,
            'name': "123456789",
            'company_id': self.env.company.id,
        })
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        quants = self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.tracked_product_id.id,
            'inventory_quantity': 1.0,
            'lot_id': self.lot_id1.id,
            'location_id': warehouse.lot_stock_id.id,
        })
        quants.action_apply_inventory()

        # Define rental order and lines

        self.cust1 = self.env['res.partner'].create({'name': 'test_rental_1'})

        self.sale_order_id = self.env['sale.order'].create({
            'partner_id': self.cust1.id,
            'partner_invoice_id': self.cust1.id,
            'partner_shipping_id': self.cust1.id,
        })

        self.order_line_id2 = self.env['sale.order.line'].create({
            'order_id': self.sale_order_id.id,
            'product_id': self.tracked_product_id.id,
            'product_uom_qty': 0.0,
            'product_uom': self.tracked_product_id.uom_id.id,
            'is_rental': True,
            'start_date': fields.Datetime.today(),
            'return_date': fields.Datetime.today() + timedelta(days=3),
            'price_unit': 250,
        })
        self.main_pos_config.open_ui()
        self.start_tour(
            "/pos/web?config_id=%d" % self.main_pos_config.id,
            "OrderLotsRentalTour",
            login="accountman",
        )
        self.main_pos_config.current_session_id.action_pos_session_closing_control()
        self.assertEqual(self.sale_order_id.order_line.pickedup_lot_ids.name, '123456789')

    def test_check_qty_delivered_after_rental_return(self):
        # Create a rental product
        self.tracked_product_id = self.env['product.product'].create({
            'name': 'Test2',
            'categ_id': self.env.ref('product.product_category_all').id,
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'uom_po_id': self.env.ref('uom.product_uom_unit').id,
            'available_in_pos': True,
            'rent_ok': True,
            'type': 'product',
            'tracking': 'none',
        })

        #create a rental order and lines with this product
        self.cust1 = self.env['res.partner'].create({'name': 'test_rental_1'})
        self.sale_order_id = self.env['sale.order'].create({
            'partner_id': self.cust1.id,
            'partner_invoice_id': self.cust1.id,
            'partner_shipping_id': self.cust1.id,
        })
        self.order_line_id2 = self.env['sale.order.line'].create({
            'order_id': self.sale_order_id.id,
            'product_id': self.tracked_product_id.id,
            'product_uom_qty': 1,
            'product_uom': self.tracked_product_id.uom_id.id,
            'is_rental': True,
            'start_date': fields.Datetime.today(),
            'return_date': fields.Datetime.today() + timedelta(days=3),
            'price_unit': 1,
        })

        #settle the order in pos

        self.main_pos_config.open_ui()
        self.start_tour(
            "/pos/web?config_id=%d" % self.main_pos_config.id,
            "PosSettleRentalOrderWithImport",
            login="accountman",
        )
        self.main_pos_config.current_session_id.action_pos_session_closing_control()

        #check the quantity delivered
        self.assertEqual(self.sale_order_id.order_line.qty_delivered, 1)

        #return the product using the rental order wizard
        return_action = self.sale_order_id.open_return()
        wizard = Form(self.env['rental.order.wizard'].with_context(return_action['context'])).save()
        with freeze_time(self.order_line_id2.return_date):
            wizard.apply()

        self.assertEqual(self.sale_order_id.order_line.qty_delivered, 1)
