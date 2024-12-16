from odoo import models, fields, api
from odoo.exceptions import UserError,Warning
import logging
import math
import re
import time
import traceback

from odoo import api, fields, models, tools, _

class Impresoraadaptacioninvoices(models.Model):
    _inherit = 'account.move'

    estado_impreso = fields.Boolean('Estado_impresion', default=False)

    def reimprimir_orden(self):
        self.estado_impreso = False