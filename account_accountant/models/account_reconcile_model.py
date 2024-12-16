from odoo import models, tools


class AccountReconcileModel(models.Model):
    _inherit = 'account.reconcile.model'

    def run_auto_reconciliation(self):
        """ Tries to auto-reconcile as many statements as possible within time limit
        arbitrary set to 3 minutes (the rest will be reconciled asynchronously with the regular cron).
        """
        cron_limit_time = tools.config['limit_time_real_cron']  # default is -1
        limit_time = cron_limit_time if 0 < cron_limit_time < 180 else 180
        self.env['account.bank.statement.line']._cron_try_auto_reconcile_statement_lines(limit_time=limit_time)
