# -*- coding: utf-8 -*-
from odoo import models, fields, osv , api
from odoo.exceptions import UserError, ValidationError,Warning
import logging
import requests
from decimal import Decimal, ROUND_DOWN, ROUND_UP, ROUND_HALF_UP
_logger = logging.getLogger(__name__)

"""
    in this code We validate the available quantities and send it to the API.
    
"""


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    amount_untaxed_bs = fields.Monetary(
        string="Base Imponible Bs.", 
        store=True, 
        compute='_compute_amount_untaxed_bs',
        currency_field='currency_ref_id'
    )
    amount_tax_bs = fields.Monetary(
        string="Impuesto Bs.", 
        store=True, 
        compute='_compute_amount_tax_bs',
        currency_field='currency_ref_id'
    )
    amount_total_bs = fields.Monetary(
        string="Total Bs.", 
        store=True, 
        compute='_compute_amount_total_bs',
        currency_field='currency_ref_id'
    )
    amount_residual_bs = fields.Monetary(
        string="Monto Deudor Bs.",
        compute='_compute_amount_residual_bs', 
        store=True,
        currency_field='currency_ref_id'
    )
    
    currency_ref_id = fields.Many2one(
        'res.currency', 
        string='Moneda Bolivar', 
        default=lambda self: self.env.ref('base.VEF')
    )

    type_report_currency  = fields.Selection(
            [
                ('usd', 'Dolares.'), 
                ('bs',  'Bolívares'),
                ('usd_bs', 'Dual'),
            ] ,
            default = "usd", 
            string = "Totales en factura (PDF)"
        )
    
    

    price_unit_bs = fields.Monetary(
        string="Bs. Precio", 
        currency_field='currency_ref_id',
        digits='Product Price',
        store=True, 
        readonly=False, 
        required=True,
        precompute=True,
    )

    subtoal_amount_bs = fields.Monetary(
        string="Bs. Subtotal",
        currency_field='currency_ref_id' ,
        store=True, 
        compute='_compute_amounts_bs', 
        tracking=4
    )
        
    related_currency_name  = fields.Char(
        string='moneda del documento',
        related='currency_id.name', readonly=True, store=True, precompute=True)

    
    display_tax_currency = fields.Boolean(string='Mostrar Tasa del día (PDF)', default = True, )
    

    @api.model
    def getRate(self):
        res_currency_id = self.env['res.currency'].sudo().search([('name','=','VEF'),('active','=',True)], limit=1)
        if res_currency_id and res_currency_id.rate_ids:
            rate_day = res_currency_id.rate_ids.sorted('name', reverse=True)[:1]
            tx = Decimal(str(rate_day.company_rate))
            tx_amount = tx.quantize(Decimal('1.00'), rounding=ROUND_DOWN)
            return tx_amount
        else :
            return   4.00
        
    tax_day  = fields.Float(
        string='Tasa del día',
        default = getRate,
        states = {'sale': [('readonly', True)]},
        digits='Product Price',
    )

    @api.depends('invoice_line_ids.price_subtotal', 'invoice_line_ids.product_id')
    def _compute_amount_untaxed_bs(self):
        for move in self:
            subtotal_amount_bs = Decimal('0.00')
            #rate = Decimal(str(move.tax_day))  # Asumiendo que 'tax_day' es la tasa de cambio

            for line in move.invoice_line_ids:
                if line.product_id.name != "IGTF":  # Excluir productos con nombre "IGTF"
                    subtotal_amount_bs += Decimal(str(line.subtoal_amount_bs))
            
            move.amount_untaxed_bs = subtotal_amount_bs
            
    @api.depends('invoice_line_ids.subtoal_amount_bs', 'invoice_line_ids.tax_ids')
    def _compute_amount_tax_bs(self):
        for move in self:
            taxes_amount_bs = Decimal('0.00')

            for line in move.invoice_line_ids:
                if line.tax_ids:  # Verificar si la línea tiene impuestos
                    # Filtrar impuestos con porcentaje mayor a 0
                    for tax in line.tax_ids:
                        if tax.amount > 0:
                            # Sumar el subtotal en bolívares de las líneas con impuestos aplicables
                            taxes_amount_bs += Decimal(str(line.subtoal_amount_bs)) * (Decimal(str(tax.amount)) / Decimal('100'))

            move.amount_tax_bs = taxes_amount_bs

    @api.depends('amount_untaxed_bs', 'amount_tax_bs')
    def _compute_amount_total_bs(self):
        for move in self:
            if move.currency_id.name == "USD" and move.tax_day:
                # Sumar amount_untaxed_bs y amount_tax_bs
                move.amount_total_bs = move.amount_untaxed_bs + move.amount_tax_bs
            else:
                move.amount_total_bs = move.amount_total

    @api.depends('amount_residual', 'tax_day')
    def _compute_amount_residual_bs(self):
        for move in self:
            if move.currency_id.name == "USD" and move.tax_day:
                rate = Decimal(str(move.tax_day))
                move.amount_residual_bs = (Decimal(move.amount_residual) * rate).quantize(Decimal('1.00'), rounding=ROUND_DOWN)
            else:
                move.amount_residual_bs = move.amount_residual if move.amount_residual else 0.00

    @api.model
    def create(self, vals):
        logging.info(vals)
        if vals.get('invoice_origin',False):
            order_id = self.env['sale.order'].search([
                ('name','=',vals.get('invoice_origin')),
                ('company_id','=',self.env.user.company_id.id)
                ])
            if order_id :
                vals.update({'tax_day':order_id.tax_day})
            else:
                order_id = self.env['purchase.order'].search([
                    ('name','=',vals.get('invoice_origin')),
                    ('company_id','=',self.env.user.company_id.id)
                ])
                if order_id :
          
                    vals.update({'tax_day':order_id.tax_day})
                    
        return super(AccountMove, self).create(vals)
    

    #LINEAS DE PEDIDO:
    @api.onchange('price_unit')
    def _onchange_precio_usd(self):
        logging.info("ONCHANGE 2")
        for line in self:
            if line.last_changed_field == 'primero' or line.last_changed_field == 'precio_usd':
                if line.price_unit and line.order_id.tax_day:
                    line.price_unit_bs = line.price_unit * line.order_id.tax_day
                    line.last_changed_field  = 'precio_usd'
                    line.active_onchange = False
                elif line.product_id and not line.price_unit_bs:
                    line.price_unit_bs = line.product_id.list_price
                elif not line.price_unit:
                    line.price_unit_bs = 0.00
       
            elif  line.active_onchange == True:
                if line.price_unit and line.order_id.tax_day:
                    line.price_unit_bs = line.price_unit * line.order_id.tax_day
                    line.last_changed_field  = 'precio_usd'
                elif line.product_id and not line.price_unit_bs:
                    line.price_unit_bs = line.product_id.list_price
                elif not line.price_unit:
                    line.price_unit_bs = 0.00
            else:
                line.active_onchange = True

    @api.onchange('price_unit_bs')
    def _onchange_precio_bs(self):
        logging.info("ONCHANGE 1")
        for line in self:
            if line.last_changed_field == 'primero' or line.last_changed_field == 'precio_bs':
                if line.price_unit_bs and line.order_id.tax_day:
                    line.price_unit = line.price_unit_bs / line.order_id.tax_day
                    line.last_changed_field  = 'precio_bs'
                    line.active_onchange = False
                elif line.product_id and not line.price_unit:
                    line.price_unit = line.product_id.list_price

                elif not line.price_unit_bs:
                    line.price_unit = 0.00
                break
            elif  line.active_onchange == True:
                if line.price_unit_bs and line.order_id.tax_day:
                    line.price_unit = line.price_unit_bs / line.order_id.tax_day
                    line.last_changed_field  = 'precio_bs'
                    
        
                elif line.product_id and not line.price_unit:
                    line.price_unit = line.product_id.list_price

                elif not line.price_unit_bs:
                    line.price_unit = 0.00
                break
            else:
                line.active_onchange = True

    @api.depends('price_unit_bs', 'quantity', 'discount')
    def _compute_amounts_bs(self):
        for line in self:
            price_unit_bs = Decimal(str(line.price_unit_bs))
            quantity = Decimal(str(line.quantity))
            discount_percentage = Decimal(str(line.discount)) / Decimal('100')
            
            # Calcular el subtotal bruto en Bs. (sin descuento)
            subtotal_bs_bruto = price_unit_bs * quantity

            # Calcular el monto del descuento en Bs.
            discount_amount_bs = subtotal_bs_bruto * discount_percentage

            # Calcular el subtotal con descuento aplicado
            subtotal_bs_con_descuento = subtotal_bs_bruto - discount_amount_bs

            # Redondear el resultado y asignar
            line.subtoal_amount_bs = subtotal_bs_con_descuento.quantize(Decimal('1.00'), rounding=ROUND_DOWN)
    ##DEESDE AQUI
    
    def calcular_totales_por_impuesto(self):
        impuestos_totales = {}
        totalBaseImponible = 0.00
        for order in self:
            
            for line in order.invoice_line_ids:
                subtoal_amount_bs = Decimal(str(line.subtoal_amount_bs))
                totalBaseImponible+=line.subtoal_amount_bs
                for impuesto in line.tax_ids:
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
    


    def calcular_totales_por_impuesto_USD(self):
        impuestos_totales = {}
        totalBaseImponible = 0.00
        for order in self:
            for line in order.invoice_line_ids:
                for impuesto in line.tax_ids:
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
    
    """
        Funciona para el libro de ventas y compras
    """

    def calcular_base_imponible_por_impuesto_USD(self):
        impuestos_totales = {}
        for order in self:
            for line in order.invoice_line_ids:
                for impuesto in line.tax_ids:
                    if impuesto.amount !=0:#vamos hacer los calculos a distinto Excento
                        # logging.info(line.price_subtotal)
                        # logging.info(impuesto.amount)
                        impuesto_nombre = impuesto.name
                        impuesto_valor = (line.price_subtotal) 
            
                        if impuesto_nombre in impuestos_totales:
                            impuestos_totales[impuesto_nombre] += impuesto_valor
                        else:
                            impuestos_totales[impuesto_nombre] = impuesto_valor

        return impuestos_totales


    @api.depends(
        'amount_untaxed',
        'amount_tax',
        'amount_total',
        'invoice_line_ids.price_unit_bs',
        'invoice_line_ids.currency_rate',
        'invoice_line_ids.tax_base_amount',
        'invoice_line_ids.tax_line_id',
        'invoice_line_ids.price_total',
        'invoice_line_ids.price_subtotal',
        'invoice_payment_term_id',
        'partner_id',
        'currency_id',
        )
    def _compute_amounts_bs(self):
        for move in self:
            if move.currency_id.name == "USD":
                if move.tax_day > 0:
                    # Utilizar los valores calculados en bolívares directamente si ya están presentes
                    # Asegúrate de que estos campos en bolívares se calculen correctamente en otro lugar
                    amount_untaxed_bs = move.amount_untaxed_bs or 0.00
                    amount_tax_bs = move.amount_tax_bs or 0.00
                    amount_total_bs = move.amount_total_bs or 0.00
                    
                    # Calcular el monto residual en bolívares
                    amount_residual_bs = move.amount_residual_bs or 0.00

                    # Asignar los valores calculados
                    move.amount_untaxed_bs = amount_untaxed_bs
                    move.amount_tax_bs = amount_tax_bs
                    move.amount_total_bs = amount_total_bs
                    move.amount_residual_bs = amount_residual_bs
                else:
                    # Si no hay tasa de cambio, establecer los montos en bolívares en 0
                    move.amount_untaxed_bs = 0.00
                    move.amount_tax_bs = 0.00
                    move.amount_total_bs = 0.00
                    move.amount_residual_bs = 0.00
            else:
                # Cuando la moneda no es USD, utilizar los valores originales
                move.amount_untaxed_bs = move.amount_untaxed
                move.amount_tax_bs = move.amount_tax
                move.amount_total_bs = move.amount_total
                move.amount_residual_bs = move.amount_residual or 0.00
    #BOTONES
    
    def _compute_amounts_line_bs(self):
        for line in self.invoice_line_ids:
            line._compute_price_unit_bs_update(line)
            
            
    def updateRateDate(self):
        self._compute_amounts_bs()
        self._compute_amounts_line_bs()
        

    #FIN AQUI

class InheritMoveLine(models.Model):
    _inherit = 'account.move.line'
    
    currency_ref_id = fields.Many2one(
        'res.currency', 
        string='Moneda de Referencial', 
        default=lambda self: self.env.ref('base.VEF')
    )

    price_unit_bs = fields.Monetary(
        string="Bs. Precio", 
        currency_field='currency_ref_id',
        compute='_compute_price_unit_bs',
        digits='Product Price',
        store=True, 
        readonly=False, 
        required=True,
        precompute=True,
    
    )

    subtoal_amount_bs = fields.Monetary(
        string="Bs. Subtotal",
        currency_field='currency_ref_id' ,
        store=True, 
        compute='_compute_amounts_bs', 
        tracking=4)   



    related_tax_day  = fields.Float(
        string='Tasa del día',
        related='move_id.tax_day', readonly=True, store=True, precompute=True,digits=(16, 3)

    )
    
    
    related_currency_id  = fields.Char(
        string='moneda del documento',
        related='move_id.currency_id.name', readonly=True, store=True, precompute=True)
    
    currency_ref_id = fields.Many2one(
        'res.currency', 
        string='Moneda Bolivar', 
        default=lambda self: self.env.ref('base.VEF')
    )
    
    last_changed_field = fields.Selection(
        selection=[('precio_bs', 'Precio Bs.'), ('precio_usd', 'Precio USD'),('primero', 'primero')],
        string='Campo Modificado',
        default='primero'
    )
    
    active_onchange  = fields.Boolean(string='')
    
    @api.depends('price_unit_bs', 'quantity', 'discount', 'move_id.currency_id', 'move_id.tax_day')
    def _compute_amounts_bs(self):
        for line in self:
            if line.move_id.currency_id.name == "USD":
                price_unit_bs = Decimal(str(line.price_unit_bs))
                quantity = Decimal(str(line.quantity))
                discount_percentage = Decimal(str(line.discount)) / Decimal('100')

                if price_unit_bs and quantity:
                    # Calcular el subtotal bruto en Bs. (sin descuento)
                    subtotal_bs_bruto = price_unit_bs * quantity
                    
                    # Calcular el monto del descuento en Bs.
                    discount_amount_bs = subtotal_bs_bruto * discount_percentage
                    
                    # Calcular el subtotal con descuento aplicado
                    subtotal_bs_con_descuento = subtotal_bs_bruto - discount_amount_bs
                    
                    # Redondear el resultado y asignar
                    line.subtoal_amount_bs = subtotal_bs_con_descuento.quantize(Decimal('1.00'), rounding=ROUND_DOWN)
                else:
                    line.subtoal_amount_bs = 0.00
            else:
                # Cuando la moneda no es USD, utiliza el subtotal en la moneda local (si es necesario)
                line.subtoal_amount_bs = line.price_subtotal


    def _compute_price_unit_bs_update(self,line):
            price_subtotal = Decimal(str(line.price_unit))
            tax_day = Decimal(str(line.move_id.tax_day))  
            if line.price_unit and  line.move_id.tax_day:
                price_unit_bs = price_subtotal * tax_day
                price_unit_bs = price_unit_bs.quantize(Decimal('1.000'), rounding=ROUND_HALF_UP)
                line.price_unit_bs = float(price_unit_bs)
            elif line.product_id:
                line.price_unit_bs = line.product_id.price_bs
            else :
                line.price_unit_bs = 0.00
                
                
    @api.depends('product_id', 'price_unit',)
    def _compute_price_unit_bs(self):
        for line in self:
            if line.move_id.currency_id.name == "USD":
                if line.price_unit and  line.move_id.tax_day:
                    price_unit = Decimal(str(line.price_unit))
                    tax_day = Decimal(str(line.move_id.tax_day))
                    price_unit_bs = price_unit * tax_day
                    price_unit_bs = price_unit_bs.quantize(Decimal('1.000'), rounding=ROUND_HALF_UP)
                    line.price_unit_bs = price_unit_bs
                elif line.product_id:
                    line.price_unit_bs = line.product_id.price_bs
                else :
                    line.price_unit_bs = 0.000
            else:
                line.price_unit_bs = line.price_unit
                      