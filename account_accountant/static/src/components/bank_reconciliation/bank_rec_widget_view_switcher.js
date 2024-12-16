/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component } = owl;

export class BankRecWidgetViewSwitcher extends Component {
    setup() {
        this.action = useService("action");
        this.bankRecService = useService("bank_rec_widget");
    }

    /** Called when the Match/View button is clicked. **/
    switchView() {
        // Add a new search facet to restrict the results to the selected statement line.
        const searchItem = Object.values(this.env.searchModel.searchItems).find((i) => i.fieldName === "statement_line_id");
        const stLineId = this.props.record.data.id;
        const autocompleteValue = {
            label: this.props.record.data.move_id[1],
            operator: "=",
            value: stLineId,
        }
        this.env.searchModel.addAutoCompletionValues(searchItem.id, autocompleteValue);

        // Switch to the kanban.
        this.action.switchView("kanban", {selectedStLineId: stLineId});
    }

    /** Give the button's label for the current record. **/
    get buttonLabel() {
        return this.props.record.data.is_reconciled ? this.env._t("View") : this.env._t("Match");
    }
}
BankRecWidgetViewSwitcher.template = "account_accountant.BankRecWidgetViewSwitcher";

registry.category("fields").add('bank_rec_widget_view_switcher', BankRecWidgetViewSwitcher);
