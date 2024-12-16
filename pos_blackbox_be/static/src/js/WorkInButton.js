odoo.define('pos_blackbox_be.WorkInButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require("@web/core/utils/hooks");
    const Registries = require('point_of_sale.Registries');

    const { useState, onWillStart } = owl;

    class WorkInButton extends PosComponent {
        setup() {
            super.setup();
            useListener('click', this.onClick);
            this.state = useState({ status: false, buttonDisabled: false });

            onWillStart(async () => {
                this.state.status= await this.getUserSessionStatus(this.env.pos.pos_session.id, this.env.pos.get_cashier().id)
            });
        }
        async onClick() {
            if (this.env.pos.get_order().orderlines.length) {
                this.showPopup('ErrorPopup', {
                    title: this.env._t("Fiscal Data Module error"),
                    body: this.env._t("Cannot clock in/out if the order is not empty"),
                });
                return;
            }
            const clocked = await this.getUserSessionStatus(this.env.pos.pos_session.id, this.env.pos.get_cashier().id);
            if (!this.state.status && !clocked) {
                this.ClockIn();
             }
            if (this.state.status && clocked) {
                this.ClockOut();
            }
        }
        async ClockIn() {
            this.state.buttonDisabled = true;

            try {
                await this.createOrderForClocking();
                await this.setUserSessionStatus(this.env.pos.pos_session.id, this.env.pos.get_cashier().id, true);
                this.state.status = true;
                this.showScreen('ReceiptScreen');
            } catch (err) {
                console.log(err);
            }
            this.state.buttonDisabled = false;
        }
        async ClockOut() {
            this.state.buttonDisabled = true;
            const unpaidTables = this.env.pos.db.load('unpaid_orders', []).filter(order => order.data.amount_total > 0).map(order => order.data.table);
            if (unpaidTables.length > 0) {
                this.showPopup('ErrorPopup', {
                    title: this.env._t("Fiscal Data Module error"),
                    body: this.env._t("Tables still have unpaid orders. You will not be able to clock out until all orders have been paid."),
                });
                return;
            }

            try {
                await this.createOrderForClocking();
                await this.setUserSessionStatus(this.env.pos.pos_session.id, this.env.pos.get_cashier().id, false);
                this.state.status = false;
                this.showScreen('ReceiptScreen');
            } catch (err) {
                console.log(err);
            }

            this.state.buttonDisabled = false;
        }
        async setUserSessionStatus(session, user, status) {
            const users = await this.rpc({
                model: 'pos.session',
                method: 'set_user_session_work_status',
                args: [session, user, status],
            });
            if (this.env.pos.config.module_pos_hr) {
                this.env.pos.pos_session.employees_clocked_ids = users;
            } else {
                this.env.pos.pos_session.users_clocked_ids = users;
            }
        }
        async getUserSessionStatus(session, user) {
            return await this.rpc({
                model: 'pos.session',
                method: 'get_user_session_work_status',
                args: [session, user],
            });
        }
        async createOrderForClocking() {
            const order = this.env.pos.get_order();
            order.add_product(this.state.status ? this.env.pos.workOutProduct : this.env.pos.workInProduct, {force: true});
            order.draft = false;
            order.clock = this.state.status ? 'out' : 'in';

            await this.env.pos.push_single_order(order);
            order.finalized = true;
            this.env.pos.db.remove_unpaid_order(order);
        }
    }
    WorkInButton.template = 'WorkInButton';

    ProductScreen.addControlButton({
        component: WorkInButton,
        condition: function() {
            return this.env.pos.useBlackBoxBe();
        },
    });

    Registries.Component.add(WorkInButton);

    return WorkInButton;
});
