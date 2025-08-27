Allow Edit Reconciled
=====================

This small Odoo 16 addon allows editing account.moves and account.move.lines that are reconciled by setting the context key `allow_edit_reconciled`.

Usage:
- Install the module.
- Call write/unlink on the invoice with context `{'allow_edit_reconciled': True}` (this module will also respect the context from RPC/UI).

WARNING: This bypasses legal/accounting protections. Use only for controlled data fixes and with accounting approval.
