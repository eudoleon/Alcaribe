odoo.define('pos_show_dual_currency.PaymentScreen', function(require) {
    'use strict';

    const NumberBuffer = require('point_of_sale.NumberBuffer');

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');

    /*const PosShowDualCurrencyPaymentScreen = (PaymentScreen) =>
        class extends PaymentScreen {
            constructor() {
                super(...arguments);
            }

            _updateSelectedPaymentline() {
                if(this.selectedPaymentLine && !this.selectedPaymentLine.payment_method.is_dollar_payment){
                    super._updateSelectedPaymentline()
                }
                else{
                    if (this.paymentLines.every((line) => line.paid)) {
                        this.currentOrder.add_paymentline(this.env.pos.payment_methods[0]);
                    }
                    if (!this.selectedPaymentLine) return; // do nothing if no selected payment line
                    // disable changing amount on paymentlines with running or done payments on a payment terminal
                    if (
                        this.payment_interface &&
                        !['pending', 'retry'].includes(this.selectedPaymentLine.get_payment_status())
                    ) {
                        return;
                    }
                    if (NumberBuffer.get() === null) {
                        this.deletePaymentLine({ detail: { cid: this.selectedPaymentLine.cid } });
                    } else {
                        let val= NumberBuffer.getFloat()
                        val= val* this.env.pos.config.show_currency_rate_real;
                        this.selectedPaymentLine.set_amount(val);
                    }

                }
            }
        };

    Registries.Component.extend(PaymentScreen, PosShowDualCurrencyPaymentScreen);

    return PaymentScreen;*/
});
