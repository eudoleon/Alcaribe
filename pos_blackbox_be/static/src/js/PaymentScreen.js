odoo.define('pos_blackbox_be.PaymentScreen', function(require) {
    "use strict";

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');

    const PosBlackboxBePaymentScreen = PaymentScreen => class extends PaymentScreen {
        //@Override
        async validateOrder(isForceValidate) {
            if (this.env.pos.useBlackBoxBe() && !this.env.pos.checkIfUserClocked()) {
                this.showPopup('ErrorPopup',{
                    'title': this.env._t("POS error"),
                    'body':  this.env._t("User must be clocked in."),
                });
                return;
            }
            await super.validateOrder(...arguments);
        }
        openCashbox() {
            this.rpc({
                model: 'pos.session',
                method: 'increase_cash_box_opening_counter',
                args: [this.env.pos.pos_session.id]
            })
            super.openCashbox(...arguments);
        }
    };

    Registries.Component.extend(PaymentScreen, PosBlackboxBePaymentScreen);

    return PosBlackboxBePaymentScreen;
});
