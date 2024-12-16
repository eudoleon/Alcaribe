from odoo import api, fields, models, _
from datetime import date, timedelta, datetime
from bs4 import BeautifulSoup
import requests
import urllib3
urllib3.disable_warnings()
class ResCurrency(models.Model):
    _inherit = 'res.currency'

    facturas_por_actualizar = fields.Boolean(compute="_facturas_por_actualizar")

    # habilitar sincronización automatica
    sincronizar = fields.Boolean(string="Sincronizar", default=False)

    # campo listado de servidores, bcv o dolar today
    server = fields.Selection([('bcv', 'BCV'), ('dolar_today', 'Dolar Today Promedio')], string='Servidor',
                              default='bcv')

    act_productos = fields.Boolean(string="Actualizar Productos", default=False)

    def _convert(self, from_amount, to_currency, company, date, round=True):
        """Returns the converted amount of ``from_amount``` from the currency
           ``self`` to the currency ``to_currency`` for the given ``date`` and
           company.

           :param company: The company from which we retrieve the convertion rate
           :param date: The nearest date from which we retriev the conversion rate.
           :param round: Round the result or not
        """
        self, to_currency = self or to_currency, to_currency or self
        assert self, "convert amount from unknown currency"
        assert to_currency, "convert amount to unknown currency"
        assert company, "convert amount from unknown company"
        assert date, "convert amount from unknown date"
        # apply conversion rate
        if self == to_currency:
            to_amount = from_amount
        else:
            if self.env.context.get('tasa_factura'):
                if to_currency == self.env.company.currency_id_dif:
                    to_amount = from_amount / self.env.context.get('tasa_factura')
                else:
                    to_amount = from_amount * self.env.context.get('tasa_factura')
            else:
                to_amount = from_amount * self._get_conversion_rate(self, to_currency, company, date)
        # apply rounding
        #print("from_amount", from_amount)
        #print("to_amount", to_amount)
        return to_currency.round(to_amount) if round else to_amount

    def _facturas_por_actualizar(self):
        for rec in self:
            if rec.name == self.env.company.currency_id_dif.name:
                if self.env['account.move'].search_count([('state', 'in', ['draft','posted'])]):
                    rec.facturas_por_actualizar = True
                else:
                    rec.facturas_por_actualizar = False
            else:
                rec.facturas_por_actualizar = False


    def actualizar_facturas(self):
        for rec in self:
            # actualizar tasa a las facturas dinamicas
            facturas = self.env['account.move'].search([('acuerdo_moneda', '=', True)])
            if facturas:
                for f in facturas:
                    f.tax_today = rec.inverse_rate
                    for l in f.line_ids:
                        l.tax_today = rec.inverse_rate
                        l._debit_usd()
                        l._credit_usd()
                    for d in f.invoice_line_ids:
                        d.tax_today = rec.inverse_rate
                        d._price_unit_usd()
                        d._price_subtotal_usd()
                    #f._amount_untaxed_usd()
                    f._amount_all_usd()
                    f._compute_payments_widget_reconciled_info_USD()

    def actualizar_productos(self):
        for rec in self:
            product_ids = self.env['product.template'].search([('list_price_usd','>',0)])
            for p in product_ids:
                p.list_price = p.list_price_usd * rec.inverse_rate

            product_product_ids = self.env['product.product'].search([('list_price_usd', '>', 0)])
            for p in product_product_ids:
                p.list_price = p.list_price_usd * rec.inverse_rate

            list_product_ids = self.env['product.pricelist.item'].search([('currency_id', '=', self.id)])

            for lp in list_product_ids:
                # buscar el producto en la lista de Bs y actualizar
                dominio = [('currency_id', '=', lp.company_id.currency_id.id or self.env.company.currency_id.id)]
                if lp.product_id:
                    dominio.append((('product_id', '=', lp.product_id.id)))
                elif lp.product_tmpl_id:
                    dominio.append((('product_tmpl_id', '=', lp.product_tmpl_id.id)))
                product_id_bs = self.env['product.pricelist.item'].search(dominio)
                for p in product_id_bs:
                    p.fixed_price = lp.fixed_price * rec.inverse_rate

            channel_id = self.env.ref('account_dual_currency.trm_channel')
            channel_id.message_post(
                body="Todos los productos han sido actualizados con la nueva tasa de cambio",
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )

    def get_bcv(self):
        url = "https://www.bcv.org.ve/"
        req = requests.get(url, verify=False)

        status_code = req.status_code
        if status_code == 200:

            html = BeautifulSoup(req.text, "html.parser")
            # Dolar
            dolar = html.find('div', {'id': 'dolar'})
            dolar = str(dolar.find('strong')).split()
            dolar = str.replace(dolar[1], '.', '')
            dolar = float(str.replace(dolar, ',', '.'))
            # Euro
            euro = html.find('div', {'id': 'euro'})
            euro = str(euro.find('strong')).split()
            euro = str.replace(euro[1], '.', '')
            euro = float(str.replace(euro, ',', '.'))

            if self.name == 'USD':
                bcv = dolar
            elif self.name == 'EUR':
                bcv = euro
            else:
                bcv = False

            return bcv
        else:
            return False

    def get_dolar_today_promedio(self):
        url = "https://s3.amazonaws.com/dolartoday/data.json"
        response = requests.get(url)
        status_code = response.status_code

        if status_code == 200:
            response = response.json()
            usd = float(response['USD']['transferencia'])
            eur = float(response['EUR']['transferencia'])
            if self.name == 'USD':
                data = usd
            elif self.name == 'EUR':
                data = eur
            else:
                data = False

            return data
        else:
            return False

    def actualizar_tasa(self):
        for rec in self:
            nueva_tasa = 0
            if rec.server == 'bcv':
                tasa_bcv = rec.get_bcv()
                if tasa_bcv:
                    nueva_tasa = tasa_bcv
            elif rec.server == 'dolar_today':
                tasa_dt = rec.get_dolar_today_promedio()
                if tasa_dt:
                    nueva_tasa = tasa_dt

            if nueva_tasa > 0:
                channel_id = self.env.ref('account_dual_currency.trm_channel')
                company_ids = self.env['res.company'].search([])
                nueva = True
                for c in company_ids:
                    tasa_actual = self.env['res.currency.rate'].sudo().search(
                        [('name', '=', datetime.now()), ('currency_id', '=', self.id), ('company_id', '=', c.id)])
                    if len(tasa_actual) == 0:
                        self.env['res.currency.rate'].sudo().create({
                                'currency_id': self.id,
                                'name': datetime.now(),
                                'rate': 1 / nueva_tasa,
                                'company_id': c.id,
                        })

                    else:
                        if rec.server== 'dolar_today':
                            tasa_actual.rate = 1 / nueva_tasa
                            nueva = False

                if nueva:
                    channel_id.message_post(
                        body="Nueva tasa de cambio del %s: %s, actualizada desde %s a las %s." % (
                            rec.name, nueva_tasa, rec.server,
                            datetime.strftime(fields.Datetime.context_timestamp(self, datetime.now()),
                                              "%d-%m-%Y %H:%M:%S")),
                        message_type='notification',
                        subtype_xmlid='mail.mt_comment',
                    )
                else:
                    channel_id.message_post(
                        body="Tasa de cambio actualizada del %s: %s, desde %s a las %s." % (
                            rec.name, nueva_tasa, rec.server,
                            datetime.strftime(fields.Datetime.context_timestamp(self, datetime.now()),
                                              "%d-%m-%Y %H:%M:%S")),
                        message_type='notification',
                        subtype_xmlid='mail.mt_comment',
                    )
                if rec.act_productos:
                    rec.actualizar_productos()


    @api.model
    def _cron_actualizar_tasa(self):
        monedas = self.env['res.currency'].search([('active', '=', True), ('sincronizar', '=',True)])
        for m in monedas:
            m.actualizar_tasa()