odoo.define('pos_blackbox_be.SplitBillScreen', function(require) {
    "use strict";

    const SplitBillScreen = require('pos_restaurant.SplitBillScreen');
    const Registries = require('point_of_sale.Registries');

    const PosBlackboxBeSplitBillScreen = SplitBillScreen => class extends SplitBillScreen {
        get disallow() {
            return super.disallow || this.env.pos.useBlackBoxBe();
        }
    }

    Registries.Component.extend(SplitBillScreen, PosBlackboxBeSplitBillScreen);

    return SplitBillScreen;
});
