from odoo import api, fields, models, tools

class PosOrderReport(models.Model):
    _name = "report.pos.order.usd"
    _description = "Point of Sale Orders Report"
    _auto = False
    _order = 'date desc'

    date = fields.Datetime(string='Order Date', readonly=True)
    order_id = fields.Many2one('pos.order', string='Order', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product Template', readonly=True)
    state = fields.Selection(
        [('draft', 'New'), ('paid', 'Paid'), ('done', 'Posted'),
         ('invoiced', 'Invoiced'), ('cancel', 'Cancelled')],
        string='Status', readonly=True)
    user_id = fields.Many2one('res.users', string='User', readonly=True)
    price_total = fields.Float(string='Total Price', readonly=True)
    price_sub_total = fields.Float(string='Subtotal w/o discount', readonly=True)
    total_discount = fields.Float(string='Total Discount', readonly=True)
    average_price = fields.Float(string='Average Price', readonly=True, group_operator="avg")
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    nbr_lines = fields.Integer(string='Sale Line Count', readonly=True)
    product_qty = fields.Integer(string='Product Quantity', readonly=True)
    journal_id = fields.Many2one('account.journal', string='Journal', readonly=True)
    delay_validation = fields.Integer(string='Delay Validation', readonly=True)
    product_categ_id = fields.Many2one('product.category', string='Product Category', readonly=True)
    invoiced = fields.Boolean(readonly=True)
    config_id = fields.Many2one('pos.config', string='Point of Sale', readonly=True)
    pos_categ_id = fields.Many2one('pos.category', string='PoS Category', readonly=True)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', readonly=True)
    session_id = fields.Many2one('pos.session', string='Session', readonly=True)
    margin = fields.Float(string='Margin', readonly=True)

    # Nuevos campos para USD
    price_total_usd = fields.Float(string='Total Price (USD)', readonly=True)
    price_sub_total_usd = fields.Float(string='Subtotal w/o discount (USD)', readonly=True)
    total_discount_usd = fields.Float(string='Total Discount (USD)', readonly=True)
    average_price_usd = fields.Float(string='Average Price (USD)', readonly=True, group_operator="avg")
    margin_usd = fields.Float(string='Margin (USD)', readonly=True)

    def _select(self):
        return """
            SELECT
                MIN(l.id) AS id,
                COUNT(*) AS nbr_lines,
                s.date_order AS date,
                SUM(l.qty) AS product_qty,
                SUM(l.qty * l.price_unit / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) AS price_sub_total,
                SUM(ROUND((l.price_subtotal_incl) / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END, cu.decimal_places)) AS price_total,
                SUM((l.qty * l.price_unit) * (l.discount / 100) / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) AS total_discount,
                CASE
                    WHEN SUM(l.qty * u.factor) = 0 THEN NULL
                    ELSE (SUM(l.qty*l.price_unit / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END)/SUM(l.qty * u.factor))::decimal
                END AS average_price,
                SUM(cast(to_char(date_trunc('day',s.date_order) - date_trunc('day',s.create_date),'DD') AS INT)) AS delay_validation,
                s.id as order_id,
                s.partner_id AS partner_id,
                s.state AS state,
                s.user_id AS user_id,
                s.company_id AS company_id,
                s.sale_journal AS journal_id,
                l.product_id AS product_id,
                pt.categ_id AS product_categ_id,
                p.product_tmpl_id,
                ps.config_id,
                pt.pos_categ_id,
                s.pricelist_id,
                s.session_id,
                s.account_move IS NOT NULL AS invoiced,
                SUM(l.price_subtotal - COALESCE(l.total_cost,0) / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) AS margin,
                -- Campos en USD
                SUM(ROUND(l.price_subtotal_incl * COALESCE(cr_usd.rate, 1.0), cu.decimal_places)) AS price_total_usd,
                SUM(l.qty * l.price_unit * COALESCE(cr_usd.rate, 1.0)) AS price_sub_total_usd,
                SUM((l.qty * l.price_unit) * (l.discount / 100) * COALESCE(cr_usd.rate, 1.0)) AS total_discount_usd,
                (SUM(l.qty*l.price_unit * COALESCE(cr_usd.rate, 1.0))/SUM(l.qty * u.factor))::decimal AS average_price_usd, 
                SUM((l.price_subtotal - COALESCE(l.total_cost,0)) * COALESCE(cr_usd.rate, 1.0)) AS margin_usd
        """

    def _from(self):
        return """
            FROM pos_order_line AS l
                INNER JOIN pos_order s ON (s.id=l.order_id)
                LEFT JOIN product_product p ON (l.product_id=p.id)
                LEFT JOIN product_template pt ON (p.product_tmpl_id=pt.id)
                LEFT JOIN uom_uom u ON (u.id=pt.uom_id)
                LEFT JOIN pos_session ps ON (s.session_id=ps.id)
                LEFT JOIN res_company co ON (s.company_id=co.id)
                LEFT JOIN res_currency cu ON (co.currency_id=cu.id)
                LEFT JOIN res_currency usd_currency ON (usd_currency.name = 'USD')
                LEFT JOIN res_currency_rate cr_usd ON (cr_usd.currency_id = usd_currency.id
                    AND cr_usd.name <= COALESCE(s.date_order, s.create_date)
                    AND (cr_usd.company_id IS NULL OR cr_usd.company_id = s.company_id))
        """

    def _group_by(self):
        return """
            GROUP BY
                s.id, s.date_order, s.partner_id, s.state, pt.categ_id,
                s.user_id, s.company_id, s.sale_journal,
                s.pricelist_id, s.account_move, s.create_date, s.session_id,
                l.product_id,
                pt.categ_id, pt.pos_categ_id,
                p.product_tmpl_id,
                ps.config_id,
                usd_currency.id,
                cr_usd.rate
        """

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                %s
                %s
                %s
            )
        """ % (self._table, self._select(), self._from(), self._group_by())
        )