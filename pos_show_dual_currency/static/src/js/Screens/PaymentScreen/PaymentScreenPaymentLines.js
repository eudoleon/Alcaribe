odoo.define('pos_show_dual_currency.PaymentScreenPaymentLinesDual', function(require) {
    'use strict';

    const PaymentScreenPaymentLines = require('point_of_sale.PaymentScreenPaymentLines');
    const Registries = require('point_of_sale.Registries');

    const PaymentScreenPaymentLinesDual = (PaymentScreenPaymentLines) =>
        class extends PaymentScreenPaymentLines {
            formatLineAmountUsd(line) {
                return this.env.pos.format_currency_no_symbol(line.get_amount() * this.env.pos.config.show_currency_rate);
            }
        };

    Registries.Component.extend(PaymentScreenPaymentLines, PaymentScreenPaymentLinesDual);

    return PaymentScreenPaymentLinesDual;
});
