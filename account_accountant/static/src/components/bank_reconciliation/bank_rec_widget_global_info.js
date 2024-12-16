/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component, onWillStart, useState } = owl;

export class BankRecWidgetGlobalInfo extends Component {
    setup() {
        this.bankRecService = useService("bank_rec_widget");
        this.kanbanState = useState(this.bankRecService.kanbanState);
        this.state = useState({
            data: {},
        })
        this.orm = useService("orm");

        onWillStart(this.fetchData);

        this.bankRecService.useTodoCommand("globalinfo-refresh", () => this.fetchData());
    }

    /** Fetch the data to display. **/
    async fetchData() {
        this.state.data = await this.orm.call("bank.rec.widget",
            "collect_global_info_data",
            ["", this.kanbanState.currentJournalId],
            {},
        );
    }

    /** Open the bank reconciliation report. **/
    async openReport() {
        const actionData = await this.orm.call(
            "bank.rec.widget",
            "action_open_bank_reconciliation_report",
            ['', this.kanbanState.currentJournalId],
            {}
        );
        this.bankRecService.trigger("kanban-do-action", actionData);
    }

}
BankRecWidgetGlobalInfo.template = "account_accountant.BankRecWidgetGlobalInfo";

registry.category("fields").add("bank_rec_widget_global_info", BankRecWidgetGlobalInfo);
