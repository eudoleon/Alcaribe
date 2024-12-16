/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";

const { Component } = owl;

export class BankRecWidgetFormRecoModelsWidget extends Component {
    setup() {
        super.setup();
        this.actionService = useService("action");
    }

    get record() {
        return this.env.model.root;
    }

    /** Create the data to render the template **/
    getRenderValues(){
        return this.record.data.reco_models_widget;
    }

    /** The user clicked on a reco model. **/
    async selectRecoModel(reco_model_id, already_selected){
        if (already_selected) {
            this.record.update({ todo_command: `unselect_reconcile_model_button,${reco_model_id}`});
        } else {
            await this.record.update({ todo_command: `select_reconcile_model_button,${reco_model_id}`});

            const line_index = this.record.data.lines_widget.lines.slice(-1)[0].index.value;
            await this.record.update({todo_command: `mount_line_in_edit,${line_index}`});
        }
    }

    /** The user clicked to quickly create a new reco model. **/
    async _onClickCreateReconciliationModel(ev) {
        const propositions_for_model = [];
        const lines = this.record.data.lines_widget.lines;

        const total = lines.filter(line => line.flag.value === 'liquidity')[0].balance.value;
        let rest = total;
        for (const line of lines) {
            let base_amount;
            if (line.flag.value !== 'manual') continue;
            if (line.tax_ids && line.tax_ids.length > 0)
            {
                base_amount = -line.tax_base_amount_currency;
            } else {
                base_amount = -line.balance.value;
            }
            propositions_for_model.push([0, 0, {
                label: line.name.value,
                amount: line.balance.value,
                account_id: line.account_id.id,
                tax_ids: [[6, 0, line.tax_ids.ids]],
                amount_type: 'percentage',
                amount_string: ((base_amount/rest) * 100).toFixed(5)
            }]);
            rest -= base_amount;
        }

        return this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "account.reconcile.model",
            views: [[false, "form"]],
            target: "current",
            context: {
                default_match_journal_ids: this.record.data.journal_id,
                default_line_ids: propositions_for_model,
                default_to_check: this.record.data.to_check,
            },
        });
    }

}

BankRecWidgetFormRecoModelsWidget.template = "account_accountant.bank_rec_widget_form_reco_models_widget";
BankRecWidgetFormRecoModelsWidget.components = { Dropdown, DropdownItem };

registry.category("fields").add("bank_rec_widget_form_reco_models_widget", BankRecWidgetFormRecoModelsWidget);
