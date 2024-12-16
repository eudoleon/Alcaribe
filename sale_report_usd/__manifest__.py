# Copyright 2023 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)
{
    "name": "Reporte USD EASY SOLUTION",
    "summary": "Reporte en USD",
    "version": "16.0.1.0.0",
    "author": "David Alejandro de la Rosa",
    "license": "AGPL-3",
    "category": "Sale",
    "depends": [
        "pos_sale",
        "sale"
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/pos.xml",
        "views/sale.xml",
    ],
    "application": False,
    "installable": True,
}
