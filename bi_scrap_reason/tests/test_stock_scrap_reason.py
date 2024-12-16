# Copyright 2023 bitigloo <http://www.bitigloo.com>
# License GPL-3.0 or laterGPL-3 or any later version (https://www.gnu.org/licenses/licenses.html#LicenseURLs).

from odoo.tests.common import TransactionCase


class TestStockScrapReason(TransactionCase):
    def setUp(self):
        super(TestStockScrapReason, self).setUp()
        self.ScrapReason = self.env['stock.scrap.reason']

    def test_compute_scrap_order_count(self):
        # Create a product
        product = self.env['product.product'].create({'name': 'Test Product'})

        # Create a scrap reason
        reason = self.ScrapReason.create({'name': 'Test Reason'})

        # Create scrap orders associated with the reason
        self.env['stock.scrap'].create({'reason_id': reason.id, 'product_id': product.id, 'state': 'done'})
        self.env['stock.scrap'].create({'reason_id': reason.id, 'product_id': product.id, 'state': 'done'})
        self.env['stock.scrap'].create({'reason_id': reason.id, 'product_id': product.id, 'state': 'draft'})   # This one should be ignored

        # Trigger the computation method
        reason._compute_scrap_order_count()

        # Check if scrap_order_count is correctly computed
        self.assertEqual(reason.scrap_order_count, 2, "Scrap order count should be 2")

    def test_action_see_scrap_orders(self):
        # Create a product
        product = self.env['product.product'].create({'name': 'Test Product'})

        # Create a scrap reason
        reason = self.ScrapReason.create({'name': 'Test Reason'})

        # Create scrap orders associated with the reason
        scrap1 = self.env['stock.scrap'].create({'reason_id': reason.id, 'product_id': product.id, 'state': 'done'})
        scrap2 = self.env['stock.scrap'].create({'reason_id': reason.id, 'product_id': product.id, 'state': 'done'})

        # Call the action
        action = reason.action_see_scrap_orders()

        # Get the domains and sort them for comparison
        expected_domain = [('id', 'in', [scrap2.id, scrap1.id])]
        actual_domain = action['domain']

        # Check if the sorted lists are equal
        self.assertEqual(expected_domain, actual_domain, "Domain should be the same")
