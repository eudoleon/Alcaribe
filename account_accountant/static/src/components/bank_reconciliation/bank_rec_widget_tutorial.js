/** @odoo-module **/

import { Component, useState } from "@odoo/owl";

export class BankRecTutorial extends Component {
    setup() {
        this.state = useState({
            activeStepIndex: 0,
        })
    }
}
BankRecTutorial.template = "account_accountant.BankRecTutorial";
BankRecTutorial.props = {
    title: { type: String },
    subtitle: { type: String },
    contentTemplate: { type: String },
    demoTemplate: { type: String },
    steps: { type: Array },
}
