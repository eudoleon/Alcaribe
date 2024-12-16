# -*- coding: UTF-8 -*-
from email.policy import default

from odoo import fields, models, api
from odoo.exceptions import UserError
from odoo.addons import decimal_precision as dp
import re

class ResPartner(models.Model):

    _inherit = 'res.partner'

    nationality = fields.Selection([
        ('V', 'Venezolano'),
        ('E', 'Extranjero'),
        ('P', 'Pasaporte')], string="Tipo Documento", default='V')
    identification_id = fields.Char(string='Documento de Identidad')
    value_parent = fields.Boolean(string='Valor parent_id', compute='compute_value_parent_id')
    people_type_individual = fields.Selection([
        ('pnre', 'PNRE Persona Natural Residente'),
        ('pnnr', 'PNNR Persona Natural No Residente')
    ], string='Tipo de Persona individual', default='pnre')
    people_type_company = fields.Selection([
        ('pjdo', 'PJDO Persona Jurídica Domiciliada'),
        ('pjnd', 'PJND Persona Jurídica No Domiciliada')], string='Tipo de Persona compañía', default='pjdo')
    rif = fields.Char(string='RIF')

    wh_iva_agent = fields.Boolean(
        '¿Es Agente de Retención (IVA)?',
        help="Indique si el socio es un agente de retención de IVA", default=True)

    wh_iva_rate = fields.Float(
        string='% Retención de IVA',
        help="Se coloca el porcentaje de la Tasa de retención de IVA", dafault=75.0)

    vat_subjected = fields.Boolean('Declaración legal de IVA',
    help="Marque esta casilla si el socio está sujeto al IVA. Se utilizará para la declaración legal del IVA.", default=True)

    purchase_journal_id = fields.Many2one('account.journal','Diario de Compra para IVA', company_dependent=True,
                                        domain="[('is_iva_journal','=', True), ('company_id', '=', current_company_id)]")
    purchase_sales_id = fields.Many2one('account.journal', 'Diario de Venta para IVA', company_dependent=True,
                                        domain="[('is_iva_journal','=', True), ('company_id', '=', current_company_id)]")

    parish_id = fields.Many2one('res.country.state.municipality.parish', 'Parish')
    @api.model
    def _address_fields(self):
        address_fields = set(super(ResPartner, self)._address_fields())
        address_fields.add('parish_id')
        return list(address_fields)

    ## ISLR #######################
    islr_withholding_agent = fields.Boolean(
        '¿Agente de retención de ingresos?', default=True,
        help="Verifique si el partner es un agente de retención de ingresos")
    spn = fields.Boolean(
        '¿Es una sociedad de personas físicas?',
        help='Indica si se refiere a una sociedad de personas físicas.')
    islr_exempt = fields.Boolean(
        '¿Está exento de retención de ingresos?',
        help='Si el individuo está exento de retención de ingresos')
    purchase_islr_journal_id = fields.Many2one('account.journal', 'Diario de Compra para ISLR', company_dependent=True,
                                        domain="[('is_islr_journal','=', True), ('company_id', '=', current_company_id)]")
    sale_islr_journal_id = fields.Many2one('account.journal', 'Diario de Venta para ISLR', company_dependent=True,
                                        domain="[('is_islr_journal','=', True), ('company_id', '=', current_company_id)]")

    same_vat_partner_id = fields.Many2one('res.partner', string='Contacto con el mismo RIF',
                                          compute='_compute_same_rif_partner_id', store=False)

    contribuyente_seniat = fields.Selection([
        ('ordinario', 'Ordinario'),
        ('especial', 'Especial'),
        ('formal', 'Formal'),
        ('gobernamental', 'Gubernamental')], string="Contribuyente", default='ordinario')

    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict', default=lambda self: self.env.company.country_id.id)
    
    @api.model_create_multi
    def create(self, vals):
        print('vals', vals)
        if vals[0].get('vat'):
            if vals[0].get('company_type'):
                if vals[0].get('company_type') == 'person':
                    vals[0]['identification_id'] = vals[0]['vat']
                else:
                    vals[0]['rif'] = vals[0]['vat']
            else:
                vals[0]['identification_id'] = vals[0]['vat']
        if vals[0].get('identification_id') and vals[0].get('nationality'):
            valor = vals[0].get('identification_id')
            nationality = vals[0].get('nationality')
            self.validation_document_ident(valor, nationality)
        if vals[0].get('identification_id'):
            if not self.validate_ci_duplicate(vals[0].get('identification_id', False), True):
                raise UserError('El cliente o proveedor ya se encuentra registrado con el Documento: %s'
                                % (vals[0].get('identification_id', False)))
        res = super(ResPartner, self).create(vals)

        if vals[0].get('rif'):
            if res.country_id:
                if res.country_id.code == 'VE':
                    if not self.validate_rif_er(vals[0].get('rif')):
                        raise UserError('El rif tiene el formato incorrecto. Ej: V-01234567-8, E-01234567-8, J-01234567-8 o G-01234567-8. Por favor verifique el formato y si posee los 12 caracteres como se indica en el Ej. e intente de nuevo')
                    if self.validate_rif_duplicate(vals[0].get('rif'), res):
                        raise UserError('El cliente o proveedor ya se encuentra registrado con el rif: %s y se encuentra activo'
                                        % (vals[0].get('rif')))
            res['vat'] = vals[0].get('rif')
        if vals[0].get('email'):
            if not self.validate_email_addrs(vals[0].get('email'), 'email'):
                raise UserError('El email es incorrecto. Ej: cuenta@dominio.xxx. Por favor intente de nuevo')

        return res

    @api.depends('rif', 'company_id')
    def _compute_same_rif_partner_id(self):
        for partner in self:
            # use _origin to deal with onchange()
            partner_id = partner._origin.id
            # active_test = False because if a partner has been deactivated you still want to raise the error,
            # so that you can reactivate it instead of creating a new one, which would loose its history.
            Partner = self.with_context(active_test=False).sudo()
            domain = [
                ('rif', '=', partner.rif),
                ('company_id', 'in', [False, partner.company_id.id]),
            ]
            if partner_id:
                domain += [('id', '!=', partner_id), '!', ('id', 'child_of', partner_id)]
            partner.same_vat_partner_id = bool(partner.rif) and not partner.parent_id and Partner.search(domain,
                                                                                                         limit=1)

    # def write(self, vals):
    #     res = super(ResPartner, self).write(vals)
    #
    #     if vals.get('identification_id') and not vals.get('nationality'):
    #         valor = vals.get('identification_id')
    #         nationality = self.nationality
    #         self.validation_document_ident(valor, nationality)
    #     if vals.get('identification_id') and vals.get('nationality'):
    #         valor = vals.get('identification_id')
    #         nationality = vals.get('nationality')
    #         self.validation_document_ident(valor, nationality)
    #     if vals.get('nationality') and not vals.get('identification_id'):
    #         valor = self.identification_id
    #         nationality = vals.get('nationality')
    #         self.validation_document_ident(valor, nationality)
    #     if not self.validate_ci_duplicate(vals.get('identification_id', False)):
    #         raise UserError('El cliente o proveedor ya se encuentra registrado con el Documento: %s'
    #                         % (vals.get('identification_id', False)))
    #
    #     if self.rif:
    #         vals['rif'] = self.rif.upper()
    #         if self.country_id:
    #             if self.country_id.code == 'VE':
    #                 if not self.validate_rif_er(self.rif):
    #                     raise UserError(
    #                         'El rif tiene el formato incorrecto. Ej: V-01234567-8, E-01234567-8, J-01234567-8 o G-01234567-8. Por favor verifique el formato y si posee los 12 caracteres como se indica en el Ej. e intente de nuevo')
    #         vals['vat'] = self.rif
    #
    #     if vals.get('email'):
    #         if not self.validate_email_addrs(vals.get('email'), 'email'):
    #             raise UserError('El email es incorrecto. Ej: cuenta@dominio.xxx. Por favor intente de nuevo')
    #
    #
    #
    #     if vals.get('rif'):
    #         if self.country_id:
    #             if self.country_id.code == 'VE':
    #                 if self.validate_rif_duplicate(vals.get('rif'), res):
    #                     raise UserError('El cliente o proveedor ya se encuentra registrado con el rif: %s y se encuentra activo'
    #                             % (vals.get('rif')))
    #
    #     return res

    @api.constrains('vat', 'vat_type', 'country_id')
    def check_vat(self):
        for rec in self:
            if rec.country_id:
                if rec.country_id.code == 'VE':
                    return
                else:
                    return super().check_vat()

    @api.onchange('rif')
    def _onchange_rif(self):
        for rec in self:
            if rec.rif:
                rec.vat = rec.rif.upper()
            else:
                rec.vat = ''

    @api.depends('company_type')
    def compute_value_parent_id(self):
        for rec in self:
            rec.value_parent = rec.parent_id.active

    @staticmethod
    def validation_document_ident(valor, nationality):
        if valor:
            if nationality == 'V' or nationality == 'E':
                if len(valor) == 7 or len(valor) == 8:
                    if not valor.isdigit():
                        raise UserError(
                            'La Cédula solo debe ser Numerico. Por favor corregir para proceder a Crear/Editar el registro')
                    return
                else:
                    raise UserError('La Cedula de Identidad no puede ser menor que 7 cifras ni mayor a 8.')
            if nationality == 'P':
                if (len(valor) > 20) or (len(valor) < 10):
                    raise UserError('El Pasaporte no puede ser menor que 10 cifras ni mayor a 20.')
                return

    def validate_ci_duplicate(self, valor, create=False):
        found = True
        partner_2 = self.search([('identification_id', '=', valor)])
        for cus_supp in partner_2:
            if create:
                if cus_supp and (cus_supp.customer_rank or cus_supp.supplier_rank):
                    found = False
                elif cus_supp and (cus_supp.customer_rank or cus_supp.supplier_rank):
                    found = False
        return found

    @api.onchange('company_type')
    def change_country_id_partner(self):
        if self.company_type and self.company_type == 'person':
            self.country_id = 238
        elif self.company_type == 'company':
            self.country_id = False

    @staticmethod
    def validate_rif_er(field_value):
        res = {}
        rif_obj = re.compile(r"[VEJGC]{1}[-]{1}[0-9]{9}[-]{1}[0-9]{1}", re.X)
        rif_obj_2 = re.compile(r"[VEJGC]{1}[-]{1}[0-9]{8}[-]{1}[0-9]{1}", re.X)
        if rif_obj.search(field_value.upper()) or rif_obj_2.search(field_value.upper()):
            res = {
                'rif': field_value
            }
        return res

    def validate_rif_duplicate(self, valor, res):
        if self:
            aux_ids = self.ids
            aux_item = self
        else:
            aux_ids = res.ids
            aux_item = res
        for _ in aux_item:
            partner = self.env['res.partner'].search([('rif', '=', valor), ('id', 'not in', aux_ids)])
            if partner:
                return True
            else:
                return False

    @staticmethod
    def validate_email_addrs(email, field):
        res = {}
        mail_obj = re.compile(r"""
                    \b             # comienzo de delimitador de palabra
                    [\w.%+-]       # usuario: Cualquier caracter alfanumerico mas los signos (.%+-)
                    +@             # seguido de @
                    [\w.-]         # dominio: Cualquier caracter alfanumerico mas los signos (.-)
                    +\.            # seguido de .
                    [a-zA-Z]{2,3}  # dominio de alto nivel: 2 a 6 letras en minúsculas o mayúsculas.
                    \b             # fin de delimitador de palabra
                    """, re.X)  # bandera de compilacion X: habilita la modo verborrágico, el cual permite organizar
        # el patrón de búsqueda de una forma que sea más sencilla de entender y leer.
        if mail_obj.search(email):
            res = {
                field: email
            }
        return res



from odoo import fields, models


class CountryState(models.Model):
    _name = 'res.country.state'
    _inherit = 'res.country.state'
    _description = "Country states"

    municipality_ids = fields.One2many('res.city', 'state_id',
                                       string='Municipalities in this state')
    ubigeo = fields.Char(string='ubigeo code', size=2)


class StateMunicipality(models.Model):
    _inherit = 'res.city'
    _description = "State municipalities"

    state_id = fields.Many2one('res.country.state', string='State', required=True,
                               help='Name of the State to which the municipality belongs')
    name = fields.Char('Municipality', required=True, help='Municipality name')
    parish_ids = fields.One2many('res.country.state.municipality.parish', 'municipality_id',
                                 string='Parishes in this municipality')
    ubigeo = fields.Char(string='ubigeo code', size=4)
    code = fields.Char(string='ubigeo code')

class MunicipalityParish(models.Model):
    _name = 'res.country.state.municipality.parish'
    _description = "Municipality parishes"

    municipality_id = fields.Many2one('res.city', string='Municipality',
                                      help='Name of the Municipality to which the parish belongs')
    name = fields.Char('Parish', required=True, help='Parish name')
    ubigeo = fields.Char(string='ubigeo code', size=6)
    