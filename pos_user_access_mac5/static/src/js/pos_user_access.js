odoo.define('pos_user_access.pos_user_access', function (require) {
"use strict";

const HeaderButton = require('point_of_sale.HeaderButton');
const NumberBuffer = require('point_of_sale.NumberBuffer');
const NumpadWidget = require('point_of_sale.NumpadWidget');
const ProductScreen = require('point_of_sale.ProductScreen');
const Registries = require('point_of_sale.Registries');
const TicketScreen = require('point_of_sale.TicketScreen');


const PosUserAccessHeaderButton = (HeaderButton) =>
    class extends HeaderButton {
        onClick() {
            var user = this.env.pos.user;
            if (!user.pos_access_close) {
                this.showPopup('ErrorPopup', {
                    title: this.env._t('Access Denied'),
                    body: this.env._t('You do not have access to close a POS!'),
                });
            } else {
                super.onClick();
            }
        }
    };


const PosUserAccessNumpadWidget = (NumpadWidget) =>
    class extends NumpadWidget {
        changeMode(mode) {
            var user = this.env.pos.user;
            if (mode === 'price' && !user.pos_access_price) {
                this.showPopup('ErrorPopup', {
                    title: this.env._t('Access Denied'),
                    body: this.env._t('You do not have access to change price!'),
                });
            } else if (mode === 'discount' && !user.pos_access_discount) {
                this.showPopup('ErrorPopup', {
                    title: this.env._t('Access Denied'),
                    body: this.env._t('You do not have access to apply discount!'),
                });
            } else {
                super.changeMode(mode);
            }
        }
    };


const PosUserAccessProductScreen = (ProductScreen) =>
    class extends ProductScreen {
        _setValue(val) {
            var newQty = NumberBuffer.get() ? parseFloat(NumberBuffer.get()) : 0;
            var orderLines = !!this.currentOrder ? this.currentOrder.get_orderlines() : undefined;
            if (orderLines !== undefined && orderLines.length > 0) {
                var currentOrderLine = this.currentOrder.get_selected_orderline();
                var currentQty = this.currentOrder.get_selected_orderline().get_quantity();
                var user = this.env.pos.user;
                if (currentOrderLine && this.env.pos.numpadMode === 'quantity' && newQty < currentQty && !user.pos_access_decrease_quantity) {
                    this.showPopup('ErrorPopup', {
                        title: this.env._t('Access Denied'),
                        body: this.env._t('You do not have access to decrease the quantity of an order line!'),
                    });
                } else if (currentOrderLine && this.env.pos.numpadMode === 'quantity' && val === 'remove' && !user.pos_access_delete_orderline) {
                    this.showPopup('ErrorPopup', {
                        title: this.env._t('Access Denied'),
                        body: this.env._t('You do not have access to delete an order line!'),
                    });
                } else {
                    super._setValue(val)
                }
            } else {
                super._setValue(val)
            }
        }

        _onClickPay() {
            var user = this.env.pos.user;
            if (!user.pos_access_payment) {
                this.showPopup('ErrorPopup', {
                    title: this.env._t('Access Denied'),
                    body: this.env._t('You do not have access to apply payment!'),
                });
            } else {
                super._onClickPay();
            }
        }

    };


const PosUserAccessTicketScreen = (TicketScreen) =>
    class extends TicketScreen {
        async _onDeleteOrder({ detail: order }) {
            var user = this.env.pos.user;
            if (!user.pos_access_delete_order) {
                await this.showPopup('ErrorPopup', {
                    title: this.env._t('Access Denied'),
                    body: this.env._t('You do not have access to delete an order!'),
                });
            } else {
                await super._onDeleteOrder({ detail: order });
            }
        }
    };


Registries.Component.extend(HeaderButton, PosUserAccessHeaderButton);
Registries.Component.extend(NumpadWidget, PosUserAccessNumpadWidget);
Registries.Model.extend(PosGlobalState, PosUserAccessPosGlobalState);
Registries.Component.extend(ProductScreen, PosUserAccessProductScreen);
Registries.Component.extend(TicketScreen, PosUserAccessTicketScreen);

});
