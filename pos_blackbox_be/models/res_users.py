from odoo import models, fields, api
from odoo.addons.base.models import res_users as ru
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class ResUser(models.Model):
    _inherit = 'res.users'

    # bis number is for foreigners in Belgium
    insz_or_bis_number = fields.Char("INSZ or BIS number",
                                     help="Social security identification number")
    session_clocked_ids = fields.Many2many(
        'pos.session',
        'users_session_clocking_info',
        string='Session Clocked In',
        help='This is a technical field used for tracking the status of the session for each users.',
    )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['insz_or_bis_number']

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ['insz_or_bis_number']

    @api.constrains('insz_or_bis_number')
    def _check_insz_or_bis_number(self):
        for rec in self:
            if rec.insz_or_bis_number and (len(rec.insz_or_bis_number) != 11 or not rec.insz_or_bis_number.isdigit()):
                raise ValidationError(_("The INSZ or BIS number has to consist of 11 numerical digits."))

    @api.model
    def create(self, values):
        filtered_values = {field: ('********' if field in ru.USER_PRIVATE_FIELDS else value)
                               for field, value in values.items()}
        self.env['pos_blackbox_be.log'].sudo().create(filtered_values, "create", self._name, values.get('login'))

        return super(ResUser, self).create(values)

    def write(self, values):
        filtered_values = {field: ('********' if field in ru.USER_PRIVATE_FIELDS else value)
                               for field, value in values.items()}
        for user in self:
            self.env['pos_blackbox_be.log'].sudo().create(filtered_values, "modify", user._name, user.login)

        return super(ResUser, self).write(values)

    def unlink(self):
        for user in self:
            self.env['pos_blackbox_be.log'].sudo().create({}, "delete", user._name, user.login)

        return super(ResUser, self).unlink()
