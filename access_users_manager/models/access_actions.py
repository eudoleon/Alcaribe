# -*- coding: utf-8 -*-

from odoo import api, models


class IrActionsActions(models.Model):
    _inherit = 'ir.actions.actions'

    @api.model_create_multi
    def create(self, vals):
        """When any new record was created then it will create inside ou custom model also."""
        records = super(IrActionsActions, self).create(vals)
        for rec in records:
            self.env['report.action.data'].create({'name': rec.name, 'access_action_id': rec.id})
        return records

    def unlink(self):
        """When any record is deleted then it will delete record inside our custom model as well."""

        for record in self:
            self.env['report.action.data'].sudo().search([('access_action_id', '=', record.id)]).unlink()
        return super(IrActionsActions, self).unlink()
