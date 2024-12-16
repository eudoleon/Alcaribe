/** @odoo-module **/

import { Orderline, Order, Product, Payment } from "point_of_sale.models";
import Registries from "point_of_sale.Registries";
var utils = require('web.utils');
var round_di = utils.round_decimals;

Registries.Model.extend(Product, (Parent) => class extends Parent {
    get isIgtfProduct() {
        const { x_igtf_product_id } = this.pos.config;

        return (x_igtf_product_id)
            ? x_igtf_product_id[0] === this.id
            : false;
    }
});

Registries.Model.extend(Payment, (Parent) => class extends Parent {
    get isForeignExchange() {
        return this.payment_method.x_is_foreign_exchange;
    }

    set_amount(value){
        var igtf_antes = this.order.x_igtf_amount;

        if(value == this.order.get_due()){
            super.set_amount(value);
        }else{
            if(value != igtf_antes){
                if(this.isForeignExchange){
                    super.set_amount(value * (1/this.pos.config.show_currency_rate));
                }else{
                    super.set_amount(value);
                }
            }
        }


        const igtfProduct = this.pos.config.x_igtf_product_id;
        if(!(igtfProduct || igtfProduct?.length)) return;
        if(!this.isForeignExchange) return;

        if(value == igtf_antes) return;
        this.order.removeIGTF();

        const price = this.order.x_igtf_amount;

        this.order.add_product(this.pos.db.product_by_id[igtfProduct[0]], {
            quantity: 1,
            price,
            lst_price: price,
        });
    }
});

Registries.Model.extend(Orderline, (Parent) => class extends Parent {
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);

        this.x_is_igtf_line = json.x_is_igtf_line;
    }
    
    export_as_JSON() {
        const result = super.export_as_JSON();

        result.x_is_igtf_line = this.x_is_igtf_line;

        return result;
    }

    export_for_printing() {
        const json = super.export_for_printing(...arguments);
        
        json.x_is_igtf_line =  this.x_is_igtf_line;

        return json;
      }
});

Registries.Model.extend(Order, (Parent) => class extends Parent {
    get x_igtf_amount() {
        var igtf_monto = this.paymentlines
            .filter((p) => p.isForeignExchange)
            .map(({ amount, payment_method: { x_igtf_percentage } }) => Math.min(this.get_total_with_tax(), amount) * (x_igtf_percentage / 100))
            .reduce((prev, current) => prev + current, 0);
        return round_di(parseFloat(igtf_monto) || 0, this.pos.currency.decimal_places);
    }

    removeIGTF() {
        this.orderlines
            .filter(({ x_is_igtf_line }) => x_is_igtf_line)
            .forEach((line) => this.remove_orderline(line));
    }

    set_orderline_options(orderline, options) {
        super.set_orderline_options(orderline, options);

        orderline.x_is_igtf_line = orderline.product.isIgtfProduct;
    }
});