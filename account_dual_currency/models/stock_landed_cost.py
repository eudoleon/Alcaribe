# -*- coding: utf-8 -*-
from odoo import fields, models, tools, api, _
from collections import defaultdict
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_is_zero


class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        required=True,
        related="",
        default=lambda self: self.env.user.company_id.currency_id,
    )
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    amount_total = fields.Monetary(
        'Total', compute='_compute_total_amount',
        store=True, tracking=True, currency_field="company_currency_id")

    move_ids = fields.Many2many('account.move', readonly=True)

    @api.onchange("account_journal_id")
    def _onchange_account_journal_id(self):
        if self.account_journal_id and self.account_journal_id.currency_id:
            self.currency_id = self.account_journal_id.currency_id

    @api.onchange("currency_id", "tax_today")
    def _onchange_currency_id(self):
        if self.currency_id:
            self.cost_lines._onchange_currency_price_unit()

    def _get_default_tasa(self):
        for rec in self:
            return self.env.company.currency_id_dif.inverse_rate

    def button_validate(self):
        self._check_can_validate()
        cost_without_adjusment_lines = self.filtered(lambda c: not c.valuation_adjustment_lines)
        if cost_without_adjusment_lines:
            cost_without_adjusment_lines.compute_landed_cost()
        if not self._check_sum():
            raise UserError(_('Cost and adjustments lines do not match. You should maybe recompute the landed costs.'))

        for cost in self:
            cost = cost.with_company(cost.company_id)
            move = self.env['account.move']

            valuation_layer_ids = []
            cost_to_add_byproduct = defaultdict(lambda: 0.0)
            cost_to_add_byproduct_usd = defaultdict(lambda: 0.0)
            asientos = []
            for line in cost.valuation_adjustment_lines.filtered(lambda line: line.move_id):
                remaining_qty = sum(line.move_id.stock_valuation_layer_ids.mapped('remaining_qty'))
                linked_layer = line.move_id.stock_valuation_layer_ids[:1]

                # Prorate the value at what's still in stock
                cost_to_add = (remaining_qty / line.move_id.product_qty) * line.additional_landed_cost
                cost_to_add_usd = (remaining_qty / line.move_id.product_qty) * line.additional_landed_cost_usd
                if not cost.company_id.currency_id.is_zero(cost_to_add):
                    layer = {
                        'value': cost_to_add,
                        'value_usd': cost_to_add_usd,
                        'unit_cost': 0,
                        'quantity': 0,
                        'remaining_qty': 0,
                        'stock_valuation_layer_id': linked_layer.id,
                        'description': cost.name,
                        'stock_move_id': line.move_id.id,
                        'product_id': line.move_id.product_id.id,
                        'stock_landed_cost_id': cost.id,
                        'company_id': cost.company_id.id,
                    }
                    valuation_layer = self.env['stock.valuation.layer'].create(layer)

                    linked_layer.remaining_value += cost_to_add
                    linked_layer.remaining_value_usd += cost_to_add_usd
                    valuation_layer_ids.append(valuation_layer.id)
                # Update the AVCO
                product = line.move_id.product_id
                if product.cost_method == 'average':
                    cost_to_add_byproduct[product] += cost_to_add
                    cost_to_add_byproduct_usd[product] += cost_to_add_usd
                # Products with manual inventory valuation are ignored because they do not need to create journal entries.
                if product.valuation != "real_time":
                    continue
                # `remaining_qty` is negative if the move is out and delivered proudcts that were not
                # in stock.
                qty_out = 0
                if line.move_id._is_in():
                    qty_out = line.move_id.product_qty - remaining_qty
                elif line.move_id._is_out():
                    qty_out = line.move_id.product_qty

                move_vals = {
                    'journal_id': cost.account_journal_id.id,
                    'date': cost.date,
                    'ref': cost.name,
                    'line_ids': [],
                    'tax_today': line.tax_today,
                    'currency_id': self.env.company.currency_id.id,
                    'currency_id_dif': self.env.company.currency_id_dif.id,
                    'move_type': 'entry',
                }

                move = move.with_context(check_move_validity=False).create(move_vals)

                move.write({'line_ids': line._create_accounting_entries(move, qty_out)})
                move.write({'stock_valuation_layer_ids': [(6, None, valuation_layer_ids)]})
                move.tax_today = line.tax_today
                asientos.append(move.id)
            # batch standard price computation avoid recompute quantity_svl at each iteration
            products = self.env['product.product'].browse(p.id for p in cost_to_add_byproduct.keys())
            for product in products:  # iterate on recordset to prefetch efficiently quantity_svl
                if not float_is_zero(product.quantity_svl, precision_rounding=product.uom_id.rounding):
                    product.with_company(cost.company_id).sudo().with_context(disable_auto_svl=True).standard_price += \
                    cost_to_add_byproduct[product] / product.quantity_svl

                    product.with_company(cost.company_id).sudo().with_context(disable_auto_svl=True).standard_price_usd += \
                        cost_to_add_byproduct_usd[product] / product.quantity_svl

            # move_vals['stock_valuation_layer_ids'] = [(6, None, valuation_layer_ids)]
            # We will only create the accounting entry when there are defined lines (the lines will be those linked to products of real_time valuation category).
            # cost_vals = {} #{'state': 'done'}
            # if move_vals.get("line_ids"):
            #     #print(move_vals.get("line_ids"))
            #     move.write({'line_ids': move_vals.get("line_ids")})
            #     #print('pasa')
            #     cost_vals.update({'account_move_id': move.id})
            cost.move_ids = [(6, None, asientos)]
            if cost.move_ids:
                cost.move_ids._post()
            cost.write({'state': 'done'})
            if cost.vendor_bill_id and cost.vendor_bill_id.state == 'posted' and cost.company_id.anglo_saxon_accounting:
                all_amls = cost.vendor_bill_id.line_ids | cost.move_ids.filtered(lambda m: m.state == 'posted').line_ids
                for product in cost.cost_lines.product_id:
                    accounts = product.product_tmpl_id.get_product_accounts()
                    input_account = accounts['stock_input']
                    all_amls.filtered(lambda aml: aml.account_id == input_account and not aml.reconciled).reconcile()

        return True

    def get_valuation_lines(self):
        self.ensure_one()
        lines = []

        for move in self._get_targeted_move_ids():
            # it doesn't make sense to make a landed cost for a product that isn't set as being valuated in real time at real cost
            if move.product_id.cost_method not in ('fifo', 'average') or move.state == 'cancel' or not move.product_qty:
                continue
            vals = {
                'product_id': move.product_id.id,
                'move_id': move.id,
                'quantity': move.product_qty,
                'former_cost': sum(move.stock_valuation_layer_ids.mapped('value')),
                'former_cost_usd': sum(move.stock_valuation_layer_ids.mapped('value_usd')),
                'weight': move.product_id.weight * move.product_qty,
                'volume': move.product_id.volume * move.product_qty
            }
            lines.append(vals)

        if not lines:
            target_model_descriptions = dict(self._fields['target_model']._description_selection(self.env))
            raise UserError(_("You cannot apply landed costs on the chosen %s(s). Landed costs can only be applied for products with FIFO or average costing method.", target_model_descriptions[self.target_model]))
        return lines

    def compute_landed_cost(self):
        AdjustementLines = self.env['stock.valuation.adjustment.lines']
        AdjustementLines.search([('cost_id', 'in', self.ids)]).unlink()

        towrite_dict = {}
        towrite_dict_usd = {}
        for cost in self.filtered(lambda cost: cost._get_targeted_move_ids()):
            rounding = cost.currency_id.rounding
            total_qty = 0.0
            total_cost = 0.0
            total_weight = 0.0
            total_volume = 0.0
            total_line = 0.0
            all_val_line_values = cost.get_valuation_lines()
            for val_line_values in all_val_line_values:
                for cost_line in cost.cost_lines:
                    val_line_values.update({'cost_id': cost.id, 'cost_line_id': cost_line.id, 'tax_today':cost_line.tax_today})
                    self.env['stock.valuation.adjustment.lines'].create(val_line_values)
                total_qty += val_line_values.get('quantity', 0.0)
                total_weight += val_line_values.get('weight', 0.0)
                total_volume += val_line_values.get('volume', 0.0)

                former_cost = val_line_values.get('former_cost', 0.0)
                # round this because former_cost on the valuation lines is also rounded
                total_cost += cost.currency_id.round(former_cost)

                total_line += 1

            for line in cost.cost_lines:
                value_split = 0.0
                for valuation in cost.valuation_adjustment_lines:
                    value = 0.0
                    if valuation.cost_line_id and valuation.cost_line_id.id == line.id:
                        if line.split_method == 'by_quantity' and total_qty:
                            per_unit = (line.price_unit / total_qty)
                            value = valuation.quantity * per_unit
                        elif line.split_method == 'by_weight' and total_weight:
                            per_unit = (line.price_unit / total_weight)
                            value = valuation.weight * per_unit
                        elif line.split_method == 'by_volume' and total_volume:
                            per_unit = (line.price_unit / total_volume)
                            value = valuation.volume * per_unit
                        elif line.split_method == 'equal':
                            value = (line.price_unit / total_line)
                        elif line.split_method == 'by_current_cost_price' and total_cost:
                            per_unit = (line.price_unit / total_cost)
                            value = valuation.former_cost * per_unit
                        else:
                            value = (line.price_unit / total_line)

                        if rounding:
                            value = tools.float_round(value, precision_rounding=rounding, rounding_method='UP')
                            fnc = min if line.price_unit > 0 else max
                            value = fnc(value, line.price_unit - value_split)
                            value_split += value

                        if valuation.id not in towrite_dict:
                            towrite_dict[valuation.id] = value
                            towrite_dict_usd[valuation.id] = value / line.tax_today
                        else:
                            towrite_dict[valuation.id] += value
                            towrite_dict_usd[valuation.id] += value / line.tax_today
        for key, value in towrite_dict.items():
            AdjustementLines.browse(key).write({'additional_landed_cost': value, 'additional_landed_cost_usd': towrite_dict_usd[key]})
        return True
