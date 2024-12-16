# -*- coding: utf-8 -*-
# Copyright 2019 NMKSoftware
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from pytz import country_names
from odoo import SUPERUSER_ID, api, fields, models, _, exceptions
from odoo.exceptions import ValidationError, except_orm, Warning, RedirectWarning
import re
import logging
_logger = logging.getLogger(__name__)



class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _get_available_regime(self):
        return [
            ('48', '48 - Responsable del impuesto sobre las ventas - IVA'),
            ('49', '49 - No responsable del IVA'),
        ]

    first_names = fields.Char(
        string="First Name",
    )
    middle_name = fields.Char(
        string="Middle Name",
    )
    last_name = fields.Char(
        string="Last Name",
    )
    second_last_name = fields.Char(
        string="Second Last Name",
    )
    vat_co = fields.Char(
        string="Numero RUT/NIT/CC",
    )
    vat_ref = fields.Char(
        string="NIT Formateado",
        compute="_compute_vat_ref",
        readonly=True,
    )
    vat_type = fields.Selection(
        string=u'Tipo de Documento',
        selection=[
            ('11', u'11 - Registro civil de nacimiento'),
            ('12', u'12 - Tarjeta de identidad'),
            ('13', u'13 - Cédula de ciudadanía'),
            ('21', u'21 - Tarjeta de extranjería'),
            ('22', u'22 - Cédula de extranjería'),
            ('31', u'31 - NIT/RUT'),
            ('41', u'41 - Pasaporte'),
            ('42', u'42 - Documento de identificación extranjero'),
            ('47', u'47 - PEP'),
            ('50', u'50 - NIT de otro pais'),
            ('91', u'91 - NUIP'),
        ],
        help = u'Identificacion del Cliente, segun los tipos definidos por la DIAN.',
    )
    vat_vd = fields.Char(
        string=u"Digito Verificación", size=1, tracking=True
    )
    ciiu_id = fields.Many2one(
        string='Actividad CIIU',
        comodel_name='res.ciiu',
        domain=[('type', '!=', 'view')],
        help=u'Código industrial internacional uniforme (CIIU)'
    )

    taxes_ids = fields.Many2many(
        string="Customer taxes",
        comodel_name="account.tax",
        relation="partner_tax_sale_rel",
        column1="partner_id",
        column2="tax_id",
        domain="[('type_tax_use','=','sale')]",
        help="Taxes applied for sale.",
    )
    supplier_taxes_ids =  fields.Many2many(
        string="Supplier taxes",
        comodel_name="account.tax",
        relation="partner_tax_purchase_rel",
        column1="partner_id",
        column2="tax_id",
        domain="[('type_tax_use','=','purchase')]",
        help="Taxes applied for purchase.",
    )
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict', default=lambda self: self.env.company.country_id.id)
    regime_type = fields.Selection(_get_available_regime, string="Regimen", default="48")
    anonymous_customer = fields.Boolean(string="Anonymous customer")

    _sql_constraints = [
        ('unique_vat','UNIQUE(vat_co,company_id)', 'VAT alreaedy exist')
    ]

    
    @api.onchange('vat','vat_co','vat_ref')
    def onchange_vat(self):
        if self.vat_co:
            self.vat = self.vat_co or self.vat_ref
    
    @api.onchange("l10n_latam_identification_type_id")
    def onchange_document_type(self):
        if self.l10n_latam_identification_type_id.l10n_co_document_code == 'rut':
            self.vat_type = '31'
        elif self.l10n_latam_identification_type_id.l10n_co_document_code == 'id_document':
            self.vat_type = '13'
        elif self.l10n_latam_identification_type_id.l10n_co_document_code == 'id_card':
            self.vat_type = '12'
        elif self.l10n_latam_identification_type_id.l10n_co_document_code == 'passport':
            self.vat_type = '41'
        elif self.l10n_latam_identification_type_id.l10n_co_document_code == 'foreign_id_card':
            self.vat_type = '22'
        elif self.l10n_latam_identification_type_id.l10n_co_document_code == 'external_id':
            self.vat_type = '42'
        elif self.l10n_latam_identification_type_id.l10n_co_document_code == 'diplomatic_card':
            self.vat_type = '42'
        elif self.l10n_latam_identification_type_id.l10n_co_document_code == 'residence_document':
            self.vat_type = '42'
        elif self.l10n_latam_identification_type_id.l10n_co_document_code == 'civil_registration':
            self.vat_type = '11'
        elif self.l10n_latam_identification_type_id.l10n_co_document_code == 'national_citizen_id':
            self.vat_type = '13'


    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        if name:
            args = ['|','|',('vat_co', 'ilike', name + '%'),('name', 'ilike', name),('display_name', 'ilike', name)] + args

        return self._search(args, limit=limit, access_rights_uid=name_get_uid)

    def _display_address(self, without_company=False):

        address_format = self.country_id.address_format or \
            self._get_default_address_format()
        args = {
            'state_code': self.state_id.code or '',
            'state_name': self.state_id.name or '',
            'country_code': self.country_id.code or '',
            'country_name': self.country_id.name or '',
            'company_name': self.commercial_company_name or '',
            'city_name': self.city_id and self.city_id.display_name or '',
        }
        for field in self._address_fields():
            args[field] = getattr(self, field) or ''
        if without_company:
            args['company_name'] = ''
        elif self.commercial_company_name:
            address_format = '%(company_name)s\n' + address_format

        if self.vat_type in ['31','13','22']:
            id_type = {}
            id_type['31'] = 'NIT'
            id_type['13'] = 'CC'
            id_type['22'] = 'CE'
            id_id = id_type[self.vat_type]
        else:
            id_id = 'ID'

        res = address_format % args
        
        if self.vat_ref:
            res = "%s:%s\n%s" % (id_id, self.vat_ref, res)
        else:
            res = "%s:%s\n%s" % (id_id, self.vat_co, res)

        return res

        
    def _address_fields(self):
        result = super(ResPartner, self)._address_fields()
        result = result + ['city_id']
        return result


    def _compute_vat_ref(self):
        """
        Compute vat_ref field
        """
        for partner in self:
            result_vat = None
            if partner.vat_type == '31' and partner.vat_co and partner.vat_co.isdigit() and len(partner.vat_co.strip()) > 0:
                #result_vat = '{:,}'.format(int(partner.vat_co.strip())).replace(",", ".")
                partner.vat_ref = "%s" % (partner.vat)
            else:
                partner.vat_ref = partner.vat_co
    @api.onchange('vat_co','city_id','l10n_latam_identification_type_id')
    def _compute_concat_nit(self):
        """
        Concatenating and formatting the NIT number in order to have it
        consistent everywhere where it is needed
        @return: void
        """
        # Executing only for Document Type 31 (NIT)
        for partner in self:

            # _logger.info('document')
            # _logger.info(partner.l10n_latam_identification_type_id.name)
            if partner.l10n_latam_identification_type_id.name == 'NIT':
                # First check if entered value is valid
                #_logger.info('if')
                # self._check_ident()
                #self._check_ident_num()

                # Instead of showing "False" we put en empty string
                if partner.vat_co == False:
                    partner.vat_co = ''
                else:
                    #_logger.info('else')
                    partner.vat_vd = ''

                    # Formatting the NIT: xx.xxx.xxx-x
                    s = str(partner.vat_co)[::-1]
                    newnit = '.'.join(s[i:i + 3] for i in range(0, len(s), 3))
                    newnit = newnit[::-1]

                    nitList = [
                        newnit,
                        # Calling the NIT Function
                        # which creates the Verification Code:
                        self._check_dv(str(partner.vat_co).replace('-', '',).replace('.', '',))
                    ]

                    formatedNitList = []

                    for item in nitList:
                        if item != '':
                            formatedNitList.append(item)
                            partner.vat_vd = '-'.join(formatedNitList)

                    # Saving Verification digit in a proper field
                    for pnitem in self:
                        #_logger.info(nitList[1])
                        #_logger.info('nitlist')
                        pnitem.vat_vd = nitList[1]

    def _check_dv(self, nit):
        """
        Function to calculate the check digit (DV) of the NIT. So there is no
        need to type it manually.
        @param nit: Enter the NIT number without check digit
        @return: String
        """
        for item in self:
            if item.l10n_latam_identification_type_id.name != 'NIT':
                return str(nit)

            nitString = '0'*(15-len(nit)) + nit
            vl = list(nitString)
            result = (
                int(vl[0])*71 + int(vl[1])*67 + int(vl[2])*59 + int(vl[3])*53 +
                int(vl[4])*47 + int(vl[5])*43 + int(vl[6])*41 + int(vl[7])*37 +
                int(vl[8])*29 + int(vl[9])*23 + int(vl[10])*19 + int(vl[11])*17 +
                int(vl[12])*13 + int(vl[13])*7 + int(vl[14])*3
            ) % 11

            if result in (0, 1):
                return str(result)
            else:
                return str(11-result)


    # @api.onchange('vat_co')
    # def _check_ident(self):
    #     """
    #     This function checks the number length in the Identification field.
    #     Min 6, Max 12 digits.
    #     @return: void
    #     """
    #     for item in self:
    #         if item.l10n_latam_identification_type_id.name != 1:
    #             msg = _('Error! Number of digits in Identification number must be'
    #                     'between 2 and 12')
    #             if len(str(item.vat_co)) < 2:
    #                 raise exceptions.ValidationError(msg)
    #             elif len(str(item.vat_co)) > 12:
    #                 raise exceptions.ValidationError(msg)

    # @api.constrains('vat_co')
    # def _check_ident_num(self):
    #     """
    #     This function checks the content of the identification fields: Type of
    #     document and number cannot be empty.
    #     There are two document types that permit letters in the identification
    #     field: 21 and 41. The rest does not permit any letters
    #     @return: void
    #     """
    #     for item in self:
    #         if item.l10n_latam_identification_type_id.name != "Cédula de ciudadanía":
    #             if item.vat_co is not False and \
    #                             item.l10n_latam_identification_type_id.name != "Cédula de extranjería" and \
    #                             item.l10n_latam_identification_type_id.name != "Nit de otro país":
    #                 if re.match("^[0-9]+$", item.vat_co) is None:
    #                     msg = _('Error! Identification number can only '
    #                             'have numbers')
    #                     raise exceptions.ValidationError(msg)



    @api.onchange('country_id', 'vat_co', 'vat_vd', 'l10n_latam_identification_type_id')
    def _onchange_vat(self):
        if self.country_id and self.vat_co:
            if self.country_id.code:
                if self.vat_vd and self.l10n_latam_identification_type_id.l10n_co_document_code == 'rut':
                    self.vat = self.vat_co + "-" + self.vat_vd
                elif self.l10n_latam_identification_type_id.l10n_co_document_code  == 'foreign_id_card':
                    self.vat_vd = False
                    self.vat = self.vat_co 
                else:
                    self.vat_vd = False
                    self.vat = self.vat_co 
            else:
                msg = _('The Country has No ISO Code.')
                raise ValidationError(msg)
        elif not self.vat_co and self.vat:
            self.vat = False

    @api.constrains('vat', 'l10n_latam_identification_type_id', 'country_id')
    def check_vat(self):
        def _checking_required(partner):
            '''
            Este método solo aplica para Colombia y obliga a seleccionar
            un tipo de documento de identidad con el fin de determinar
            si es verificable por el algoritmo VAT. Si no se define,
            de todas formas el VAT se evalua como un NIT.
            '''
            return ((partner.l10n_latam_identification_type_id and \
                partner.l10n_latam_identification_type_id) or \
                not partner.l10n_latam_identification_type_id) == True

        msg = _('The Identification Document does not seems to be correct.')

        for partner in self:
            if not partner.vat:
                continue

            vat_country, vat_number = self._split_vat(partner.vat)

            if partner.l10n_latam_identification_type_id.name == 'Nit de otro país':
                vat_country = 'co'
            elif partner.country_id:
                vat_country = partner.country_id.code.lower()

            if not hasattr(self, 'check_vat_' + vat_country):
                continue

            #check = getattr(self, 'check_vat_' + vat_country)

            if vat_country == 'co':
                if not _checking_required(partner):
                    continue

            #if check and not check(vat_number):
            #   raise ValidationError(msg)

        return True

    # def check_vat_co(self, vat):
    #     '''
    #     Check VAT Routine for Colombia.
    #     '''
    #     # if type(vat) == str:
    #     #     vat = vat.replace('-', '', 1).replace('.', '', 2)

    #     if len(str(vat)) < 4:
    #         return False

    #     try:
    #         int(vat)
    #     except ValueError:
    #         return False

    #     # Validación Sin identificación del exterior
    #     # o para uso definido por la DIAN
    #     if len(str(vat)) == 9 and str(vat)[0:5] == '44444' \
    #         and int(str(vat)[5:]) <= 9000 \
    #         and int(str(vat)[5:]) >= 4001:

    #         return True

    #     prime = [3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71]
    #     sum = 0
    #     vat_len = len(str(vat))

    #     for i in range(vat_len - 2, -1, -1):
    #         sum += int(str(vat)[i]) * prime[vat_len - 2 - i]

    #     if sum % 11 > 1:
    #         return str(vat)[vat_len - 1] == str(11 - (sum % 11))
    #     else:
    #         return str(vat)[vat_len - 1] == str(sum % 11)


    @api.constrains("vat_co", "vat_type")
    def check_vat(self):
        """
        Check vat_co field
        """
        for partner in self:
            if partner.vat_co:
                if not re.match(r'^\d+$', partner.vat_co) and partner.vat_type in ['31', '13']:
                    raise ValidationError(_('The vat_co number must be only numbers, there are characters invalid like letters or empty space'))

                partner.vat_co.strip()
                #partner.check_unique_constraint()

    # @api.onchange("vat_type", "vat_co", "vat_vd", )
    # def _onchange_vat_vd(self):
    #     self.ensure_one()
    #     if self.vat_type == '31' and self.vat_co and self.vat_vd:

    #         return {
    #             'warning': {
    #                 'title': _('Warning'),
    #                 'message': u'NIT/RUT [%s - %i] suministrado para "%s" no supera la prueba del dígito de verificacion, el valor calculado es %s!' %
    #                               (self.vat_co, self.vat_vd, self.name, self.compute_vat_vd(self.vat_co))
            #     }
            # }

    # def check_vat_co(self):
    #     """
    #     Check vat_co field
    #     """
    #     self.ensure_one()
    #     vat_vd = self.vat_vd
    #     computed_vat_vd = self.compute_vat_vd(self.vat_co)
    #     if int(vat_vd) != int(computed_vat_vd):
    #         return False
    #     return True


    @api.onchange('first_names', 'middle_name', 'last_name', 'second_last_name')
    def _onchange_person_names(self):
        if self.company_type == 'person':
            names = [name for name in [self.first_names, self.middle_name, self.last_name, self.second_last_name] if name]
            self.name = u' '.join(names)

    @api.depends('company_type', 'name', 'first_names', 'middle_name', 'last_name', 'second_last_name')
    def copy(self, default=None):
        default = default or {}
        if self.company_type == 'person':
            default.update({
                'first_names': self.first_names and self.first_names + _('(copy)') or '',
                'middle_name': self.middle_name and self.middle_name + _('(copy)') or '',
                'last_name': self.last_name and self.last_name + _('(copy)') or '',
                'second_last_name': self.second_last_name and self.second_last_name + _('(copy)') or '',
            })
        return super(ResPartner, self).copy(default=default)

    # @api.constrains("vat")
    # def check_unique_constraint(self):
    #     partner_ids = self.search([
    #         ('vat','=', self.vat),
    #         ('vat_type','=', self.vat_type),
    #         #('parent_id','=',False),
    #     ])
    #     partner_ids = partner_ids - self
        
    #     if len(partner_ids) > 0 and not self.parent_id:
    #         raise ValidationError(_("VAT %s is already registered for the contact %s") % (self.vat, ';'.join([partner_id.display_name for partner_id in partner_ids])))

    def person_name(self, vals):
        values = vals or {}
        person_field = ['first_names', 'middle_name', 'last_name', 'second_last_name']
        person_names = set(person_field)
        values_keys = set(values.keys())

        if person_names.intersection(values_keys):
            names = []
            for x in person_field:
                if x in values.keys():
                    names += [values.get(x, False) and values.get(x).strip() or '']
                else:
                    names += [self[x] or '']
            name = ' '.join(names)
            if name.strip():
                values.update({
                    'name': name,
                })

        if values.get('name', False):
            values.update({
                'name': values.get('name').strip(),
            })

        return values

    def write(self, values):
        values = self.person_name(values)
        return super(ResPartner, self).write(values)

    @api.model
    def create(self, values):
        values = self.person_name(values)
        return super(ResPartner, self).create(values)
