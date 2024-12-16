# coding: utf-8
###########################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64, time


class TxtIva(models.Model):
    _name = "account.wh.iva.txt"
    _check_company_auto = True
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def _default_period_id(self):
        """ Return current period
        """
        fecha = time.strftime('%m/%Y')
        periods = self.env['account.period'].search([('code', '=', fecha)])
        return periods and periods[0].id or False

    name = fields.Char(
        string='Descripción', size=128, required=True,
        default=lambda self: 'Retención IVA ' + time.strftime('%m/%Y'),
        help="Description about statement of withholding income")
    company_id = fields.Many2one(
        'res.company', string='Compañia', required=True, help='Company', readonly=True, store=True,
        default=lambda self: self.env.company)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmado'),
        ('done', 'Realizado'),
        ('cancel', 'Cancelado')
    ], string='Estado', readonly=True, default='draft',
        help="proof status")
    period_id = fields.Date(string='Periodo')
    type = fields.Boolean(
        string='Retención de Proveedores?', required=True,
        states={'draft': [('readonly', False)]}, default=True,
        help="Select the type of retention to make")
    date_start = fields.Date(
        string='Fecha de Inicio', required=True,
        states={'draft': [('readonly', False)]},
        help="Fecha de inicio del período")
    date_end = fields.Date(
        string='Fecha Fin', required=True,
        states={'draft': [('readonly', False)]},
        help="Fecha de Fin del período")
    txt_ids = fields.One2many(
        'account.wh.iva.txt.line', 'txt_id',
        states={'draft': [('readonly', False)]},
        help='Txt líneas de campo de ar requeridas por SENIAT para '
             'Retención de IVA')
    amount_total_ret = fields.Float(
        string='Monto Total Retenido',
        #   compute='_get_amount_total',
        help="Monto Total Retenido")
    amount_total_base = fields.Float(
        string='Total de la Base Imponible',
        #   compute='_get_amount_total_base',
        help="Total de la Base Imponible")
    txt_name = fields.Char('Nombre Archivo')
    txt_file = fields.Binary('Descargar TXT', states={'done': [('invisible', False)]})

    def _get_amount_total(self):
        """ Return total amount withheld of each selected bill
        """
        res = {}

        for txt in self.browse(self.ids):
            res[txt.id] = 0.0
            if txt.create_date:
                for txt_line in txt.txt_ids:
                    if txt_line.invoice_id.move_type in ['out_refund', 'in_refund']:
                        res[txt.id] -= txt_line.amount_withheld
                    else:
                        res[txt.id] += txt_line.amount_withheld
        return res

    def _get_amount_total_base(self):
        """ Return total amount base of each selected bill
        """
        res = {}
        for txt in self.browse(self.ids):
            res[txt.id] = 0.0
            if txt.create_date:
                for txt_line in txt.txt_ids:
                    if txt_line.invoice_id.move_type in ['out_refund', 'in_refund']:
                        res[txt.id] -= txt_line.untaxed
                    else:
                        res[txt.id] += txt_line.untaxed
        return res

    def name_get(self):
        """ Return a list with id and name of the current register
        """
        res = [(r.id, r.name) for r in self]
        return res

    def action_anular(self):
        """ Return document state to draft
        """
        self.write({'state': 'draft', 'txt_file': False, 'txt_name': False})
        return True

    def check_txt_ids(self):  # , cr, uid, ids, context=None
        """ Check that txt_iva has lines to process."""
        for awi in self:
            if not awi.txt_ids:
                raise UserError("Valores faltantes! \nFaltan líneas TXT de IVA !!!")
        return True

    def action_confirm(self):
        """ Transfers the document status to confirmed
        """
        txt_mismo_periodo = self.search([('date_start','=',self.date_start),('date_end','=', self.date_end),('state','!=','draft'),('company_id','=',self.company_id.id)])
        if txt_mismo_periodo:
            raise UserError(
                "Procedimiento inválido !! \nYa existe un documento TXT con el mismo perído.")
        self.check_txt_ids()
        self.write({'state': 'confirmed'})
        return True

    def action_generate_lines_txt(self):
        """ Current lines are cleaned and rebuilt
        """
        rp_obj = self.env['res.partner']
        voucher_obj = self.env['account.wh.iva']
        txt_iva_obj = self.env['account.wh.iva.txt.line']
        vouchers = []
        txt_brw = self.browse(self.ids)
        txt_ids = txt_iva_obj.search([('txt_id', '=', txt_brw.id)])
        if txt_ids:
            for txt in txt_ids: txt.unlink()

        if txt_brw.type:
            vouchers = voucher_obj.search([
                ('date_ret', '>=', txt_brw.date_start),
                ('date_ret', '<=', txt_brw.date_end),
                # ('period_id', '=', txt_brw.period_id.id),
                ('state', '=', 'done'),
                ('type', 'in', ['in_invoice', 'in_refund', 'in_debit'])])
        else:
            vouchers = voucher_obj.search([
                ('date_ret', '>=', txt_brw.date_start),
                ('date_ret', '<=', txt_brw.date_end),
                # ('period_id', '=', txt_brw.period_id.id),
                ('state', '=', 'done'),
                ('type', 'in', ['out_invoice', 'out_refund', 'in_debit'])])

        amount_amount = 0
        base_base = 0
        for voucher in vouchers:
            amount = 0
            base = 0
            amount_total = 0
            base_total = 0
            total_base_exent = 0
            acc_part_id = rp_obj._find_accounting_partner(voucher.partner_id)
            voucher_line_name = None
            voucher_invoice_id = None

            for voucher_lines in voucher.wh_lines.tax_line:
                voucher_invoice_id = voucher_lines.wh_vat_line_id.invoice_id.id
                if voucher.type in ['in_invoice', 'in_debit']:
                    if voucher_lines.alicuota == 0:
                        total_base_exent += voucher_lines.base
                        base_base += voucher_lines.base
                    elif voucher_lines.alicuota == 16:
                        amount_total += voucher_lines.amount_ret
                        amount_amount += voucher_lines.amount_ret
                        base_base += voucher_lines.base
                        base_total += voucher_lines.base
                        voucher_line_name = voucher_lines.name
                    elif voucher_lines.alicuota == 8:
                        amount_total += voucher_lines.amount_ret
                        amount_amount += voucher_lines.amount_ret
                        base_base += voucher_lines.base
                        base_total += voucher_lines.base
                        voucher_line_name = voucher_lines.name
                    elif voucher_lines.alicuota == 31:
                        amount_total += voucher_lines.amount_ret
                        amount_amount += voucher_lines.amount_ret
                        base_base += voucher_lines.base
                        base_total += voucher_lines.base
                        voucher_line_name = voucher_lines.name
                elif voucher.type in ['in_refund']:
                    if voucher_lines.alicuota == 0:
                        total_base_exent -= voucher_lines.base
                        base_base -= voucher_lines.base
                    elif voucher_lines.alicuota == 16:
                        amount_total -= voucher_lines.amount_ret
                        amount_amount -= voucher_lines.amount_ret
                        base_base -= voucher_lines.base
                        base_total -= voucher_lines.base
                        voucher_line_name = voucher_lines.name
                    elif voucher_lines.alicuota == 8:
                        amount_total -= voucher_lines.amount_ret
                        amount_amount -= voucher_lines.amount_ret
                        base_base -= voucher_lines.base
                        base_total -= voucher_lines.base
                        voucher_line_name = voucher_lines.name
                    elif voucher_lines.alicuota == 31:
                        amount_total -= voucher_lines.amount_ret
                        amount_amount -= voucher_lines.amount_ret
                        base_base -= voucher_lines.base
                        base_total -= voucher_lines.base
                        voucher_line_name = voucher_lines.name

            txt_iva_obj.create(
                {'partner_id': acc_part_id.id,
                 'voucher_id': voucher.id,
                 'invoice_id': voucher_invoice_id,
                 'txt_id': txt_brw.id,
                 # 'untaxed':  voucher_lines.base,
                 'untaxed': base_total,  # voucher_lines.base_ret,
                 'amount_withheld': amount_total,  # voucher_lines.amount_tax_ret,
                 'amount_sdcf': total_base_exent,  # self.get_amount_scdf(voucher_lines),
                 'tax_wh_iva_id': voucher_line_name if voucher_line_name else ' ',
                 })

            if voucher_lines.wh_vat_line_id.invoice_id.state not in ['posted']:
                pass
        self.update({'amount_total_ret': amount_amount,
                     'amount_total_base': base_base})
        return True

    @api.model
    def get_alicuota_iva(self, voucher_lines):
        tax_id = 0.00
        line_tax_obj = self.env['account.wh.iva.line.tax']
        line_tax_bw = line_tax_obj.search([('wh_vat_line_id', '=', voucher_lines.id)])

        for line_tax in line_tax_bw:
            if line_tax.amount != 0.0:
                tax_id = line_tax.id
        return tax_id

    @api.model
    def get_buyer_vendor(self, txt, txt_line):
        """ Return the buyer and vendor of the sale or purchase invoice
        @param txt: current txt document
        @param txt_line: One line of the current txt document
        """
        rp_obj = self.env['res.partner']
        vat_company = txt.company_id.partner_id.rif
        vat_partner = txt_line.partner_id.rif
        if not vat_partner:
            nationality = txt_line.partner_id.nationality
            cedula = txt_line.partner_id.identification_id
            if nationality and cedula:
                if nationality == 'V' or nationality == 'E':
                    vat_partner = str(nationality) + str(cedula)
                else:
                    vat_partner = str(cedula)
        if txt_line.invoice_id.move_type in ['out_invoice', 'out_refund']:
            vendor = vat_company
            buyer = vat_partner
        else:
            buyer = vat_company
            vendor = vat_partner
        return vendor, buyer

    @api.model
    def get_document_affected(self, txt_line):
        """ Return the reference or number depending of the case
        @param txt_line: line of the current document
        """
        number = '0'
        if txt_line.invoice_id.move_type in ['out_refund', 'in_refund'] and txt_line.invoice_id.name.find(
                "ND") != -1 or txt_line.invoice_id.name.find("nd") != -1 \
                or txt_line.invoice_id.name.find("NC") != -1 or txt_line.invoice_id.name.find("nc") != -1:
            number = txt_line.invoice_id.supplier_invoice_number
        elif txt_line.invoice_id:
            number = '0'
        return number

    @api.model
    def get_number(self, number, inv_type, max_size):
        """ Return a list of number for document number
        @param number: list of characters from number or reference of the bill
        @param inv_type: invoice type
        @param long: max size oh the number
        """
        if not number:
            return '0'
        result = ''
        for i in number:
            if inv_type == 'vou_number' and i.isdigit():
                if len(result) < max_size:
                    result = i + result
            elif i.isalnum():
                if len(result) < max_size:
                    result = i + result
        return result[::-1].strip()

    @api.model
    def get_document_number(self, txt_line, inv_type):
        """ Return the number o reference of the invoice into txt line
        @param txt_line: One line of the current txt document
        @param inv_type: invoice type into txt line
        """
        number = 0
        if txt_line.invoice_id.move_type in ['in_invoice', 'in_refund']:
            if not txt_line.invoice_id.supplier_invoice_number:
                raise UserError(
                    "Acción Invalida! \nNo se puede hacer el archivo txt porque la factura no tiene número de referencia gratis!")
            else:
                number = self.get_number(
                    txt_line.invoice_id.supplier_invoice_number.strip(),
                    inv_type, 20)
        elif txt_line.invoice_id.number:
            number = self.get_number(
                txt_line.invoice_id.number.strip(), inv_type, 20)
        return number

    @api.model
    def get_type_document(self, txt_line):
        """ Return the document type
        @param txt_line: line of the current document
        """
        inv_type = '03'
        if txt_line.invoice_id.move_type in ['out_invoice',
                                             'in_invoice'] and txt_line.invoice_id.partner_id.people_type_company != 'pjnd':
            inv_type = '01'
        elif txt_line.invoice_id.move_type in ['out_debit', 'in_debit'] and \
                txt_line.invoice_id.name:
            inv_type = '02'
        elif txt_line.invoice_id.move_type in ['in_invoice']:
            if txt_line.invoice_id.debit_origin_id:
                inv_type = '02'
        elif txt_line.invoice_id.partner_id.company_type == 'company' and txt_line.invoice_id.partner_id.people_type_company == 'pjnd':
            inv_type = '05'
        elif txt_line.invoice_id.move_type in ['out_invoice',
                                               'in_invoice'] and txt_line.invoice_id.partner_id.people_type_company != 'pjnd':
            inv_type = '01'

        return inv_type

    @api.model
    def get_max_aliquot(self, txt_line):
        """Get maximum aliquot per invoice"""
        res = []
        # for tax_line in txt_line.invoice_id.tax_line_ids:
        #     res.append(int(tax_line.tax_id.amount * 100))
        return res

    @api.model
    def get_amount_line(self, txt_line, amount_exempt):
        """Method to compute total amount"""
        ali_max = 0
        exempt = 0

        alic_porc = 0
        busq = self.env['account.tax'].search([('name', '=', txt_line.tax_wh_iva_id)])
        if busq:
            alic_porc = busq.amount
        if ali_max == alic_porc:
            exempt = amount_exempt

        total = (txt_line.untaxed + txt_line.amount_withheld +
                 exempt)

        return total, exempt

    @api.model
    def get_amount_exempt_document(self, txt_line):
        """ Return total amount not entitled to tax credit and the remaining
        amounts
        @param txt_line: One line of the current txt document
        """
        tax = 0
        amount_doc = 0
        for tax_lines in txt_line.voucher_id.wh_lines.tax_line:
            if 'Exento (compras)' in tax_lines.name or (tax_lines.base and not tax_lines.amount):
                tax = tax_lines.base + tax
            else:
                amount_doc = tax_lines.base + amount_doc
        return tax, amount_doc

    @api.model
    def get_alicuota(self, txt_line):
        """ Return aliquot of the withholding into line
        @param txt_line: One line of the current txt document
        """
        busq = self.env['account.tax'].search([('name', '=', txt_line.tax_wh_iva_id)])

        alic_porc = 0
        if busq:
            alic_porc = busq.amount

        return int(alic_porc)

    def get_period(self, date):
        split_date = str(date).split('-')

        return str(split_date[0]) + str(split_date[1])

    def generate_txt(self):
        """ Return string with data of the current document
        """
        txt_string = ''
        # txt_all_lines = []
        rp_obj = self.env['res.partner']
        value1 = 0
        value2 = 0
        for txt in self:
            expediente = '0'
            vat = txt.company_id.partner_id.rif
            amount_total11 = 0
            for txt_line in txt.txt_ids:
                vendor, buyer = self.get_buyer_vendor(txt, txt_line)
                if txt_line.invoice_id.move_type in ['out_invoice', 'out_refund']:
                    if vendor:
                        vendor = vendor.replace("-", "")
                    else:
                        vendor = ''
                    if txt_line.partner_id.company_type == 'person':
                        buyer = buyer
                    else:
                        if buyer:
                            buyer = buyer.replace("-", "")
                        else:
                            buyer = ''
                else:
                    if buyer:
                        buyer = buyer.replace("-", "")
                    else:
                        buyer = ' '
                    if txt_line.partner_id.company_type == 'person':
                        if vendor:
                            vendor = vendor.replace("-", "")
                    else:
                        if vendor:
                            vendor = vendor.replace("-", "")
                        else:
                            vendor = ''

                period = self.get_period(txt.date_start)
                # TODO: use the start date of the period to get the period2
                # with the 'YYYYmm'
                operation_type = ('V' if txt_line.invoice_id.move_type in ['out_invoice', 'out_refund'] else 'C')
                document_type = self.get_type_document(txt_line)
                document_number = self.get_document_number(txt_line, 'inv_number')
                control_number = self.get_number(txt_line.invoice_id.nro_ctrl, 'inv_ctrl', 20)
                document_affected = self.get_document_affected(txt_line)
                document_affected = document_affected.replace("-", "") if document_affected else '0'
                voucher_number = self.get_number(txt_line.voucher_id.number, 'vou_number', 14)
                amount_exempt, amount_untaxed = self.get_amount_exempt_document(txt_line)
                if document_type == '03':

                    sign = -1
                else:
                    sign = 1
                alicuota = float(self.get_alicuota(txt_line))
                amount_total, amount_exempt = self.get_amount_line(txt_line, amount_exempt)
                if txt_line.voucher_id == txt_line.invoice_id.wh_iva_id:
                    amount_total11 = txt_line.invoice_id.amount_total
                    amount_total2 = str(round(amount_total11, 2))
                    amount_untaxed = txt_line.untaxed
                else:
                    amount_total2 = str(round(amount_total, 2))
                    amount_untaxed = amount_untaxed
                untaxed2 = str(round(txt_line.untaxed, 2))
                amount_withheld2 = str(round(txt_line.amount_withheld, 2))
                amount_exempt2 = str(round(txt_line.amount_sdcf, 2))
                alicuota2 = alicuota
                if document_type == '05':
                    expediente = str(txt_line.invoice_id.nro_expediente_impor)

                # txt_all_lines.append({
                #     'txt_string': txt_string,
                #     'buyer': buyer,
                #     'period': period,
                #     'invoice_date': txt_line.invoice_id.date,
                #     'operation_type': operation_type,
                #     'document_type': document_type,
                #     'vendor': vendor,
                #     'document_number': document_number,
                #     'control_number': control_number,
                #     'amount_total2': self.formato_cifras(amount_total2),
                #     'amount_untaxed': self.formato_cifras(amount_untaxed),
                #     'amount_withheld2': self.formato_cifras(txt_line.amount_withheld2),
                #     'document_affected': document_affected,
                #     'voucher_number': voucher_number,
                #     'amount_exempt2': self.formato_cifras(amount_exempt2),
                #     'alicuota2': self.formato_cifras(alicuota2),
                #     'expediente': expediente
                # })
                # with_holding = self.env['account.wh.iva'].search([()])

                if float(amount_withheld2) < 0:
                    value1 = float(amount_withheld2) * -1
                else:
                    value1 = float(amount_withheld2)
                if float(amount_untaxed) < 0:
                    value2 = float(amount_untaxed) * -1
                else:
                    value2 = float(amount_untaxed)
                txt_string = (
                        txt_string + buyer + '\t' + period + '\t'
                        + (str(txt_line.invoice_id.date)) + '\t' + operation_type +
                        '\t' + document_type + '\t' + vendor + '\t' +
                        document_number + '\t' + control_number + '\t' +
                        self.formato_cifras(amount_total2) + '\t' +
                        # self.formato_cifras(txt_line.untaxed2) + '\t' +
                        self.formato_cifras(value2) + '\t' +
                        self.formato_cifras(value1) + '\t' + document_affected + '\t' + voucher_number
                        + '\t' + self.formato_cifras(amount_exempt2) + '\t' + self.formato_cifras(alicuota2)
                        + '\t' + expediente + '\n')
        return txt_string

    def _write_attachment(self, root):
        """ Encrypt txt, save it to the db and view it on the client as an
        attachment
        @param root: location to save document
        """
        fecha = time.strftime('%Y_%m_%d_%H%M%S')
        name = 'IVA_' + fecha + '.' + 'txt'
        #         self.env['ir.attachment'].create({
        #             'name': name,
        #             'datas': base64.encodestring(root),
        #             'datas_fname': name,
        #             'res_model': 'account.wh.iva.txt',
        #             'res_id': self.ids[0],
        #         })
        txt_name = name
        txt_file = root.encode('utf-8')
        txt_file = base64.encodebytes(txt_file)
        self.write({'txt_name': txt_name, 'txt_file': txt_file})
        msg = _("File TXT %s generated.") % name
        self.message_post(body=msg)

    def action_done(self):
        """ Transfer the document status to done
        """
        root = self.generate_txt()
        self._write_attachment(root)
        self.write({'state': 'done'})

        return True

    @staticmethod
    def formato_cifras(monto):
        cds = '0'
        monto = str(monto)
        if monto == '0':
            monto = '0.00'
        for i in range(0, len(monto)):
            if monto[i] == '.':
                cds = monto[i + 1:]
        if len(cds) == 2:
            imprimir0 = ''
        else:
            imprimir0 = '0'
        montofinal = monto + imprimir0
        return montofinal


class TxtIvaLine(models.Model):
    _name = "account.wh.iva.txt.line"

    partner_id = fields.Many2one(
        'res.partner', string='Comprador/Vendedor', readonly=True,
        help="Persona natural o jurídica que genera la Factura,"
             "Nota de crédito, nota de débito o certificación (vendedor)")
    invoice_id = fields.Many2one(
        'account.move', 'Factura/ND/NC', readonly=True,
        help="Fecha de factura, nota de crédito, nota de débito o certificado, "
             "Declaración de Importación")
    voucher_id = fields.Many2one(
        'account.wh.iva', string='Impuesto de Retención', readonly=True,
        help="Retencion de impuesto del valor agregado(IVA)")
    amount_withheld = fields.Float(
        string='Cantidad retenida', readonly=True, help='Cantidad retenida')
    amount_sdcf = fields.Float(
        string='Monto SDCF', readonly=True, help='Monto SDCF')
    untaxed = fields.Float(
        string='Base de la Retención', readonly=True, help='Base de la Retención')
    txt_id = fields.Many2one(
        'account.wh.iva.txt', string='Generar-Documento TXT IVA', readonly=True,
        help='Lineas de Retención')
    # tax_wh_iva_id = fields.Many2one(
    #     'account.wh.iva.line.tax', string='Líneas de impuesto de Retención de IVA')
    tax_wh_iva_id = fields.Char(
        string='Líneas de impuesto de Retención de IVA', readonly=True)

    _rec_name = 'partner_id'
