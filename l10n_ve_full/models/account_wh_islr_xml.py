# coding: utf-8
import logging
import base64
import time
from xml.etree.ElementTree import Element, SubElement, tostring

from odoo import api, fields, models
from odoo.tools.translate import _
from odoo.addons import decimal_precision as dp

_logger = logging.getLogger(__name__)
ISLR_XML_WH_LINE_TYPES = [('invoice', 'Invoice'), ('employee', 'Employee')]


class IslrXmlWhDoc(models.Model):
    _name = "account.wh.islr.xml"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _check_company_auto = True
    _description = 'Generar archivo XML'

    @api.depends('xml_ids')
    def _get_amount_total(self):
        """ Return withhold total amount
        """
        self.amount_total_ret = 0.0
        for line in self.xml_ids:
            self.amount_total_ret += line.wh
        # return amount_ret

    @api.depends('xml_ids')
    def _get_amount_total_base(self):
        """ Return base total amount
        """
        self.amount_total_base = 0.0
        # for xml in self.browse():
        #   res[xml.id] = 0.0
        for line in self.xml_ids:
            self.amount_total_base += line.base
        # return amount_base

    @api.model
    def _get_company(self):
        user = self.env['res.users'].browse(self.env.uid)
        return user.company_id.id

    name = fields.Char(
        string='Descripción', size=128, required=True,
        default='Retención de ingresos ' + time.strftime('%m/%Y'),
        help="Descripción de la declaración de retención de ingresos")
    company_id = fields.Many2one(
        'res.company', string='Compañia', required=True,
        default=lambda self: self.env.company,
        help="Compañia")
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('generated', 'Generado'),
        ('confirmed', 'Confirmado'),
        ('done', 'Realizado'),
        ('cancel', 'Cencelado')
    ], string='Estado', readonly=True, default='draft',
        help="Estado del Vale")
    amount_total_ret = fields.Float(
        compute='_get_amount_total', digits=(16, 2), readonly=True,
        string='Total de retención de ingresos',
        help="Importe total de la retención")
    amount_total_base = fields.Float(
        compute='_get_amount_total_base', digits=(16, 2), readonly=True,
        string='Sin cantidad de impuestos', help="Total sin impuestos")
    xml_ids = fields.One2many(
        'account.wh.islr.xml.line', 'islr_xml_wh_doc', 'Líneas de documentos XML',
        readonly=True, states={'draft': [('readonly', False)]},
        help='ID de línea de factura de retención XML')
    invoice_xml_ids = fields.One2many(
        'account.wh.islr.xml.line', 'islr_xml_wh_doc', 'Líneas de documentos XML',
        readonly=True, states={'draft': [('readonly', False)]},
        help='ID de línea de factura de retención XML',
        domain=[('type', '=', 'invoice')])
    employee_xml_ids = fields.One2many(
        'account.wh.islr.xml.line', 'islr_xml_wh_doc', 'Líneas de documentos XML',
        readonly=True, states={'draft': [('readonly', False)]},
        help='ID de línea de empleado de retención XML',
        domain=[('type', '=', 'employee')])
    user_id = fields.Many2one(
        'res.users', string='Usuario', readonly=True,
        states={'draft': [('readonly', False)]},
        default=lambda self: self.env.user,
        help='Usuario que crea el documento')
    # rsosa: ID 95
    xml_filename = fields.Char('Nombre Archivo XML')
    xml_binary = fields.Binary('Archivo XML')
    # period_id = fields.Many2one(
    #        'account.period', string='Period', required=True,
    #       default=lambda s: s.period_return(),
    #      help="Period when the accounts entries were done")
    date_start = fields.Date("Fecha Inicio", required=True,
                             states={'draft': [('readonly', False)]},
                             help="Begin date of period")
    date_end = fields.Date("fecha Fin", required=True,
                           states={'draft': [('readonly', False)]},
                           help="Begin date of period")

    def copy(self, default=None):
        """ Initialized id by duplicating
        """
        if default is None:
            default = {}
        default = default.copy()
        default.update({
            'xml_ids': [],
            'invoice_xml_ids': [],
            'employee_xml_ids': [],
        })

        return super(IslrXmlWhDoc, self).copy(default)

    def get_period(self):

        split_date = str(self.date_end).split('-')

        return str(split_date[0]) + str(split_date[1])

    def period_return(self):
        """ Return current period
        """
        '''
        period_obj = self.pool.get('account.period')
        fecha = time.strftime('%m/%Y')
        period_id = period_obj.search([('code', '=', fecha)])
        if period_id:
            return period_id[0]
        else:
            return False

    def search_period(self, period_id, ids):
        """ Return islr lines associated with the period_id
        @param period_id: period associated with returned islr lines
        """
        if self._context is None:
            context = {}
        res = {'value': {}}
        if period_id:
            islr_line = self.pool.get('account.wh.islr.xml.line')
            islr_line_ids = islr_line.search(
                 [('period_id', '=', period_id)])
            if islr_line_ids:
                res['value'].update({'xml_ids': islr_line_ids})
                return res
        '''

    def name_get(self):
        """ Return id and name of all records
        """
        context = self._context or {}
        if not len(self.ids):
            return []

        res = [(r['id'], r['name']) for r in self.read(
            ['name'])]
        return res

    def action_anular1(self):
        """ Return the document to draft status
        """
        # context = self._context or {}
        return self.write({'state': 'draft', 'xml_binary': False, 'xml_filename': False})

    def action_confirm1(self):
        """ Passes the document to state confirmed
        """
        # to set date_ret if don't exists
        # obj_ixwl = self.env['account.wh.islr.xml.line']
        # self.invoice_xml_ids = obj_ixwl.search([('date_ret','>=',self.date_start),
        #                             ('date_ret','<=',self.date_end)])

        # for item in self.browse(self.ids):
        #    for ixwl in item.xml_ids:
        #        if not ixwl.date_ret and ixwl.islr_wh_doc_inv_id:
        #            obj_ixwl.write(
        #                 [ixwl.id],
        #                {'date_ret':
        #                    ixwl.islr_wh_doc_inv_id.islr_wh_doc_id.date_ret})
        #            ixwl.write({'date_ret':
        #                    ixwl.islr_wh_doc_inv_id.islr_wh_doc_id.date_ret})
        return self.write({'state': 'confirmed'})

    def action_generate_line_xml(self):
        """ Passes the document to state confirmed
        """
        # to set date_ret if don't exists
        obj_ixwl = self.env['account.wh.islr.xml.line']
        self.invoice_xml_ids = obj_ixwl.search([('date_ret', '>=', self.date_start),
                                                ('date_ret', '<=', self.date_end)])
        for l in self.invoice_xml_ids:
            new_rif = l.partner_vat
            if l.partner_id.rif:
                new_rif = l.partner_id.rif.replace("-", "")
            l.partner_vat = new_rif
        return True

    def action_done1(self):
        """ Passes the document to state done
        """
        # context = self._context or {}
        root = self._xml()
        self._write_attachment(root)
        self.write({'state': 'done'})
        return True

    @api.model
    def _write_attachment(self, root):
        """ Codify the xml, to save it in the database and be able to
        see it in the client as an attachment
        @param root: data of the document in xml
        """
        fecha = time.strftime('%Y_%m_%d_%H%M%S')
        name = 'ISLR_' + fecha + '.' + 'xml'
        #         self.env('ir.attachment').create(cr, uid, {
        #             'name': name,
        #             'datas': base64.encodestring(root),
        #             'datas_fname': name,
        #             'res_model': 'account.wh.islr.xml',
        #             'res_id': ids[0],
        #         }, context=context
        #         )
        #         cr.commit()
        # rsosa: ID 95
        self.write({
            'xml_filename': name,
            'xml_binary': base64.encodebytes(root)
        })
        # self.log( self.ids[0], _("File XML %s generated.") % name)

    @api.model
    def indent(self, elem, level=0):
        """ Return indented text
        @param level: number of spaces for indentation
        @param elem: text to indentig
        """
        i = "\n" + level * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                self.indent(elem, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

    def import_xml_employee(self):
        ids = isinstance(self.ids, (int)) and [self.ids] or self.ids
        xml_brw = self.browse(ids)[0]
        # period = time.strptime(xml_brw.period_id.date_stop, '%Y-%m-%d')
        return {'name': _('Import XML employee'),
                'type': 'ir.actions.act_window',
                'res_model': 'employee.income.wh',
                'view_type': 'form',
                'view_id': False,
                'view_mode': 'form',
                'nodestroy': True,
                'target': 'new',
                'domain': "",
                'context': {
                    # 'default_period_id': xml_brw.period_id.id,
                    # 'islr_xml_wh_doc_id': xml_brw.id,
                    # 'period_code': "%0004d%02d" % (
                    #    period.tm_year, period.tm_mon),
                    'company_vat': xml_brw.company_id.partner_id.rif[0:]}}

    def download_xml_employee_template(self):
        return {
            "type": "ir.actions.act_url",
            "url": "/l10n_ve_full/static/src/csv/Plantilla_retencion_empleados.csv",
            "target": "new",
        }

    def _xml(self):
        """ Transform this document to XML format
        """
        rp_obj = self.env['res.partner']
        inv_obj = self.env['account.move']
        root = ''
        for ixwd_id in self.ids:
            wh_brw = self.browse(ixwd_id)

            # period = time.strptime(wh_brw.period_id.date_stop, '%Y-%m-%d')
            period = self.get_period()
            # period2 = "%0004d%02d" % (period.tm_year, period.tm_mon)

            local_ids = [int(i.id) for i in wh_brw.xml_ids]
            if local_ids:
                sql = '''
                SELECT partner_vat,control_number, porcent_rete,
                    concept_code,invoice_number,
                    SUM(COALESCE(base,0)) as base, account_invoice_id, date_ret
                FROM account_wh_islr_xml_line
                WHERE id in (%s)
                GROUP BY partner_vat, control_number, porcent_rete, concept_code,
                    invoice_number,account_invoice_id, date_ret ORDER BY concept_code ASC''' % ",".join(
                    map(str, local_ids))
                self.env.cr.execute(sql)
                xml_lines = self.env.cr.fetchall()
            else:
                xml_lines = []
            acc_prtner = rp_obj._find_accounting_partner(wh_brw.company_id.partner_id)
            if acc_prtner and acc_prtner.rif :
                company_vat = rp_obj._find_accounting_partner(wh_brw.company_id.partner_id).rif[0:]
            else:
                company_vat = ''
            company_vat = company_vat.replace("-", "")

            if wh_brw.company_id.partner_id and wh_brw.company_id.partner_id.rif :
                company_vat1 = wh_brw.company_id.partner_id.rif
            else:
                company_vat1 = ''

            company_vat1 = company_vat1.replace("-", "")
            root = Element("RelacionRetencionesISLR")
            # root.attrib['RifAgente'] = rp_obj._find_accounting_partner(wh_brw.company_id.partner_id).vat[0:] if wh_brw.company_id.partner_id.vat else ''
            x1 = "RifAgente"
            x2 = "Periodo"
            root.attrib[x1] = company_vat if company_vat1 else ''
            root.attrib[x2] = period

            for line in xml_lines:
                partner_vat, control_number, porcent_rete, concept_code, \
                invoice_number, base, inv_id, date_ret = line
                control_number = control_number.replace("-", "")
                invoice_number = invoice_number.replace("-", "")
                detalle = SubElement(root, "DetalleRetencion")
                SubElement(detalle, "RifRetenido").text = partner_vat

                SubElement(detalle, "NumeroFactura").text = invoice_number if len(invoice_number) < 11 else invoice_number[-10:]
                SubElement(detalle, "NumeroControl").text = control_number if len(control_number) < 11 else control_number[-10:]

                # SubElement(detalle, "NumeroFactura").text = ''.join(
                #    i for i in invoice_number if i.isdigit())[:] or '0'
                # SubElement(detalle, "NumeroControl").text = ''.join(
                #    i for i in control_number if i.isdigit())[:] or 'NA'
                if date_ret:
                    date_ret = time.strptime(str(date_ret), '%Y-%m-%d')
                    SubElement(detalle, "FechaOperacion").text = time.strftime(
                        '%d/%m/%Y', date_ret)
                # This peace of code will be left for backward compatibility
                # TODO: Delete on V8 onwards
                elif inv_id and inv_obj.browse(inv_id).islr_wh_doc_id:
                    date_ret = time.strptime(inv_obj.browse(
                        inv_id).islr_wh_doc_id.date_ret, '%Y-%m-%d')
                    SubElement(detalle, "FechaOperacion").text = time.strftime(
                        '%d/%m/%Y', date_ret)
                SubElement(detalle, "CodigoConcepto").text = concept_code
                SubElement(detalle, "MontoOperacion").text = str(base)
                SubElement(detalle, "PorcentajeRetencion").text = str(
                    porcent_rete)
        # self.indent(root)
        return tostring(root, encoding="ISO-8859-1")

class IslrXmlWhLine(models.Model):
    _name = "account.wh.islr.xml.line"
    _description = 'Generate XML Lines'

    concept_id = fields.Many2one(
        'account.wh.islr.concept', string='Concepto de Retencion',
        help="Concepto de retención asociado a esta tasa",
        required=True, ondelete='cascade')
    # period_id = fields.Many2one(
    #        'account.period', 'Period', required=False,
    #        help="Period when the journal entries were done")
    partner_vat = fields.Char(
        'RIF', size=10, required=True, help="Socio RIF")
    invoice_number = fields.Char(
        'Número de factura', size=20, required=True,
        default='0',
        help="Número de factura")
    control_number = fields.Char(
        'Numero de Control', size=20,
        default='NA',
        help="Reference")
    concept_code = fields.Char(
        'Código Conceptual', size=10, required=True, help="Código Conceptual")
    base = fields.Float(
        'Cantidad base', required=True,
        help="Amount where a withholding is going to be computed from",
        digits=(16, 2))
    raw_base_ut = fields.Float(
        'Cantidad de UT', digits=(16, 2),
        help="Cantidad de UT")
    raw_tax_ut = fields.Float(
        'Impuesto retenido de UT',
        digits=(16, 2),
        help="Impuesto retenido de UT")
    porcent_rete = fields.Float(
        'Tasa de retención', required=True, help="Tasa de retención",
        digits=(16, 2))
    wh = fields.Float(
        'Cantidad retenida', required=True,
        help="Cantidad retenida a socio",
        digits=(16, 2))
    rate_id = fields.Many2one(
        'account.wh.islr.rates', 'Tipo de persona',
        domain="[('concept_id','=',concept_id)]", required=False,
        help="Tipo de persona")
    islr_wh_doc_line_id = fields.Many2one(
        'account.wh.islr.doc.line', 'Documento de retención de ingresos',
        ondelete='cascade', help="Documento de retención de ingresos")
    account_invoice_line_id = fields.Many2one(
        'account.move.line', 'Línea de factura',
        help="Línea de factura a retener")
    account_invoice_id = fields.Many2one(
        'account.move', 'Factura', help="Factura para Retener")
    islr_xml_wh_doc = fields.Many2one(
        'account.wh.islr.xml', 'Documento XML ISLR', help="Impuesto sobre la renta XML Doc")
    partner_id = fields.Many2one(
        'res.partner', 'Empresa', required=True,
        help="Socio objeto de retención")
    sustract = fields.Float(
        'Sustraendo', help="Subtrahend",
        digits=(16, 2))
    islr_wh_doc_inv_id = fields.Many2one(
        'account.wh.islr.doc.invoices', 'Factura retenida',
        help="Facturas retenidas")
    date_ret = fields.Date('Fecha de Operacion')
    type = fields.Selection(
        ISLR_XML_WH_LINE_TYPES,
        string='Tipo', required=True, readonly=False,
        default='invoice')
    _rec_name = 'partner_id'

    def onchange_partner_vat(self, partner_id):
        """ Changing the partner, the partner_vat field is updated.
        """
        context = self._context or {}
        rp_obj = self.env['res.partner']
        acc_part_brw = rp_obj._find_accounting_partner(rp_obj.browse(
            partner_id))
        return {'value': {'partner_vat': acc_part_brw.rif[2:]}}

    def onchange_code_perc(self, rate_id):
        """ Changing the rate of the islr, the porcent_rete and concept_code fields
        is updated.
        """
        context = self._context or {}
        rate_brw = self.env['account.wh.islr.rates'].browse(rate_id)
        return {'value': {'porcent_rete': rate_brw.wh_perc,
                          'concept_code': rate_brw.code}}