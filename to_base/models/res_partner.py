from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _is_foreigner(self, force_company=None):
        self.ensure_one()
        company = force_company or self.company_id or self.env.company
        return self.country_id != company.country_id
