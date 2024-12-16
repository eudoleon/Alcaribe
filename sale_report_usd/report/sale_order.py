# Copyright 2023 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class SaleReport(models.Model):
    _name = "sale.report.usd"
    _description = "Sales Analysis Report USD"
    _auto = False
    _rec_name = 'date'
    _order = 'date desc'

    @api.model
    def _get_done_states(self):
        done_states = ['sale', 'done']
        done_states.extend(['paid', 'invoiced', 'done'])
        return done_states

    name = fields.Char('Order Reference', readonly=True)
    date = fields.Datetime('Order Date', readonly=True)
    product_id = fields.Many2one('product.product', 'Product Variant', readonly=True)
    product_uom = fields.Many2one('uom.uom', 'Unit of Measure', readonly=True)
    product_uom_qty = fields.Float('Qty Ordered', readonly=True)
    qty_to_deliver = fields.Float('Qty To Deliver', readonly=True)
    qty_delivered = fields.Float('Qty Delivered', readonly=True)
    qty_to_invoice = fields.Float('Qty To Invoice', readonly=True)
    qty_invoiced = fields.Float('Qty Invoiced', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Customer', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    user_id = fields.Many2one('res.users', 'Salesperson', readonly=True)
    price_total = fields.Float('Total', readonly=True)
    price_subtotal = fields.Float('Untaxed Total', readonly=True)
    untaxed_amount_to_invoice = fields.Float('Untaxed Amount To Invoice', readonly=True)
    untaxed_amount_invoiced = fields.Float('Untaxed Amount Invoiced', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', 'Product', readonly=True)
    categ_id = fields.Many2one('product.category', 'Product Category', readonly=True)
    nbr = fields.Integer('# of Lines', readonly=True)
    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist', readonly=True)
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account', readonly=True)
    team_id = fields.Many2one('crm.team', 'Sales Team', readonly=True)
    country_id = fields.Many2one('res.country', 'Customer Country', readonly=True)
    industry_id = fields.Many2one('res.partner.industry', 'Customer Industry', readonly=True)
    commercial_partner_id = fields.Many2one('res.partner', 'Customer Entity', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Sales Done'),
        ('cancel', 'Cancelled'),
        ('paid', 'Paid'),
        ('invoiced', 'Invoiced')
    ], string='Status', readonly=True)
    weight = fields.Float('Gross Weight', readonly=True)
    volume = fields.Float('Volume', readonly=True)
    discount = fields.Float('Discount %', readonly=True, group_operator="avg")
    discount_amount = fields.Float('Discount Amount', readonly=True)
    campaign_id = fields.Many2one('utm.campaign', 'Campaign', readonly=True)
    medium_id = fields.Many2one('utm.medium', 'Medium', readonly=True)
    source_id = fields.Many2one('utm.source', 'Source', readonly=True)
    order_id = fields.Many2one('sale.order', 'Order #', readonly=True)
    price_total_usd = fields.Monetary('Total (USD)', readonly=True, currency_field='usd_currency_id')
    price_subtotal_usd = fields.Monetary('Untaxed Total (USD)', readonly=True, currency_field='usd_currency_id')
    untaxed_amount_to_invoice_usd = fields.Monetary('Untaxed Amount To Invoice (USD)', readonly=True, currency_field='usd_currency_id')
    untaxed_amount_invoiced_usd = fields.Monetary('Untaxed Amount Invoiced (USD)', readonly=True, currency_field='usd_currency_id')
    discount_amount_usd = fields.Monetary('Discount Amount (USD)', readonly=True, currency_field='usd_currency_id')
    usd_currency_id = fields.Many2one('res.currency', string='USD Currency', readonly=True)
    order_reference = fields.Reference(selection=[('sale.order', 'Sale Order'), ('pos.order', 'POS Order')], readonly=True)

    def _with_sale(self):
        return ""

    def _select_sale(self):
        select_ = f"""
            MIN(l.id) AS id,
            l.product_id AS product_id,
            t.uom_id AS product_uom,
            CASE WHEN l.product_id IS NOT NULL THEN SUM(l.product_uom_qty / u.factor * u2.factor) ELSE 0 END AS product_uom_qty,
            CASE WHEN l.product_id IS NOT NULL THEN SUM(l.qty_delivered / u.factor * u2.factor) ELSE 0 END AS qty_delivered,
            CASE WHEN l.product_id IS NOT NULL THEN SUM((l.product_uom_qty - l.qty_delivered) / u.factor * u2.factor) ELSE 0 END AS qty_to_deliver,
            CASE WHEN l.product_id IS NOT NULL THEN SUM(l.qty_invoiced / u.factor * u2.factor) ELSE 0 END AS qty_invoiced,
            CASE WHEN l.product_id IS NOT NULL THEN SUM(l.qty_to_invoice / u.factor * u2.factor) ELSE 0 END AS qty_to_invoice,
            CASE WHEN l.product_id IS NOT NULL THEN SUM(l.price_total
                / {self._case_value_or_one('s.currency_rate')}
                * {self._case_value_or_one('currency_table.rate')}
                ) ELSE 0
            END AS price_total,
            CASE WHEN l.product_id IS NOT NULL THEN SUM(l.price_subtotal
                / {self._case_value_or_one('s.currency_rate')}
                * {self._case_value_or_one('currency_table.rate')}
                ) ELSE 0
            END AS price_subtotal,
            CASE WHEN l.product_id IS NOT NULL THEN SUM(l.untaxed_amount_to_invoice
                / {self._case_value_or_one('s.currency_rate')}
                * {self._case_value_or_one('currency_table.rate')}
                ) ELSE 0
            END AS untaxed_amount_to_invoice,
            CASE WHEN l.product_id IS NOT NULL THEN SUM(l.untaxed_amount_invoiced
                / {self._case_value_or_one('s.currency_rate')}
                * {self._case_value_or_one('currency_table.rate')}
                ) ELSE 0
            END AS untaxed_amount_invoiced,
            COUNT(*) AS nbr,
            s.name AS name,
            s.date_order AS date,
            s.state AS state,
            s.partner_id AS partner_id,
            s.user_id AS user_id,
            s.company_id AS company_id,
            s.campaign_id AS campaign_id,
            s.medium_id AS medium_id,
            s.source_id AS source_id,
            t.categ_id AS categ_id,
            s.pricelist_id AS pricelist_id,
            s.analytic_account_id AS analytic_account_id,
            s.team_id AS team_id,
            p.product_tmpl_id,
            partner.country_id AS country_id,
            partner.industry_id AS industry_id,
            partner.commercial_partner_id AS commercial_partner_id,
            CASE WHEN l.product_id IS NOT NULL THEN SUM(p.weight * l.product_uom_qty / u.factor * u2.factor) ELSE 0 END AS weight,
            CASE WHEN l.product_id IS NOT NULL THEN SUM(p.volume * l.product_uom_qty / u.factor * u2.factor) ELSE 0 END AS volume,
            l.discount AS discount,
            CASE WHEN l.product_id IS NOT NULL THEN SUM(l.price_unit * l.product_uom_qty * l.discount / 100.0
                / {self._case_value_or_one('s.currency_rate')}
                * {self._case_value_or_one('currency_table.rate')}
                ) ELSE 0
            END AS discount_amount,
            s.id AS order_id,
            CASE 
                WHEN s.currency_id = usd_currency.id THEN 
                    CASE WHEN l.product_id IS NOT NULL THEN SUM(l.price_total) ELSE 0 END
                ELSE 
                    CASE WHEN l.product_id IS NOT NULL THEN SUM(l.price_total * {self._case_value_or_one('cr_usd.rate')}) ELSE 0 END
            END AS price_total_usd,
            CASE 
                WHEN s.currency_id = usd_currency.id THEN 
                    CASE WHEN l.product_id IS NOT NULL THEN SUM(l.price_subtotal) ELSE 0 END
                ELSE 
                    CASE WHEN l.product_id IS NOT NULL THEN SUM(l.price_subtotal * {self._case_value_or_one('cr_usd.rate')}) ELSE 0 END
            END AS price_subtotal_usd,
            CASE 
                WHEN s.currency_id = usd_currency.id THEN 
                    CASE WHEN l.product_id IS NOT NULL THEN SUM(l.untaxed_amount_to_invoice) ELSE 0 END
                ELSE 
                    CASE WHEN l.product_id IS NOT NULL THEN SUM(l.untaxed_amount_to_invoice * {self._case_value_or_one('cr_usd.rate')}) ELSE 0 END
            END AS untaxed_amount_to_invoice_usd,
            CASE 
                WHEN s.currency_id = usd_currency.id THEN 
                    CASE WHEN l.product_id IS NOT NULL THEN SUM(l.untaxed_amount_invoiced) ELSE 0 END
                ELSE 
                    CASE WHEN l.product_id IS NOT NULL THEN SUM(l.untaxed_amount_invoiced * {self._case_value_or_one('cr_usd.rate')}) ELSE 0 END
            END AS untaxed_amount_invoiced_usd,
            CASE 
                WHEN s.currency_id = usd_currency.id THEN 
                    CASE WHEN l.product_id IS NOT NULL THEN SUM(l.price_unit * l.product_uom_qty * l.discount / 100.0) ELSE 0 END
                ELSE 
                    CASE WHEN l.product_id IS NOT NULL THEN SUM(l.price_unit * l.product_uom_qty * l.discount / 100.0 * {self._case_value_or_one('cr_usd.rate')}) ELSE 0 END
            END AS discount_amount_usd,
            usd_currency.id AS usd_currency_id,
            concat('sale.order', ',', s.id) AS order_reference"""

        additional_fields_info = self._select_additional_fields()
        template = """,
            %s AS %s"""
        for fname, query_info in additional_fields_info.items():
            select_ += template % (query_info, fname)

        return select_
    def _select_pos(self):
        select_ = f"""
            -MIN(l.id) AS id,
            l.product_id AS product_id,
            t.uom_id AS product_uom,
            SUM(l.qty) AS product_uom_qty,
            SUM(l.qty) AS qty_delivered,
            0 AS qty_to_deliver,
            CASE WHEN pos.state = 'invoiced' THEN SUM(l.qty) ELSE 0 END AS qty_invoiced,
            CASE WHEN pos.state != 'invoiced' THEN SUM(l.qty) ELSE 0 END AS qty_to_invoice,
            SUM(l.price_subtotal_incl)
                / MIN({self._case_value_or_one('pos.currency_rate')})
                * {self._case_value_or_one('currency_table.rate')}
            AS price_total,
            SUM(l.price_subtotal)
                / MIN({self._case_value_or_one('pos.currency_rate')})
                * {self._case_value_or_one('currency_table.rate')}
            AS price_subtotal,
            (CASE WHEN pos.state != 'invoiced' THEN SUM(l.price_subtotal) ELSE 0 END)
                / MIN({self._case_value_or_one('pos.currency_rate')})
                * {self._case_value_or_one('currency_table.rate')}
            AS untaxed_amount_to_invoice,
            (CASE WHEN pos.state = 'invoiced' THEN SUM(l.price_subtotal) ELSE 0 END)
                / MIN({self._case_value_or_one('pos.currency_rate')})
                * {self._case_value_or_one('currency_table.rate')}
            AS untaxed_amount_invoiced,
            count(*) AS nbr,
            pos.name AS name,
            pos.date_order AS date,
            (CASE WHEN pos.state = 'done' THEN 'sale' ELSE pos.state END) AS state,
            pos.partner_id AS partner_id,
            pos.user_id AS user_id,
            pos.company_id AS company_id,
            NULL AS campaign_id,
            NULL AS medium_id,
            NULL AS source_id,
            t.categ_id AS categ_id,
            pos.pricelist_id AS pricelist_id,
            NULL AS analytic_account_id,
            pos.crm_team_id AS team_id,
            p.product_tmpl_id,
            partner.commercial_partner_id AS commercial_partner_id,
            partner.country_id AS country_id,
            partner.industry_id AS industry_id,
            (SUM(p.weight) * l.qty / u.factor) AS weight,
            (SUM(p.volume) * l.qty / u.factor) AS volume,
            l.discount AS discount,
            SUM((l.price_unit * l.discount * l.qty / 100.0
                / {self._case_value_or_one('pos.currency_rate')}
                * {self._case_value_or_one('currency_table.rate')}))
            AS discount_amount,
            pos.id AS order_id,
            SUM(l.price_subtotal_incl * {self._case_value_or_one('cr_usd.rate')}) AS price_total_usd,
            SUM(l.price_subtotal * {self._case_value_or_one('cr_usd.rate')}) AS price_subtotal_usd,
            (CASE WHEN pos.state != 'invoiced' THEN SUM(l.price_subtotal * {self._case_value_or_one('cr_usd.rate')}) ELSE 0 END) AS untaxed_amount_to_invoice_usd,

            (CASE WHEN pos.state = 'invoiced' THEN SUM(l.price_subtotal * {self._case_value_or_one('cr_usd.rate')}) ELSE 0 END) AS untaxed_amount_invoiced_usd,

            SUM((l.price_unit * l.discount * l.qty / 100.0 * {self._case_value_or_one('cr_usd.rate')})) AS discount_amount_usd,
            usd_currency.id AS usd_currency_id,
            concat('pos.order', ',', pos.id) AS order_reference"""

        additional_fields = self._select_additional_fields()
        additional_fields_info = self._fill_pos_fields(additional_fields)
        template = """,
            %s AS %s"""
        for fname, value in additional_fields_info.items():
            select_ += template % (value, fname)
        return select_

    def _case_value_or_one(self, value):
        return f"""CASE COALESCE({value}, 0) WHEN 0 THEN 1.0 ELSE {value} END"""

    def _select_additional_fields(self):
        return {}

    def _from_sale(self):
        return """
            sale_order_line l
            LEFT JOIN sale_order s ON s.id=l.order_id
            JOIN res_partner partner ON s.partner_id = partner.id
            LEFT JOIN product_product p ON l.product_id=p.id
            LEFT JOIN product_template t ON p.product_tmpl_id=t.id
            LEFT JOIN uom_uom u ON u.id=l.product_uom
            LEFT JOIN uom_uom u2 ON u2.id=t.uom_id
            JOIN {currency_table} ON currency_table.company_id = s.company_id
            LEFT JOIN res_currency usd_currency ON usd_currency.name = 'USD'
            LEFT JOIN res_currency_rate cr_usd ON (cr_usd.currency_id = usd_currency.id
                AND cr_usd.name <= COALESCE(s.date_order, s.create_date)
                AND (cr_usd.company_id IS NULL OR cr_usd.company_id = s.company_id))
            """.format(
            currency_table=self.env['res.currency']._get_query_currency_table(
                {
                    'multi_company': True,
                    'date': {'date_to': fields.Date.today()}
                }),
            )

    def _from_pos(self):
        return """
            pos_order_line l
            JOIN pos_order pos ON l.order_id = pos.id
            LEFT JOIN res_partner partner ON (pos.partner_id=partner.id OR pos.partner_id = NULL)
            LEFT JOIN product_product p ON l.product_id=p.id
            LEFT JOIN product_template t ON p.product_tmpl_id=t.id
            LEFT JOIN uom_uom u ON u.id=t.uom_id
            LEFT JOIN pos_session session ON session.id = pos.session_id
            LEFT JOIN pos_config config ON config.id = session.config_id
            LEFT JOIN stock_picking_type picking ON picking.id = config.picking_type_id
            JOIN {currency_table} ON currency_table.company_id = pos.company_id
            LEFT JOIN res_currency usd_currency ON usd_currency.name = 'USD'
            LEFT JOIN res_currency_rate cr_usd ON (cr_usd.currency_id = usd_currency.id
                AND cr_usd.name <= COALESCE(pos.date_order, pos.create_date)
                AND (cr_usd.company_id IS NULL OR cr_usd.company_id = pos.company_id))
            """.format(
                 currency_table=self.env['res.currency']._get_query_currency_table(
                {
                    'multi_company': True,
                    'date': {'date_to': fields.Date.today()}
                }),
            )
    def _where_sale(self):
        return """
            l.display_type IS NULL"""

    def _where_pos(self):
        return """
            l.sale_order_line_id IS NULL"""

    def _group_by_sale(self):
        return """
            l.product_id,
            l.order_id,
            t.uom_id,
            t.categ_id,
            s.name,
            s.date_order,
            s.partner_id,
            s.user_id,
            s.state,
            s.company_id,
            s.campaign_id,
            s.medium_id,
            s.source_id,
            s.pricelist_id,
            s.analytic_account_id,
            s.team_id,
            p.product_tmpl_id,
            partner.country_id,
            partner.industry_id,
            partner.commercial_partner_id,
            l.discount,
            s.id,
            currency_table.rate,
            cr_usd.rate,
            usd_currency.id"""

    def _group_by_pos(self):
        return """
            l.order_id,
            l.product_id,
            l.price_unit,
            l.discount,
            l.qty,
            t.uom_id,
            t.categ_id,
            pos.id,
            pos.name,
            pos.date_order,
            pos.partner_id,
            pos.user_id,
            pos.state,
            pos.company_id,
            pos.pricelist_id,
            p.product_tmpl_id,
            partner.country_id,
            partner.industry_id,
            partner.commercial_partner_id,
            u.factor,
            pos.crm_team_id,
            currency_table.rate,
            cr_usd.rate,
            usd_currency.id,
            picking.warehouse_id"""

    def _query(self):
        return f"""
            SELECT {self._select_sale()}
            FROM {self._from_sale()}
            WHERE {self._where_sale()}
            GROUP BY {self._group_by_sale()}
            UNION ALL
            SELECT {self._select_pos()}
            FROM {self._from_pos()}
            WHERE {self._where_pos()}
            GROUP BY {self._group_by_pos()}
        """

    def _fill_pos_fields(self, additional_fields):
        filled_fields = {x: 'NULL' for x in additional_fields}
        for fname, value in self._available_additional_pos_fields().items():
            if fname in additional_fields:
                filled_fields[fname] = value
        return filled_fields

    def _available_additional_pos_fields(self):
        return {
            'warehouse_id': 'picking.warehouse_id',
        }

    @property
    def _table_query(self):
        return self._query()