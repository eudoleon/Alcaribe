from odoo import models, fields, api, _


class AllowEditReconciledWizard(models.TransientModel):
    _name = 'allow.edit.reconciled.wizard'
    _description = 'Allow Edit Reconciled Wizard'

    note = fields.Text(string='Note')

    def action_apply(self):
        moves = self.env.context.get('active_ids') or []
        if not moves:
            return {'type': 'ir.actions.client', 'tag': 'reload'}
        self.env['account.move'].browse(moves).with_context(allow_edit_reconciled=True).write({'narration': (self.note or '')})
        return {'type': 'ir.actions.client', 'tag': 'reload'}
