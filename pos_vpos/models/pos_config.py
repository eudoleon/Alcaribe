# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PosConfig(models.Model):
    _inherit = 'pos.config'

    vpos =fields.Boolean(string="VPOS")
    vpos_restApi = fields.Char('VPOS Terminal Url',default='http://localhost:8085')

