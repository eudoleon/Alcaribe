odoo.define('pos_blackbox_be.TicketScreen', function(require) {
    "use strict";

    const TicketScreen = require('point_of_sale.TicketScreen');
    const Registries = require('point_of_sale.Registries');
    const NumberBuffer = require('point_of_sale.NumberBuffer');

    const PosBlackboxBeTicketScreen = TicketScreen => class extends TicketScreen {
        _onUpdateSelectedOrderline({ detail }) {
            if (this.env.pos.useBlackBoxBe()) {
                const order = this.getSelectedSyncedOrder();
                if (!order) return NumberBuffer.reset();

                const selectedOrderlineId = this.getSelectedOrderlineId();
                const orderline = order.orderlines.find((line) => line.id == selectedOrderlineId);
                if (!orderline) return NumberBuffer.reset();
                if (orderline.product.id === this.env.pos.workOutProduct.id || orderline.product.id === this.env.pos.workInProduct.id) {
                    this.showPopup('ErrorPopup', {
                        title: this.env._t('Fiscal Error'),
                        body: this.env._t("You are not allowed to refund this product")
                    });
                    return;
                }
            }
            super._onUpdateSelectedOrderline({ detail });
        }
        shouldHideDeleteButton(order) {
            return (
                (this.env.pos.useBlackBoxBe() && (this.isDefaultOrderEmpty(order) ||
                order.locked ||
                order
                    .get_paymentlines()
                    .some(
                    (payment) =>
                        payment.is_electronic() &&
                        payment.get_payment_status() === "done"))
                || !order.is_empty())
                || super.shouldHideDeleteButton(order));
        }
    };

    Registries.Component.extend(TicketScreen, PosBlackboxBeTicketScreen);

    return PosBlackboxBeTicketScreen;
});
