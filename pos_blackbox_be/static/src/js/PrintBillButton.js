odoo.define('pos_blackbox_be.PrintBillButton', function(require) {
    'use strict';

    const PrintBillButton = require('pos_restaurant.PrintBillButton');
    const Registries = require('point_of_sale.Registries');

    const PosBlackBoxPrintBillButton = PrintBillButton => class extends PrintBillButton {
        async onClick() {
            const order = this.env.pos.get_order();
            if (this.env.pos.useBlackBoxBe() && order.get_orderlines().length > 0) {
                await this.env.pos.pushProFormaOrder(order);
            }
            await super.onClick();
        }
    };

    Registries.Component.extend(PrintBillButton, PosBlackBoxPrintBillButton);

    return PrintBillButton;
 });
