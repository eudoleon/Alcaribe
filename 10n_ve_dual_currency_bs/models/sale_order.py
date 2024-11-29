# -*- coding: utf-8 -*-
from odoo import models, fields, osv , api
from odoo.exceptions import UserError, ValidationError,Warning
import logging
import requests
from decimal import Decimal, ROUND_DOWN

_logger = logging.getLogger(__name__)

"""
    in this code We validate the available quantities and send it to the API.
"""


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    validate_Check_orderline  = fields.Boolean(string='Validar si tiene lineas',compute='_compute_validate_order_line')
    
    amount_untaxed_bs = fields.Monetary(
        string="Base Imponible Bs.", 
        store=True, 
        compute='_compute_amount_untaxed_bs',
        digit=(16,2),
        currency_field='currency_ref_id'
    )
    amount_tax_bs = fields.Monetary(
        string="Impuesto Bs.", 
        store=True, 
        compute='_compute_amount_tax_bs',
        digit=(16,2),
        currency_field='currency_ref_id'
    )

    #amount_untaxed_bs = fields.Float(string="Base Imponible Bs.", store=True, compute='_compute_amounts_bs', tracking=5, digits=(16, 4))
    #amount_tax_bs = fields.Float(string="Impuesto Bs", store=True, compute='_compute_amounts_bs',digits=(16, 4))
    amount_total_bs = fields.Float(string="Total BS", store=True, compute='_compute_amount_total_bs', tracking=4,digits=(16, 2))
    currency_ref_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.ref('base.VEF'),digits=(16, 4))
    amount_residual_bs = fields.Monetary(
        string='Bs. Monto Deudor',
        # compute='_compute_amount_bs', 
        store=True,
        digits=(16, 2)
    )

    
    
    test = fields.Float(string="Base Imponible BS.")
   
    @api.model
    def getRate(self):
        res_currency_id = self.env['res.currency'].sudo().search([('name','=','VEF'),('active','=',True)], limit=1)
        if res_currency_id and res_currency_id.rate_ids:
            rate_day = res_currency_id.rate_ids.sorted('name', reverse=True)[:1]
            return round(rate_day.company_rate , 2) 
        else :
            return   1.00
        
    tax_day  = fields.Float(
        string='Tasa del día',
        default = getRate,
        states = {'sale': [('readonly', True)]},
        digits='Product Price',
    )
    
    
    def calcular_totales_por_impuesto(self):
        impuestos_totales = {}
        totalBaseImponible = 0.00
        for order in self:
            
            for line in order.order_line:
                subtoal_amount_bs = Decimal(str(line.subtoal_amount_bs))
                totalBaseImponible+=line.subtoal_amount_bs
                for impuesto in line.tax_id:
                    if impuesto.amount !=0:#vamos hacer los calculos a distinto Excento
                        impuestod = Decimal(str(impuesto.amount))
                        impuesto_nombre = impuesto.name
                        impuesto_valor = subtoal_amount_bs * impuestod / 100
                        impuesto_valor = impuesto_valor.quantize(Decimal('1.00'), rounding=ROUND_DOWN)
                        if impuesto_nombre in impuestos_totales:
                            impuestos_totales[impuesto_nombre] += impuesto_valor
                        else:
                            impuestos_totales[impuesto_nombre] = impuesto_valor

        return impuestos_totales

    @api.depends('order_line')
    def _compute_validate_order_line(self):
        for rec in self:
            if rec.order_line:
                rec.validate_Check_orderline = False
            else:rec.validate_Check_orderline = True #Si no tiene Valor las lineas del pedido habilita para editar la tasa


    @api.depends('order_line.subtoal_amount_bs', 'order_line.product_id')
    def _compute_amount_untaxed_bs(self):
        for order in self:
            subtotal_amount_bs = Decimal('0.00')
            #rate = Decimal(str(order.tax_day))  # Asumiendo que 'tax_day' es la tasa de cambio

            for line in order.order_line:
                if line.product_id.name != "IGTF":  # Excluir productos con nombre "IGTF"
                    subtotal_amount_bs += Decimal(str(line.subtoal_amount_bs))
            
            order.amount_untaxed_bs = subtotal_amount_bs
    
    @api.depends('order_line.subtoal_amount_bs', 'order_line.tax_id')
    def _compute_amount_tax_bs(self):
        for order in self:
            taxes_amount_bs = Decimal('0.00')

            for line in order.order_line:
                if line.tax_id:  # Verificar si la línea tiene impuestos
                    # Filtrar impuestos con porcentaje mayor a 0
                    for tax in line.tax_id:
                        if tax.amount > 0:
                            # Asegúrate de que el campo subtotal_amount_bs esté correctamente definido y tenga valores válidos
                            if line.subtoal_amount_bs:
                                taxes_amount_bs += Decimal(str(line.subtoal_amount_bs)) * (Decimal(str(tax.amount)) / Decimal('100'))

            order.amount_tax_bs = taxes_amount_bs

    @api.depends('amount_untaxed_bs', 'amount_tax_bs')
    def _compute_amount_total_bs(self):
        for order in self:
            if order.currency_id.name == "USD" and order.tax_day:
                # Sumar amount_untaxed_bs y amount_tax_bs
                order.amount_total_bs = order.amount_untaxed_bs + order.amount_tax_bs
            else:
                order.amount_total_bs = order.amount_total

    def calcular_totales_por_impuesto_USD(self):
        impuestos_totales = {}
        totalBaseImponible = 0.00
        for order in self:
            for line in order.order_line:
                for impuesto in line.tax_id:
                    if impuesto.amount !=0:#vamos hacer los calculos a distinto Excento
                        # logging.info(line.price_subtotal)
                        # logging.info(impuesto.amount)
                        impuesto_nombre = impuesto.name
                        impuesto_valor = (line.price_subtotal * impuesto.amount) / 100
            
                        if impuesto_nombre in impuestos_totales:
                            impuestos_totales[impuesto_nombre] += impuesto_valor
                        else:
                            impuestos_totales[impuesto_nombre] = impuesto_valor

        return impuestos_totales

    def _compute_amounts_line_bs(self):
        for line in self.order_line:
            line._compute_price_unit_bs()   
    def _compute_amount_bs(self):
        for line in self.order_line:
            line._compute_amount_bs()
    def updateRateDate(self):
        for order in self:
         # Forzar el recálculo de los precios en bolívares en cada línea
         for line in order.order_line:
             line._onchange_precio_usd()  # Invocar directamente el método de cambio para actualizar precios
         self._compute_amount_bs()
         self._compute_amounts_line_bs()

class InheritSaleOrder(models.Model):
    _inherit = 'sale.order.line'
    
    currency_ref_id = fields.Many2one(
        'res.currency', 
        string='Moneda Bolivar', 
        default=lambda self: self.env.ref('base.VEF')
    )
    
    price_unit_bs = fields.Monetary(
        string="Bs. Precio", 
        currency_field='currency_ref_id',
        digits=(16, 2),
        store=True, 
        readonly=False, 
        required=True,
        precompute=True,
    )
    
    
    subtoal_amount_bs = fields.Monetary(
        string="Subtotal Bs.",
        currency_field='currency_ref_id' ,
        store=True, 
        precompute=True, 
        tracking=4)    
    
    
    last_changed_field = fields.Selection(
        selection=[('precio_bs', 'Precio Bs.'), ('precio_usd', 'Precio USD'),('primero', 'primero')],
        string='Campo Modificado',
        default='primero'
    )

    active_onchange  = fields.Boolean(string='')

    @api.depends('price_unit_bs', 'product_uom_qty', 'discount')
    def _compute_amount_bs(self):
        for line in self:
            price_unit_bs = Decimal(str(line.price_unit_bs))
            quantity = Decimal(str(line.product_uom_qty))
            discount_percentage = Decimal(str(line.discount)) / Decimal('100')
            
            # Calcular el subtotal bruto en Bs. (sin descuento)
            subtotal_bs_bruto = price_unit_bs * quantity

            # Calcular el monto del descuento en Bs.
            discount_amount_bs = subtotal_bs_bruto * discount_percentage

            # Calcular el subtotal con descuento aplicado
            subtotal_bs_con_descuento = subtotal_bs_bruto - discount_amount_bs

            # Redondear el resultado y asignar
            line.subtoal_amount_bs = subtotal_bs_con_descuento.quantize(Decimal('1.00'), rounding=ROUND_DOWN)
    
    @api.onchange('discount')
    def _onchange_discount(self):
        # Llama a _compute_amount_bs cada vez que el descuento cambie
        self._compute_amount_bs()
                       
    @api.onchange('price_unit', 'order_id.tax_day')
    def _onchange_precio_usd(self):
        logging.info("ONCHANGE 2")
        for line in self:
            if line.price_unit and line.order_id.tax_day:
                # Calcular el precio en bolívares en base al precio en USD y la tasa del día
                line.price_unit_bs = line.price_unit * line.order_id.tax_day
                line.last_changed_field = 'precio_usd'
                line.active_onchange = False  # Aseguramos que solo se calcule una vez

            elif line.product_id and not line.price_unit_bs:
                line.price_unit_bs = line.product_id.list_price  # Asignamos precio por defecto si no hay precio en USD

            elif not line.price_unit:
                line.price_unit_bs = 0.00
            else:
                line.active_onchange = True

    @api.onchange('price_unit_bs', 'order_id.tax_day')
    def _onchange_precio_bs(self):
        logging.info("ONCHANGE 1")
        for line in self:
            if line.price_unit_bs and line.order_id.tax_day:
                # Calcular el precio en USD en base al precio en bolívares y la tasa del día
                line.price_unit = line.price_unit_bs / line.order_id.tax_day
                line.last_changed_field = 'precio_bs'
                line.active_onchange = False  # Aseguramos que solo se calcule una vez

            elif line.product_id and not line.price_unit:
                line.price_unit = line.product_id.list_price  # Asignamos precio por defecto si no hay precio en bolívares

            elif not line.price_unit_bs:
                line.price_unit = 0.00
            else:
                line.active_onchange = True

            
    # @api.depends('price_subtotal')
    # def _compute_amount_bs(self):
    #     for line in self:
    #         price_subtotal = Decimal(str(line.price_subtotal))
    #         tax_day = Decimal(str(line.order_id.tax_day))

    #         if line.price_subtotal and  line.order_id.tax_day:
    #             subtoal_amount_bs = price_subtotal * tax_day
    #             subtoal_amount_bs = subtoal_amount_bs.quantize(Decimal('1.00'), rounding=ROUND_DOWN)
    #             line.subtoal_amount_bs= subtoal_amount_bs
         
    #         else :
    #             line.subtoal_amount_bs = 0.00

    
                
    @api.depends('product_id', 'price_unit',)
    def _compute_price_unit_bs(self):
        for line in self:
            logging.info("Se ejecuto el metodooooooo ")
            price_subtotal = Decimal(str(line.price_unit))
            tax_day = Decimal(str(line.order_id.tax_day))
            
            if line.price_unit and  line.order_id.tax_day:
                price_unit_bs = price_subtotal * tax_day
                price_unit_bs = price_unit_bs.quantize(Decimal('1.00'), rounding=ROUND_DOWN)
                line.price_unit_bs = price_unit_bs
            elif line.product_id:
                line.price_unit_bs = line.product_id.price_bs
            else :
                line.price_unit_bs = 0.00
    
    
    """
    
    
    @api.onchange('price_unit_bs')            
    @api.depends('price_unit_bs')
    def _inverse_price_unit_bs(self):
        for line in self:
            logging.info("INVERSOOOOOOOO")
            if line.price_unit and  line.order_id.tax_day:
                line.price_unit = line.price_unit_bs / line.order_id.tax_day
            elif line.product_id:
                line.price_unit = line.product_id.list_price
            else :
                line.price_unit_bs = 0.00
    """