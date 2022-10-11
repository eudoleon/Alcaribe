from odoo import models, fields

class AccountMoveLineHide(models.Model):
    _inherit = 'account.move.line'

    loc_ven = fields.Boolean(compute='_change_status', default=lambda self: self.env.company.loc_ven)

    def _change_status(self):
        self.loc_ven = self.env.company.loc_ven


class ResPartnerHide(models.Model):
    _inherit = 'res.partner'

    loc_ven = fields.Boolean(compute='_change_status', default=lambda self: self.env.company.loc_ven)

    def _change_status(self):
        self.loc_ven = self.env.company.loc_ven



class AccountMoveHide(models.Model):
    _inherit = 'account.move'

    loc_ven = fields.Boolean(compute='_change_status', default=lambda self: self.env.company.loc_ven)

    def _change_status(self):
        self.loc_ven = self.env.company.loc_ven


class AccountMoveHide(models.Model):
    _inherit = 'account.tax'

    loc_ven = fields.Boolean(compute='_change_status', default=lambda self: self.env.company.loc_ven)

    def _change_status(self):
        self.loc_ven = self.env.company.loc_ven