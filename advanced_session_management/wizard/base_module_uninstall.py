from odoo import models


class base_module_uninstall(models.TransientModel):
    _inherit = "base.module.uninstall"
   
    def action_uninstall(self):
        if 'advanced_session_management' in self.module_ids.mapped('name'):
            self.env['login.log'].search([]).unlink()
            # self._cr.commit()
        return super(base_module_uninstall, self).action_uninstall()
