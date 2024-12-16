# coding: utf-8
import time

from odoo import api
from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _
from odoo.addons import decimal_precision as dp


class AccountWhIslrDocInvoices(models.Model):
    _name = "account.wh.islr.doc.invoices"
    _description = 'Document and Invoice Withheld Income'

    @api.depends('islr_wh_doc_id.amount_total_ret')
    def _amount_all(self):
        """ Return all amount relating to the invoices lines
        """
        res = {}
        ut_obj = self.env['account.ut']
        for ret_line in self.browse(self.id):
            f_xc = ut_obj.sxc(
                ret_line.invoice_id.company_id.currency_id.id,
                ret_line.invoice_id.currency_id.id,
                ret_line.islr_wh_doc_id.date_uid)
            res[ret_line.id] = {
                'amount_islr_ret': 0.0,
                'base_ret': 0.0,
                'currency_amount_islr_ret': 0.0,
                'currency_base_ret': 0.0,
            }
            #for line in ret_line.iwdl_ids:
            #    res[ret_line.id]['amount_islr_ret'] += line.amount
            #    res[ret_line.id]['base_ret'] += line.base_amount
            #    res[ret_line.id]['currency_amount_islr_ret'] += \
            #        f_xc(line.amount)
            #    res[ret_line.id]['currency_base_ret'] += f_xc(line.base_amount)
            iwdl_local = self.env['account.wh.islr.doc.line'].search([('islr_wh_doc_id', '=', ret_line.islr_wh_doc_id.id)])
            for line in iwdl_local:
                res[ret_line.id]['amount_islr_ret'] += (line.base_amount * line.retencion_islr / 100) - line.subtract
                res[ret_line.id]['base_ret'] += line.base_amount
                if ret_line.invoice_id.currency_id == ret_line.invoice_id.company_id.currency_id:
                    res[ret_line.id]['currency_amount_islr_ret'] += f_xc(line.base_amount * line.retencion_islr / 100)
                    res[ret_line.id]['currency_base_ret'] += f_xc(line.base_amount)
                else:
                    module_dual_currency = self.env['ir.module.module'].sudo().search(
                        [('name', '=', 'account_dual_currency'), ('state', '=', 'installed')])
                    if module_dual_currency:
                        res[ret_line.id]['currency_amount_islr_ret'] += (
                            line.base_amount * line.retencion_islr / 100) * ret_line.invoice_id.tax_today
                        res[ret_line.id]['currency_base_ret'] += (line.base_amount) * ret_line.invoice_id.tax_today
                    else:
                        res[ret_line.id]['currency_amount_islr_ret'] += f_xc(
                            line.base_amount * line.retencion_islr / 100)
                        res[ret_line.id]['currency_base_ret'] += f_xc(line.base_amount)
        return res

    sustraendo = fields.Float('Sustraendo')

    islr_wh_doc_id= fields.Many2one(
            'account.wh.islr.doc', 'Retener documento', ondelete='cascade',
            help="Retención de documentos del impuesto sobre la renta generado por esta factura")
    invoice_id= fields.Many2one(
            'account.move', 'Factura', help="Factura retenida")
    supplier_invoice_number=fields.Char(related='invoice_id.supplier_invoice_number',
            string='Proveedor inv. #', size=64, store=False, readonly=True)
    islr_xml_id= fields.One2many(
            'account.wh.islr.xml.line', 'islr_wh_doc_inv_id', 'Retención de ISLR')
    #TODO revisar proceso de calculo de valores. Se crearan campos tradicionales
    #amount_islr_ret= fields.Float(compute='_amount_all',  digits=(16, 2), string='Withheld Amount',
    #        multi='all', help="Amount withheld from the base amount")
    #base_ret = fields.Float(compute='_amount_all',  digits=(16, 2), string='Base Amount',
    #        multi='all',
    #        help="Monto a partir del cual se calculará una retención")
    #currency_amount_islr_ret = fields.Float(compute='_amount_all',  digits=(16, 2),
    #                                        string='Moneda retenida Monto retenido', multi='all',
    #                                        help="Amount withheld from the base amount")
    #currency_base_ret = fields.Float(compute='_amount_all',  digits=(16, 2),
    #                                 string='Monto base en moneda extranjera', multi='all',
    #                                 help="Monto a partir del cual se calculará una retención")
    amount_islr_ret= fields.Float(string='Cantidad retenida', digits=(16, 2), help="Monto retenido del monto base")
    base_ret = fields.Float(string='Cantidad base', digits=(16, 2), help="Monto a partir del cual se calculará una retención")
    currency_amount_islr_ret = fields.Float(string='Moneda retenida Monto retenido', digits=(16, 2),
                                            help="Monto retenido del monto base")
    currency_base_ret = fields.Float(string='Monto base en moneda extranjera', digits=(16, 2),
                                     help="Monto a partir del cual se calculará una retención")
    iwdl_ids= fields.One2many(
            'account.wh.islr.doc.line', 'iwdi_id', 'Conceptos de retención',
            help='Conceptos de retención de esta factura retenida')
    move_id = fields.Many2one(
            'account.move', 'Entrada de diario', ondelete='restrict',
            readonly=True, help="Bono contable")

    _rec_rame = 'invoice_id'

    def get_amount_all(self, iwdi_brw):
        """ Return all amount relating to the invoices lines
        """
        res = {}
        ut_obj = self.env['account.ut']
        for ret_line in self.browse(iwdi_brw.id):
            f_xc = ut_obj.sxc(
                ret_line.invoice_id.company_id.currency_id.id,
                ret_line.invoice_id.currency_id.id,
                ret_line.islr_wh_doc_id.date_uid)
            res[ret_line.id] = {
                'amount_islr_ret': 0.0,
                'base_ret': 0.0,
                'currency_amount_islr_ret': 0.0,
                'currency_base_ret': 0.0,
            }
            iwdl_local = self.env['account.wh.islr.doc.line'].search([('islr_wh_doc_id', '=', ret_line.islr_wh_doc_id.id)])
            for line in iwdl_local:
                res[ret_line.id]['amount_islr_ret'] += (line.base_amount * line.retencion_islr / 100) - line.subtract
                res[ret_line.id]['base_ret'] += line.base_amount
                if ret_line.invoice_id.currency_id == ret_line.invoice_id.company_id.currency_id:
                    res[ret_line.id]['currency_amount_islr_ret'] += f_xc(line.base_amount * line.retencion_islr / 100)
                    res[ret_line.id]['currency_base_ret'] += f_xc(line.base_amount)
                else:
                    module_dual_currency = self.env['ir.module.module'].sudo().search(
                        [('name', '=', 'account_dual_currency'), ('state', '=', 'installed')])
                    if module_dual_currency:
                        res[ret_line.id]['currency_amount_islr_ret'] += (line.base_amount * line.retencion_islr / 100) * ret_line.invoice_id.tax_today
                        res[ret_line.id]['currency_base_ret'] += line.base_amount * ret_line.invoice_id.tax_today
                    else:
                        res[ret_line.id]['currency_amount_islr_ret'] += f_xc(
                            line.base_amount * line.retencion_islr / 100)
                        res[ret_line.id]['currency_base_ret'] += f_xc(line.base_amount)
                res[ret_line.id]['iwdl_ids'] = line.concept_id
                res['amount'] = res[ret_line.id].get('amount_islr_ret', 0.0)
        return res

    def _check_invoice(self):
        """ Determine if the given invoices are in Open State
        """
        self.context = self._context or {}
        ids = isinstance(self.ids, (int)) and [self.ids] or self.ids
        for iwdi_brw in self.browse(ids):
            if iwdi_brw.invoice_id.state != 'open':
                return False
        return True

    _constraints = [
        (_check_invoice, 'Error! The invoice must be in Open State.',
         ['invoice_id']),
    ]
    @api.model
    def _get_concepts(self, inv_id):
        """ Get a list of withholdable concepts (concept_id) from the invoice lines
        """
        context = self._context or {}
        ids = isinstance(inv_id, (int)) and [inv_id] or (isinstance(inv_id, (list)) and inv_id) or [inv_id.id]
        inv_obj = self.env['account.move']
        concept_set = set()
        #TODO VERIFICAR SI PARA CLEINTES TIENE EL MISMO COPORTAMIENTO PARA ELIMINAR ESTA LINEA
        #for i in inv_id:

        inv_brw = inv_obj.browse(ids)
        for ail in inv_brw.invoice_line_ids:
            if ail.concept_id and ail.concept_id.withholdable:
                concept_set.add(ail.concept_id.id)
        return list(concept_set)

    def _withholdable_invoices(self, inv_ids):
        """ Given a list of invoices return only those
        where there are withholdable concepts
        """
        context = self._context or {}
        #ids = isinstance(inv_ids, (int)) and [inv_ids] or inv_ids
        res_ids = []
        for iwdi_id in inv_ids:
            iwdi_id = self._get_concepts(iwdi_id) and iwdi_id
            if iwdi_id:
                res_ids += [iwdi_id]
        return res_ids


    @api.model
    def _get_wh(self, iwdl_id, concept_id):
        """ Return a dictionary containing all the values of the retention of an
        invoice line.
        @param concept_id: Withholding reason
        """
        # TODO: Change the signature of this method
        # This record already has the concept_id built-in
        #context = self._context or {}
        #ids = isinstance(self.ids, (int)) and [self.ids] or self.ids
        ixwl_obj = self.env['account.wh.islr.xml.line']
        iwdl_obj = self.env['account.wh.islr.doc.line']
        #iwdl_brw = iwdl_obj.browse(iwdl_id)
        residual_ut = 0.0
        subtract_write_ut = 0.0

        ut_date = iwdl_id.islr_wh_doc_id.date_uid
        ut_obj = self.env['account.ut']
        money2ut = ut_obj.compute
        ut2money = ut_obj.compute_ut_to_money

        vendor, buyer, wh_agent = self._get_partners(iwdl_id.invoice_id)
        apply_income = not vendor.islr_exempt
        residence = self._get_residence(vendor, buyer)
        #TODO revisar donde se configura este parametro
        nature = self._get_nature(vendor)
        #nature = False

        concept_id = iwdl_id.concept_id.id

        base = 0
        wh_concept = 0.0


        # Using a clousure to make this call shorter
        f_xc = ut_obj.sxc(
            iwdl_id.invoice_id.currency_id.id,
            iwdl_id.invoice_id.company_id.currency_id.id,
            iwdl_id.invoice_id.date)
        #PROVEEDORES
        if iwdl_id.invoice_id.move_type in ('in_invoice', 'in_refund'):
            for line in iwdl_id.xml_ids:
                if iwdl_id.invoice_id.currency_id == iwdl_id.invoice_id.company_id.currency_id:
                    base += f_xc(line.account_invoice_line_id.price_subtotal)
                else:
                    module_dual_currency = self.env['ir.module.module'].sudo().search(
                        [('name', '=', 'account_dual_currency'), ('state', '=', 'installed')])
                    if module_dual_currency:
                        base += (line.account_invoice_line_id.price_subtotal) * iwdl_id.invoice_id.tax_today
                    else:
                        base += f_xc(line.account_invoice_line_id.price_subtotal)
            rate_tuple = self._get_rate(concept_id, residence, nature, base=base,
                inv_brw=iwdl_id.invoice_id)

            if rate_tuple[7]:
                apply_income = True
                residual_ut = (
                    (rate_tuple[0] / 100.0) * (rate_tuple[2] / 100.0) *
                    rate_tuple[7]['cumulative_base_ut'])
                residual_ut -= rate_tuple[7]['cumulative_tax_ut']
                residual_ut -= rate_tuple[7]['subtrahend']
            else:
                apply_income = (apply_income and
                                base >= rate_tuple[0] * rate_tuple[1] / 100.0)
            wh = 0.0
            subtract = apply_income and rate_tuple[1] or 0.0
            subtract_write = 0.0
            sb_concept = subtract
            for line in iwdl_id.xml_ids:
                if iwdl_id.invoice_id.currency_id == iwdl_id.invoice_id.company_id.currency_id:
                    base_line = f_xc(line.account_invoice_line_id.price_subtotal)
                else:
                    module_dual_currency = self.env['ir.module.module'].sudo().search(
                        [('name', '=', 'account_dual_currency'), ('state', '=', 'installed')])
                    if module_dual_currency:
                        base_line = (line.account_invoice_line_id.price_subtotal) * iwdl_id.invoice_id.tax_today
                    else:
                        base_line = f_xc(line.account_invoice_line_id.price_subtotal)
                base_line_ut = money2ut(base_line, ut_date)
                values = {}
                if apply_income and not rate_tuple[7]:
                    wh_calc = ((rate_tuple[0] / 100.0) *
                               (rate_tuple[2] / 100.0) * base_line)
                    if subtract >= wh_calc:
                        wh = 0.0
                        subtract -= wh_calc
                    else:
                        wh = wh_calc - subtract
                        subtract_write = subtract
                        subtract = 0.0
                    values = {
                        'wh': wh,
                        'raw_tax_ut': money2ut(wh, ut_date),
                        'sustract': subtract or subtract_write,
                    }
                elif apply_income and rate_tuple[7]:
                    tax_line_ut = (base_line_ut * (rate_tuple[0] / 100.0) *
                                   (rate_tuple[2] / 100.0))
                    if residual_ut >= tax_line_ut:
                        wh_ut = 0.0
                        residual_ut -= tax_line_ut
                    else:
                        wh_ut = tax_line_ut + residual_ut
                        subtract_write_ut = residual_ut
                        residual_ut = 0.0
                    wh = ut2money(wh_ut, ut_date)
                    values = {
                        'wh': wh,
                        'raw_tax_ut': wh_ut,
                        'sustract': ut2money(
                            residual_ut or subtract_write_ut,
                            ut_date),
                    }
                type_person = ''
                if nature == False and residence == True:
                    type_person = 'PJDO'
                elif nature == False and residence == False:
                    type_person = 'PJND'
                if nature == True and residence == True:
                    type_person = 'PNRE'
                if nature == True and residence == False:
                    type_person = 'PNNR'
                name_rates = self.env['account.wh.islr.rates'].write({
                                                        'name': type_person
                                                         })
                values.update({
                    'base': base_line * (rate_tuple[0] / 100.0),
                    'raw_base_ut': base_line_ut,
                    'rate_id': rate_tuple[5],
                    'porcent_rete': rate_tuple[2],
                    'concept_code': rate_tuple[4],
                })
                #ixwl_obj.write(line.id, values)
                line.write(values)
                wh_concept += wh
        else:   #CLIENTES
            for line in iwdl_id.invoice_id.invoice_line_ids:
                if line.concept_id.id == concept_id:
                    if iwdl_id.invoice_id.currency_id == iwdl_id.invoice_id.company_id.currency_id:
                        base += f_xc(line.price_subtotal)
                    else:
                        module_dual_currency = self.env['ir.module.module'].sudo().search(
                            [('name', '=', 'account_dual_currency'), ('state', '=', 'installed')])
                        if module_dual_currency:
                            base += (line.price_subtotal) * iwdl_id.invoice_id.tax_today
                        else:
                            base += f_xc(line.price_subtotal)

            rate_tuple = self._get_rate(concept_id, residence, nature, base=0.0,
                inv_brw=iwdl_id.invoice_id)

            if rate_tuple[7]:
                apply_income = True
            else:
                apply_income = (apply_income and
                                base >= rate_tuple[0] * rate_tuple[1] / 100.0)
            sb_concept = apply_income and rate_tuple[3] or 0.0
            if apply_income:
                wh_concept = ((rate_tuple[0] / 100.0) *
                              rate_tuple[2] * base / 100.0)
                wh_concept -= sb_concept
        values = {
            'amount': wh_concept,
            'raw_tax_ut': money2ut(wh_concept, ut_date),
            'subtract': sb_concept,
            'base_amount': base * (rate_tuple[0] / 100.0),
            'raw_base_ut': money2ut(base, ut_date),
            'retencion_islr': rate_tuple[2],
            # 'islr_rates_id': rate_tuple[5],
        }
        iwdl_id.write(values)
        return True


    def load_taxes(self, ids):
        """ Load taxes to the current invoice,
        and if already loaded, it recalculates and load.
        """
        #context = self._context or {}
        #ids = isinstance(ids, (int)) and [ids] or ids
        ids = isinstance(ids, (int)) and [ids] or (isinstance(ids, (list)) and ids) or [ids.id]
        ixwl_obj = self.env['account.wh.islr.xml.line']
        iwdl_obj = self.env['account.wh.islr.doc.line']
        ail_obj = self.env['account.move.line']
        ret_line = self.browse(ids)
        lines = []
        xmls = {}

        if not ret_line.invoice_id:
            return True

        concept_list = self._get_concepts(ret_line.invoice_id)

        if ret_line.invoice_id.move_type in ('in_invoice', 'in_refund'):
            # Searching & Unlinking for xml lines from the current invoice
            xml_lines = ixwl_obj.search([(
                'islr_wh_doc_inv_id', '=', ret_line.id)])
            if xml_lines:
                xml_lines.unlink()

            # Creating xml lines from the current invoices again
            ilids = self.env['account.move.line'].search([('move_id','=',ret_line.invoice_id.id)])
            #ail_brws = [
            #    i for i in ilids
            #    if i.concept_id and i.concept_id.withholdable]
            for i in ilids:
                values = self._get_xml_lines(i)
                values.update({'islr_wh_doc_inv_id': ret_line.id, })
                #TODO VALIDACION QUE ESTA DE MAS PORQUE SE ESTA COLOCANDO UN VALOR POR DEFECTO
                if not values.get('invoice_number'):
                    raise UserError("Error en proceso humano \nComplete el número de factura para continuar, sin este número será imposible de calcular la Retencion")
                # Vuelve a crear las lineas
                xml_id = ixwl_obj.create(values)
                # Write back the new xml_id into the account_invoice_line
                ail_vals = {'wh_xml_id': xml_id.id}
                i.write(ail_vals)
                lines.append(xml_id)
                # Keeps a log of the rate & percentage for a concept
                if xmls.get(i.concept_id.id):
                    xmls[i.concept_id.id] += [xml_id.id]
                else:
                    xmls[i.concept_id.id] = [xml_id.id]

            # Searching & Unlinking for concept lines from the current invoice
            iwdl_ids = iwdl_obj.search( [(
                'invoice_id', '=', ret_line.invoice_id.id)])
            if iwdl_ids:
                iwdl_ids.unlink()
                iwdl_ids = []
            # Creating concept lines for the current invoice
            for concept_id in concept_list:
                iwdl_id = iwdl_obj.create(
                     {'islr_wh_doc_id': ret_line.islr_wh_doc_id.id,
                              'concept_id': concept_id,
                              'invoice_id': ret_line.invoice_id.id,
                              'xml_ids': [(6, 0, xmls.get(concept_id, False))],
                              'iwdi_id': ret_line.id})
                self.write({'sustraendo' :self._get_wh( iwdl_id, concept_id,)})
        else:
            # Searching & Unlinking for concept lines from the current
            # withholding
            iwdl_ids = iwdl_obj.search(
               [('iwdi_id', '=', ret_line.id)])
            if iwdl_ids:
                iwdl_ids.unlink()
                iwdl_ids = []

            for concept_id in concept_list:
                iwdl_id = iwdl_obj.create(
                     {
                        'islr_wh_doc_id': ret_line.islr_wh_doc_id.id,
                        'concept_id': concept_id,
                        'invoice_id': ret_line.invoice_id.id},)
                iwdl_ids += iwdl_id
                self.write({'sustraendo': self._get_wh(iwdl_id, concept_id, )})
                iwdl_id.write({'iwdi_id': ids[0]})
            #self.write({'iwdl_ids': [(6, 0, iwdl_ids)]})
        #values = self.get_amount_all()
        #self.write(values)
        return True

    def _get_partners(self, invoice_id):
        """ Is obtained: the seller's id, the buyer's id
        invoice and boolean field that determines whether the buyer is
        retention agent.
        """
        rp_obj = self.env['res.partner']
        inv_part_id = rp_obj._find_accounting_partner(invoice_id.partner_id)
        comp_part_id = rp_obj._find_accounting_partner(invoice_id.company_id.partner_id)
        if invoice_id.move_type in ('in_invoice', 'in_refund'):
            vendor = inv_part_id
            buyer = comp_part_id
        else:
            buyer = inv_part_id
            vendor = comp_part_id
        return (vendor, buyer, buyer.islr_withholding_agent)

    def _get_residence(self,vendor, buyer):
        """It determines whether the tax form buyer address is the same
        that the seller, then in order to obtain the associated rate.
        Returns True if a person is resident. Returns
        False if is not resident.
        """

        vendor_address = self._get_country_fiscal(vendor)
        buyer_address = self._get_country_fiscal(buyer)
        if vendor_address and buyer_address:
            if self.invoice_id.move_type in ('in_invoice', 'in_refund'):
                if (vendor.company_type== 'person' and vendor.people_type_individual == 'pnre') \
                    or (vendor.company_type == 'company' and vendor.people_type_company == 'pjdo'):
                    return True
                elif (vendor.company_type== 'person' and vendor.people_type_individual == 'pnnr') \
                    or (vendor.company_type == 'company' and vendor.people_type_company == 'pjnd') :
                    return False
            else:
                if (buyer.company_type== 'person' and buyer.people_type_individual == 'pnre') \
                    or (buyer.company_type == 'company' and buyer.people_type_company == 'pjdo'):
                    return True
                elif (buyer.company_type== 'person' and buyer.people_type_individual == 'pnnr') \
                    or (buyer.company_type == 'company' and buyer.people_type_company == 'pjnd') :
                    return False
        return False

    def _get_nature(self, partner_id):
        """ It obtained the nature of the seller from VAT, returns
        True if natural person, and False if is legal.
        """
        rp_obj = self.env['res.partner']
        acc_part_id = rp_obj._find_accounting_partner(partner_id)
        # if not acc_part_id.:
        #     raise UserError(
        #         _('Accion Invalida!'),
        #         _("Imposible retención de ingresos, porque el socio '%s' no esta"
        #           " asociado a ningun tipo de persona") % (acc_part_id.name))
        # else:
        if acc_part_id.company_type == 'person' :
            return True
        else:
            return False

    def _get_rate(self,concept_id, residence, nature, base=0.0,
                  inv_brw=None):
        """ Rate is obtained from the concept of retention, provided
        if there is one associated with the specifications:
        The vendor's nature matches a rate.
        The vendor's residence matches a rate.
        """
        context = self._context or {}
        iwdl_obj = self.env['account.wh.islr.doc.line']
        ut_obj = self.env['account.ut']
        iwhd_obj = self.env["account.wh.islr.historical.data"]
        # money2ut = ut_obj.compute
        # ut2money = ut_obj.compute_ut_to_money
        islr_rate_obj = self.env['account.wh.islr.rates']
        islr_rate_args = [('concept_id', '=', concept_id),
                          ('nature', '=', nature),
                          ('residence', '=', residence), ]
        order = 'minimum desc'

        date_ret = inv_brw and inv_brw.islr_wh_doc_id.date_uid or \
            time.strftime('%Y-%m-%d')

        concept_brw = self.env['account.wh.islr.concept'].browse(concept_id)

        # First looking records for ISLR rate1
        rate2 = False
        islr_rate_ids = islr_rate_obj.search(
            islr_rate_args + [('rate2', '=', rate2)], order=order)

        # Now looking for ISLR rate2
        if not islr_rate_ids:
            rate2 = True
            islr_rate_ids = islr_rate_obj.search(
                islr_rate_args + [('rate2', '=', rate2)], order=order)

        msg_nature = nature and 'Natural' or u'Jurídica'
        msg_residence = residence and 'Domiciliada' or 'No Domiciliada'
        msg = _(u'No hay tarifas disponibles para "Persona %s %s" en el concepto: "%s"') % (
            msg_nature, msg_residence, concept_brw.name)
        if not islr_rate_ids:
            raise UserError("Falta la configuración \n %s" %(msg))

        if not rate2:
            ut_obj = self.env['account.ut'].search([], order='id desc', limit=1)
            #rate_brw = islr_rate_obj.browse(islr_rate_ids[0])

            if islr_rate_ids.minimum == 83.33 and islr_rate_ids.name == 'PNRE':
                valor = 0.0034
            else:
                valor = 0
            rate_brw_minimum = float(ut_obj.amount *(islr_rate_ids.minimum + valor)* (islr_rate_ids.wh_perc/100))
            rate_brw_minimum = round(rate_brw_minimum, 2)
            rate_brw_subtract =   float(ut_obj.amount * islr_rate_ids.subtract * (islr_rate_ids.wh_perc/100))
            rate_brw_subtract = round(rate_brw_subtract, 2)
        else:
            rate2 = {
                'cumulative_base_ut': 0.0,
                'cumulative_tax_ut': 0.0,
            }

            ut_obj = self.env['account.ut'].search([], order='id desc', limit=1)
            base_ut = ut_obj
            iwdl_ids = iwdl_obj.search(

                [('partner_id', '=', inv_brw.partner_id.id),
                 ('concept_id', '=', concept_id),
                 ('invoice_id', '!=', inv_brw.id)]) # need to exclude this
                                                    # invoice from computation
                 #('fiscalyear_id', '=',inv_brw.islr_wh_doc_id.fiscalyear_id.id)]

            # Previous amount Tax Unit for this partner in this fiscalyear with
            # this concept
            for iwdl_brw in iwdl_obj.browse(iwdl_ids):
                base_ut += iwdl_brw.raw_base_ut
                rate2['cumulative_base_ut'] += iwdl_brw.raw_base_ut
                rate2['cumulative_tax_ut'] += iwdl_brw.raw_tax_ut
            iwhd_ids = iwhd_obj.search(

                [('partner_id', '=', inv_brw.partner_id.id),
                 ('concept_id', '=', concept_id)])
            for iwhd_brw in iwhd_obj.browse( iwhd_ids):
                base_ut += iwhd_brw.raw_base_ut
                rate2['cumulative_base_ut'] += iwhd_brw.raw_base_ut
                rate2['cumulative_tax_ut'] += iwhd_brw.raw_tax_ut
            found_rate = False
            for rate_brw in islr_rate_obj.browse(
                     islr_rate_ids):

                if rate_brw.minimum > base_ut * rate_brw.base / 100.0:
                    continue
                if islr_rate_ids.minimum == 83.33 and islr_rate_ids.name == 'PNRE':
                    valor = 0.0034
                else:
                    valor = 0
                rate_brw_minimum =  float(ut_obj.amount * (islr_rate_ids.minimum + valor) * (islr_rate_ids.wh_perc/100))
                rate_brw_minimum = round(rate_brw_minimum, 2)
                rate_brw_subtract =  float(ut_obj.amount * islr_rate_ids.subtract * (islr_rate_ids.wh_perc/100))
                rate_brw_subtract = round(rate_brw_subtract, 2)
                found_rate = True
                rate2['subtrahend'] = rate_brw.subtract
                break
            if not found_rate:
                msg += _(' Para unidades impositivas mayores que cero')
                raise UserError(_('Falta la configuración'), msg)
        return (islr_rate_ids.base, rate_brw_minimum, islr_rate_ids.wh_perc,
                rate_brw_subtract, islr_rate_ids.code, islr_rate_ids.id, islr_rate_ids.name,
                rate2) if msg_nature == 'Natural' else (islr_rate_ids.base, 0, islr_rate_ids.wh_perc,
                0, islr_rate_ids.code, islr_rate_ids.id, islr_rate_ids.name,
                rate2)

    def _get_country_fiscal(self, partner_id):
        """ Get the country of the partner
        @param partner_id: partner id whom consult your country
        """
        # TODO: THIS METHOD SHOULD BE IMPROVED
        # DUE TO OPENER HAS CHANGED THE WAY PARTNER
        # ARE USED FOR ACCOUNT_MOVE
        context = self._context or {}
        rp_obj = self.env['res.partner']
        acc_part_id = rp_obj._find_accounting_partner(partner_id)
        if not acc_part_id.country_id:
            raise UserError(
                _('Acción no válida \n Retención de ingresos imposible, porque el socio %s no ha definido el pais en la dirección.' % (acc_part_id.name)))
        else:
            return acc_part_id.country_id.id

    def _get_xml_lines(self, ail_brw):
        """ Extract information from the document to generate xml lines
        @param ail_brw: invoice of the document
        """
        context = self._context or {}
        rp_obj = self.env['res.partner']
        acc_part_id = rp_obj._find_accounting_partner(
            ail_brw.move_id.partner_id)
        vendor, buyer, wh_agent = self._get_partners(
             ail_brw.move_id)
        #TODO VERIFICAR SI EL RIF DEL VENDEDOR (PROVEEDOR) DEBE SER BLIGATORIO PARA GENERAR EL XML
        #if not vendor.vat:
        #    raise UserError(
        #        _('Missing RIF number!!!'),
        #        _('Vendor has not RIF number. This value is required for procesing withholding!!!'))

        #TODO EVALUAR SI ESTOS CAMPOS SON REQUERIDOS EN EL XML
        #self.buyer = buyer
        #self.wh_agent = wh_agent
        document_v = False
        if vendor:
            if vendor.company_type == 'company':
                people_type = vendor.people_type_company
                if people_type == 'pjdo':
                    document_v = vendor.rif.replace("-","")
            elif vendor.company_type == 'person':
                people_type = vendor.people_type_individual
                if vendor.nationality == 'V' or vendor.nationality == 'E':
                    document_v = str(vendor.nationality) + str(vendor.identification_id)
                else:
                    document_v = vendor.identification_id
        if vendor.vat :
            vendor = vendor.vat.replace("-","")
        else:
            vendor = str()
        if not ail_brw.concept_id:
            raise UserError(_('¡La factura no ha retenido conceptos!'))
        return {
            'account_invoice_id': ail_brw.move_id.id,
            'islr_wh_doc_line_id': False,
            'islr_xml_wh_doc': False,
            'wh': 0.0,  # To be updated later
            'base': 0.0,  # To be updated later
              # We review the definition because it is in
                                 # NOT NULL

            'invoice_number': ail_brw.move_id.supplier_invoice_number,

            'partner_id': acc_part_id.id,  # Warning Depends if is a customer
                                           # or supplier
            'concept_id': ail_brw.concept_id.id,
            'partner_vat': document_v[0:12] if document_v else str(),  # Warning Depends if is a
                                              # customer or supplier
            'porcent_rete': 0.0,  # To be updated later

            'control_number': ail_brw.move_id.nro_ctrl,
            'account_invoice_line_id': ail_brw.id,
            'concept_code': '000',# To be updated later
            'type': 'invoice'
        }
