{
    "name": "Allow Edit Reconciled Entries",
    "version": "16.0.1.0.0",
    "category": "Accounting",
    "summary": "Allow editing invoices/account moves that have reconciled lines by bypassing the built-in restriction",
    "description": "Temporary module to bypass 'cannot modify reconciled entry' restriction for editing legacy invoices. Use with caution.",
    "author": "GitHub Copilot",
    "depends": ["account"],
    "data": [
        "security/ir.model.access.csv",
        "views/actions.xml",
    ],
    "installable": True,
    "application": False,
}
