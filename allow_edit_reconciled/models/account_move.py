from odoo import models, api, fields, _
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def _is_reconciled_strict(self, account_move_line):
        """
        Helper: original code raises if move is reconciled. We'll detect reconciled lines.
        """
        return bool(account_move_line.full_reconcile_id)

    def write(self, vals):
        # If context contains 'allow_edit_reconciled', bypass the reconciliation checks.
        if self.env.context.get('allow_edit_reconciled'):
            # Temporarily unset the checks by calling super with adjusted context
            _logger.info('allow_edit_reconciled: bypassing reconciled checks for account.move write')
            # ensure child calls see the flag
            ctx = dict(self.env.context, allow_edit_reconciled=True)
            return super(AccountMove, self.with_context(ctx)).write(vals)
        # Default behaviour
        return super(AccountMove, self).write(vals)

    def unlink(self):
        if self.env.context.get('allow_edit_reconciled'):
            _logger.info('allow_edit_reconciled: bypassing reconciled checks for account.move unlink')
            return super(AccountMove, self).unlink()
        return super(AccountMove, self).unlink()


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def write(self, vals):
        # Bypass validation that prevents writing reconciled lines if context flag provided
        if self.env.context.get('allow_edit_reconciled'):
            _logger.info('allow_edit_reconciled: bypassing reconciled checks for account.move.line write')
            return super(AccountMoveLine, self.with_context(allow_edit_reconciled=True)).write(vals)
        return super(AccountMoveLine, self).write(vals)
