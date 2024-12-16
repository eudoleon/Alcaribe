odoo.define('pos_blackbox_be.chrome', function (require) {
    'use strict';

    const Chrome = require('point_of_sale.Chrome');
    const Registries = require('point_of_sale.Registries');

    const PosBlackboxBeChrome = (Chrome) =>
        class extends Chrome {
            showCashMoveButton() {
                 return super.showCashMoveButton() && !this.env.pos.useBlackBoxBe();
            }
        };

    Registries.Component.extend(Chrome, PosBlackboxBeChrome);

    return Chrome;
});
