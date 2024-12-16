odoo.define('pos_show_dual_currency.TRM', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    // Previously UsernameWidget
    class TRM extends PosComponent {
        get trm() {
            return this.env.pos.format_currency_no_symbol(1 / this.env.pos.config.show_currency_rate);
        }
    }
    TRM.template = 'TRM';

    Registries.Component.add(TRM);

    return TRM;
});
