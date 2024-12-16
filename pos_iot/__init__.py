# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models

def uninstall_hook(cr, registry):
    cr.execute("SELECT 1 FROM ir_module_module WHERE name = 'pos_enterprise' AND state = 'installed'")
    if cr.rowcount:
        cr.execute("UPDATE pos_config SET is_posbox = False WHERE is_posbox")
