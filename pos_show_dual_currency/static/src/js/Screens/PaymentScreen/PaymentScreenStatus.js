odoo.define('pos_show_dual_currency.PaymentScreenStatusDual', function(require) {
    'use strict';

    const PaymentScreenStatus = require('point_of_sale.PaymentScreenStatus');
    const Registries = require('point_of_sale.Registries');

    const PaymentScreenStatusDual = (PaymentScreenStatus) =>
        class extends PaymentScreenStatus {
            get remainingTextUSD() {
                return this.env.pos.format_currency_no_symbol(
                    this.props.order.get_due() > 0 ? (this.props.order.get_due() * this.env.pos.config.show_currency_rate) : 0
                );
            }
            get changeTextUSD() {
                return this.env.pos.format_currency_no_symbol(this.props.order.get_change() * this.env.pos.config.show_currency_rate);
            }
        };

    Registries.Component.extend(PaymentScreenStatus, PaymentScreenStatusDual);

    return PaymentScreenStatusDual;
});
