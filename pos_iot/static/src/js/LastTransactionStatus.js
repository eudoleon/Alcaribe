odoo.define('pos_iot.LastTransactionStatus', function(require) {
    'use strict';

    const core = require('web.core');
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    var { Gui } = require('point_of_sale.Gui');

    const { useState } = owl;
    const _t = core._t;

    /**
     * Last Transaction Status Button
     *
     * Retrieve the status of the last transaction processed by the connected
     * Worldline payment terminal and opens a popup to display the result.
     */
    class LastTransactionStatusButton extends PosComponent {
        setup() {
            this.state = useState({ pending: false });

            // Precompute the worldline payment methods values

            // An IoT box can only support one WorldLine payment terminal
            // However, several payment method can use the same terminal (eco/meal vouchers for instance)
            // In some cases, there is no need to perform several call to the same IoT and might cause errors
            this.worldline_payment_method_terminals = [];
            const worldlineTerminalIoT = new Set();

            this.env.pos.payment_methods.filter(pm => pm.use_payment_terminal === 'worldline').forEach(worldline_pm => {
                const terminal = worldline_pm.payment_terminal && worldline_pm.payment_terminal.get_terminal();
                const terminalIoTIP = terminal && terminal._iot_ip;
                if (terminal && terminalIoTIP && !worldlineTerminalIoT.has(terminalIoTIP)) {
                    this.worldline_payment_method_terminals.push(terminal);
                    worldlineTerminalIoT.add(terminalIoTIP);
                }
            });

        }

        sendLastTransactionStatus() {
            if (this.state.pending)
                return;

            if (this.env.pos.get_order() && this.env.pos.get_order().selected_paymentline &&
                ['waiting', 'waitingCard', 'waitingCancel'].includes(this.env.pos.get_order().selected_paymentline.payment_status)) {
    
                Gui.showPopup('ErrorPopup',{
                    'title': _t('Electronic payment in progress'),
                    'body': _t('You cannot check the status of the last transaction when a payment in in progress.'),
                });
                return;
            }

            this.state.pending = true;
            if (this.worldline_payment_method_terminals.length === 0) {
                this.state.pending = false;
                Gui.showPopup('ErrorPopup',{
                    'title': _t('No worldline terminal configured'),
                    'body': _t('No worldline terminal device configured for any payment methods. ' +
                        'Double check if your configured payment method define the field Payment Terminal Device')
                });
            }
            else {
                this.worldline_payment_method_terminals.forEach(worldline_terminal => {
                    worldline_terminal.add_listener(this._onLastTransactionStatus.bind(this));
                    worldline_terminal.action({messageType: 'LastTransactionStatus'}).catch(() => {
                        this.state.pending = false;
                    });
                });
            }
        }

        _onLastTransactionStatus (data) {
            // If the response data has a cid,
            // it's not a response to a Last Transaction Status request
            if (data.cid)
                return;

            this.state.pending = false;

            if (data.Error) {
                Gui.showPopup('ErrorPopup',{
                    'title': _t('Failed to request last transaction status'),
                    'body': data.Error,
                });
            }
            else {
                Gui.showPopup('LastTransactionPopup', data.value);
            }
        }
    }
    LastTransactionStatusButton.template = 'LastTransactionStatusButton';
    Registries.Component.add(LastTransactionStatusButton);

    /**
     * Last Transaction Popup
     *
     * Displays the result of the last transaction processed by the connected
     * Worldline payment terminal
     */
    class LastTransactionPopup extends AbstractAwaitablePopup { }
    LastTransactionPopup.template = 'LastTransactionPopup';
    LastTransactionPopup.defaultProps = { cancelKey: false };
    Registries.Component.add(LastTransactionPopup);

    return {
        LastTransactionStatusButton: LastTransactionStatusButton,
        LastTransactionPopup: LastTransactionPopup,
    };
});
