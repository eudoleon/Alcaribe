odoo.define('pos_blackbox_be.RefundButton', function (require) {
    'use strict';

    const Chrome = require('point_of_sale.RefundButton');
    const Registries = require('point_of_sale.Registries');

    const PosBlackboxBeRefundButton = (Chrome) =>
        class extends Chrome {
            _onClick() {
                if (this.env.pos.useBlackBoxBe() && !this.env.pos.checkIfUserClocked()) {
                    this.showPopup('ErrorPopup',{
                        'title': this.env._t("POS error"),
                        'body':  this.env._t("User must be clocked in."),
                    });
                    return;
                }
                return super._onClick();
            }
        };

    Registries.Component.extend(Chrome, PosBlackboxBeRefundButton);

    return Chrome;
});
