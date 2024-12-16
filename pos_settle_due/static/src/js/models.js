odoo.define('pos_settle_due.models', function (require) {
"use strict";

var { PosGlobalState } = require('point_of_sale.models');
const Registries = require('point_of_sale.Registries');

const PoSSettleDuePosGlobalState = (PosGlobalState) => class PoSSettleDuePosGlobalState extends PosGlobalState {

    async refreshTotalDueOfPartner(partner) {
        const total_due = await this.env.services.rpc({
            model: 'res.partner',
            method: 'get_total_due',
            args: [partner.id, this.env.pos.config.currency_id[0]]
        });
        partner.total_due = total_due;
        this.db.update_partners([partner]);
        return [partner];
    }
};
Registries.Model.extend(PosGlobalState, PoSSettleDuePosGlobalState);
});
