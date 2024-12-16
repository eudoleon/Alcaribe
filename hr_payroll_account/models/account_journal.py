#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def unlink(self):
        if self._context.get(MODULE_UNINSTALL_FLAG):
            return super().unlink()

        journal = self.env.ref('hr_payroll_account.hr_payroll_account_journal')
        return super(AccountJournal, self - journal).unlink()
