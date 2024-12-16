# coding: utf-8
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
import calendar
from odoo.exceptions import UserError, ValidationError

class HrLeave(models.Model):
    _inherit = 'hr.leave'

    descontar_nom = fields.Boolean(default=True)#odoo 14