# Copyright 2023 bitigloo <http://www.bitigloo.com>
# License GPL-3.0 or laterGPL-3 or any later version (https://www.gnu.org/licenses/licenses.html#LicenseURLs).

{
    "name": "Add Scrap Reason & Note - bitigloo",
    "version": "16.0.1.0",
    "category": "Inventory",
    "author": "bitigloo GmbH",
    "summary": "Select a reason and add a note on Scrap",
    "description": """
It makes it possible to select a reason and add a note on Scrap.
================================================================

This module makes it possible to defined some reasons in the configurations and
then on Scrap wizard or form view, we can select the reason for Scrap. Besides,
it adds a Note field on those views.
""",
    "depends": [
        "stock",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/stock_scrap_views.xml",
        "views/stock_scrap_reason_views.xml",
    ],
    "installable": True,
    "website": "https://www.bitigloo.com",
    "images": ['static/description/background.png'],
    "license": "GPL-3 or any later version",
    "support": "apps@bitigloo.com",
}
