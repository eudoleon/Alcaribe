odoo.define('pos_blackbox_be.ReprintReceiptButton', function(require) {
    'use strict';

    const ReprintReceiptButton = require('point_of_sale.ReprintReceiptButton');
    const Registries = require('point_of_sale.Registries');
    const contexts = require('point_of_sale.PosContext');
    const { useState } = owl;

    const PosBlackboxBeReprintReceiptButton = ReprintReceiptButton =>
        class extends ReprintReceiptButton {
            constructor() {
                super(...arguments);
                this.orderManagementContext = useState(contexts.orderManagement);
            }

            async _onClick() {
                if (this.env.pos.useBlackBoxBe()) {
                    this.showPopup('ErrorPopup', {
                        title: this.env._t("Fiscal Data Module Restriction"),
                        body: this.env._t("You are not allowed to reprint a ticket when using the fiscal data module."),
                    });
                    return;
                }
                super._onClick();
            }
        };

    Registries.Component.extend(ReprintReceiptButton, PosBlackboxBeReprintReceiptButton);

    return PosBlackboxBeReprintReceiptButton;
});
