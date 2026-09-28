# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
import time
from datetime import datetime, date, timedelta
from odoo.tools import (
    DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT,
    DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT,
)
import xlsxwriter
import base64
from io import BytesIO


class AccountInventoryBookWizard(models.TransientModel):
    _name = "account.inventory.book.wizard"
    _description = "Asistente de Libro de Inventario"

    date_start = fields.Date(
        "Fecha de Inicio", required=True, default=fields.Date.context_today
    )
    date_end = fields.Date(
        "Fecha Fin", required=True, default=fields.Date.context_today
    )
    product_type_filter = fields.Selection(
        [
            ("all", _("Todos los productos")),
            ("category", _("Categoría")),
            ("product", _("Producto")),
        ],
        "Filtrar por",
        required=True,
        default="all",
    )

    category_ids = fields.Many2many(comodel_name="product.category", string="Categoría")
    product_ids = fields.Many2many(
        comodel_name="product.product",
        string="Producto",
        domain="[('detailed_type','=','product')]",
    )
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )

    @api.onchange("product_type_filter")
    def _onchange_product_type_filter(self):
        for rec in self:
            if rec.product_type_filter == "all":
                rec.product_ids = False
                rec.category_ids = False
            elif rec.product_type_filter == "category":
                rec.product_ids = False
            elif rec.product_type_filter == "product":
                rec.category_ids = False

    def imprimir_pdf(self):
        for rec in self:
            data = {
                "ids": 0,
                "form": {
                    "date_from": self.date_start,
                    "date_to": self.date_end,
                    "category_ids": self.category_ids.ids if self.category_ids else [],
                    "product_ids": self.product_ids.ids if self.product_ids else [],
                    "company": self.company_id.id,
                },
            }
            return self.env.ref("account_inventory_book.report_inventary_book").report_action(
                self, data=data
            )

    def imprimir_xlsx(self):
        for rec in self:
            data = {
                "ids": 0,
                "form": {
                    "date_from": self.date_start,
                    "date_to": self.date_end,
                    "category_ids": self.category_ids.ids if self.category_ids else [],
                    "product_ids": self.product_ids.ids if self.product_ids else [],
                    "company": self.company_id.id,
                },
            }
            report_values = self.env[
                "report.account_inventory_book.report_invantary_book_template"
            ]._get_report_values(self.ids, data=data)

            output = BytesIO()
            workbook = xlsxwriter.Workbook(output, {"in_memory": True})
            sheet = workbook.add_worksheet("Libro de Inventario")
            formats = self.set_formats(workbook)

            # Headers
            sheet.merge_range("B2:E2", report_values["company"].name, formats["bold"])
            company_rif = getattr(report_values["company"], "rif", False) or report_values["company"].vat or ""
            sheet.merge_range(
                "B3:E3",
                company_rif,
                formats["bold"],
            )

            address = report_values["company"].street or ""
            if report_values["company"].street2:
                address += ", " + report_values["company"].street2
            if report_values["company"].city:
                address += ", " + report_values["company"].city
            if report_values["company"].state_id:
                address += ", " + report_values["company"].state_id.name
            if report_values["company"].country_id:
                address += ", " + report_values["company"].country_id.name

            sheet.merge_range("B4:E4", address, formats["bold"])

            sheet.merge_range("F2:I2", "LIBRO DE INVENTARIO", formats["title_center"])
            sheet.merge_range(
                "F3:I3",
                "Desde: %s Hasta: %s"
                % (
                    report_values["date_start"].strftime("%d/%m/%Y"),
                    report_values["date_end"].strftime("%d/%m/%Y"),
                ),
                formats["center"],
            )
            sheet.merge_range(
                "F4:M4",
                "Base Legal: Artículo 177. Los contribuyentes, responsables y terceros están obligados a llevar y mantener en el domicilio fiscal o establecimiento a través de medios manuales o magnéticos cuando la Administración Tributaria lo autorice, la siguiente información relativa al registro detallado de entradas y salidas de mercancías de los inventarios, mensuales, por unidades y valores así como, los retiros y autoconsumo de bienes y servicios.",
                formats["text_wrap_center"],
            )

            # Table Headers
            row = 6
            sheet.merge_range(
                row, 2, row, 4, "Inventario Inicial", formats["header_center"]
            )
            sheet.merge_range(
                row, 5, row, 7, "Entradas del Mes", formats["header_center"]
            )
            sheet.merge_range(
                row, 8, row, 10, "Salidas del Mes", formats["header_center"]
            )
            sheet.merge_range(
                row, 11, row, 13, "Inventario Final", formats["header_center"]
            )

            row += 1
            headers = [
                "Código",
                "Descripción",
                "Existencia Inicial",
                "Costo Inicial",
                "Total",
                "Cant. Entradas",
                "Costo Entradas",
                "Total",
                "Cant. Salidas",
                "Costo Salidas",
                "Total",
                "Stock Final",
                "Costo Promedio",
                "Total",
            ]

            for i, header in enumerate(headers):
                sheet.write(row, i, header, formats["header"])

            row += 1

            # Data
            for d in report_values["datos"]:
                sheet.write(row, 0, d["default_code"], formats["left"])
                sheet.write(row, 1, d["name"], formats["left"])

                sheet.write(row, 2, d["existencia_inicial"], formats["number"])
                sheet.write(row, 3, d["precio_inicial"], formats["money"])
                sheet.write(row, 4, d["precio_total_inicial"], formats["money"])

                sheet.write(row, 5, d["entradas_mes"], formats["number"])
                sheet.write(row, 6, d["entradas_mes_precio"], formats["money"])
                sheet.write(row, 7, d["entradas_mes_precio_total"], formats["money"])

                sheet.write(row, 8, d["salida_mes"], formats["number"])
                sheet.write(row, 9, d["salida_mes_precio"], formats["money"])
                sheet.write(row, 10, d["salida_mes_precio_total"], formats["money"])

                sheet.write(row, 11, d["final"], formats["number"])
                sheet.write(row, 12, d["final_precio"], formats["money"])
                sheet.write(row, 13, d["final_precio_total"], formats["money"])

                row += 1

            workbook.close()
            output.seek(0)
            file_base64 = base64.b64encode(output.read())

            attachment_id = (
                self.env["ir.attachment"]
                .sudo()
                .create(
                    {
                        "name": "Libro_Inventario.xlsx",
                        "datas": file_base64,
                        "type": "binary",
                        "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    }
                )
            )

            return {
                "type": "ir.actions.act_url",
                "url": "/web/content/%s?download=true" % attachment_id.id,
                "target": "self",
            }

    def set_formats(self, workbook):
        formats = {}
        formats["bold"] = workbook.add_format({"bold": True})
        formats["center"] = workbook.add_format({"align": "center"})
        formats["left"] = workbook.add_format({"align": "left"})
        formats["title_center"] = workbook.add_format(
            {"bold": True, "align": "center", "font_size": 14}
        )
        formats["header"] = workbook.add_format(
            {"bold": True, "align": "center", "border": 1, "bg_color": "#f0f0f0"}
        )
        formats["header_center"] = workbook.add_format(
            {"bold": True, "align": "center", "border": 1, "bg_color": "#e0e0e0"}
        )
        formats["number"] = workbook.add_format({"num_format": "#,##0.00"})
        formats["money"] = workbook.add_format({"num_format": "#,##0.00"})
        formats["text_wrap_center"] = workbook.add_format(
            {
                "bold": False,
                "align": "center",
                "valign": "top",
                "text_wrap": True,
                "font_size": 10,
            }
        )
        return formats


class AccountInventoryBookReport(models.AbstractModel):
    _name = "report.account_inventory_book.report_invantary_book_template"
    _description = "Reporte de Libro de Inventario"

    @api.model
    def _get_report_values(self, docids, data=None):
        date_start = data["form"]["date_from"]
        date_end = data["form"]["date_to"]
        if isinstance(date_start, str):
            date_start = datetime.strptime(date_start, DATE_FORMAT)
        if isinstance(date_end, str):
            date_end = datetime.strptime(date_end, DATE_FORMAT)

        if isinstance(date_start, date) and not isinstance(date_start, datetime):
            date_start = datetime.combine(date_start, datetime.min.time())
        if isinstance(date_end, date) and not isinstance(date_end, datetime):
            date_end = datetime.combine(date_end, datetime.min.time())

        date_end_search = date_end + timedelta(days=1)

        company_id = self.env["res.company"].search(
            [("id", "=", data["form"]["company"])]
        )
        datos = []
        dominio_productos = [
            "|",
            ("company_id", "=", company_id.id),
            ("company_id", "=", False),
            ("detailed_type", "=", "product"),
        ]

        if data["form"]["category_ids"]:
            dominio_productos.append(("categ_id", "in", data["form"]["category_ids"]))
        if data["form"]["product_ids"]:
            dominio_productos.append(("id", "in", data["form"]["product_ids"]))

        productos_ids = self.env["product.product"].search(dominio_productos)
        for p in productos_ids:
            # 1. Buscar saldos iniciales del producto
            initial_moves = self.env["stock.move"].search(
                [
                    ("product_id", "=", p.id),
                    ("date", "<", data["form"]["date_from"]),
                    ("state", "=", "done"),
                    ("company_id", "=", company_id.id),
                ]
            )

            existencia_inicial = 0.0
            precio_inicial = 0.0
            precio_total_inicial = 0.0

            initial_layers = initial_moves.mapped("stock_valuation_layer_ids")
            if initial_layers:
                existencia_inicial = sum(initial_layers.mapped("quantity"))
                precio_total_inicial = sum(initial_layers.mapped("value"))
                if existencia_inicial != 0:
                    precio_inicial = precio_total_inicial / existencia_inicial
                else:
                    precio_inicial = 0.0
            elif p.standard_price:
                # Si no tiene layers iniciales pero tiene precio estándar y stock
                precio_inicial = p.standard_price

            # 2. Movimientos del mes
            period_moves = self.env["stock.move"].search(
                [
                    ("product_id", "=", p.id),
                    ("date", ">=", data["form"]["date_from"]),
                    ("date", "<", date_end_search),
                    ("state", "=", "done"),
                    ("company_id", "=", company_id.id),
                ]
            )

            period_layers = period_moves.mapped("stock_valuation_layer_ids")

            entradas_mes = 0.0
            entradas_mes_precio = 0.0
            entradas_mes_precio_total = 0.0

            salida_mes = 0.0
            salida_mes_precio = 0.0
            salida_mes_precio_total = 0.0

            # 2.1 Cálculo de ENTRADAS basado en facturas de compra asociadas
            entradas_layers = period_layers.filtered(lambda x: x.quantity > 0)
            if entradas_layers:
                entradas_mes = sum(entradas_layers.mapped("quantity"))
                for layer in entradas_layers:
                    move = layer.stock_move_id
                    layer_qty = layer.quantity
                    unit_cost = 0.0
                    found_invoice = False

                    if move:
                        # Buscar factura de compra asociada (PO line -> invoice lines)
                        inv_lines = self.env["account.move.line"]
                        if move.purchase_line_id:
                            inv_lines = move.purchase_line_id.invoice_lines.filtered(
                                lambda l: l.move_id.state == "posted"
                                and l.move_id.move_type in ("in_invoice", "in_refund")
                            )
                        if not inv_lines and move.picking_id and getattr(move.picking_id, "purchase_id", False):
                            po_lines = move.picking_id.purchase_id.order_line.filtered(
                                lambda pol: pol.product_id == p
                            )
                            inv_lines = po_lines.mapped("invoice_lines").filtered(
                                lambda l: l.move_id.state == "posted"
                                and l.move_id.move_type in ("in_invoice", "in_refund")
                            )

                        if inv_lines:
                            found_invoice = True
                            # Calcular precio unitario en moneda de la compañía según la factura
                            total_inv_val = sum(abs(l.balance) for l in inv_lines)
                            total_inv_qty = sum(l.quantity for l in inv_lines)
                            if total_inv_qty:
                                unit_cost = total_inv_val / total_inv_qty
                            else:
                                unit_cost = inv_lines[0].price_unit

                    # Fallbacks si no hay factura de compra asociada
                    if not found_invoice or unit_cost <= 0:
                        if layer.quantity != 0 and layer.value != 0:
                            unit_cost = layer.value / layer.quantity
                        elif move and move.purchase_line_id and move.purchase_line_id.price_unit:
                            unit_cost = move.purchase_line_id.price_unit
                        else:
                            unit_cost = p.standard_price or 0.0

                    entradas_mes_precio_total += layer_qty * unit_cost

                if entradas_mes > 0:
                    entradas_mes_precio = entradas_mes_precio_total / entradas_mes

            # 2.2 Cálculo de SALIDAS basado en el Coste Promedio de la ficha del producto
            salidas_layers = period_layers.filtered(lambda x: x.quantity < 0)
            if salidas_layers:
                salida_mes = abs(sum(salidas_layers.mapped("quantity")))
                # Coste promedio de la ficha del producto
                costo_ficha = p.standard_price
                if not costo_ficha or costo_ficha <= 0:
                    # Fallback a capas de salida o costo inicial
                    total_val_salidas = abs(sum(salidas_layers.mapped("value")))
                    costo_ficha = (total_val_salidas / salida_mes) if salida_mes > 0 else (precio_inicial or 0.0)

                salida_mes_precio = costo_ficha
                salida_mes_precio_total = salida_mes * salida_mes_precio

            # 3. Cálculo de INVENTARIO FINAL (Valuación contable estándar: Costo Promedio Ponderado)
            final = existencia_inicial + entradas_mes - salida_mes
            total_disponible_qty = existencia_inicial + entradas_mes
            total_disponible_val = precio_total_inicial + entradas_mes_precio_total

            if total_disponible_qty > 0 and total_disponible_val > 0:
                costo_promedio_final = total_disponible_val / total_disponible_qty
            elif p.standard_price > 0:
                costo_promedio_final = p.standard_price
            elif precio_inicial > 0:
                costo_promedio_final = precio_inicial
            else:
                costo_promedio_final = 0.0

            final_precio = costo_promedio_final
            final_precio_total = (final * final_precio) if final > 0 else 0.0

            datos.append(
                {
                    "default_code": p.default_code or "",
                    "name": p.name,
                    "existencia_inicial": existencia_inicial,
                    "precio_inicial": precio_inicial,
                    "precio_total_inicial": precio_total_inicial,
                    "entradas_mes": entradas_mes,
                    "entradas_mes_precio": entradas_mes_precio,
                    "entradas_mes_precio_total": entradas_mes_precio_total,
                    "salida_mes": salida_mes,
                    "salida_mes_precio": salida_mes_precio,
                    "salida_mes_precio_total": salida_mes_precio_total,
                    "final": final,
                    "final_precio": final_precio,
                    "final_precio_total": final_precio_total,
                }
            )

        company_rif = (
            getattr(company_id, "rif", False) or company_id.vat or ""
        )
        return {
            "company": company_id,
            "company_rif": company_rif,
            "currency": company_id.currency_id,
            "date_start": (
                date_start.date() if isinstance(date_start, datetime) else date_start
            ),
            "date_end": date_end.date() if isinstance(date_end, datetime) else date_end,
            "datos": datos,
        }
