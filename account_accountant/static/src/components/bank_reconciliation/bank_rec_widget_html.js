/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component } = owl;

export class BankRecWidgetHTML extends Component {
    async setup() {
        super.setup();

        this.bankRecService = useService("bank_rec_widget");
    }

    async handleButtonsClicks(ev) {
        if (ev.target.tagName === "BUTTON" && ev.target.attributes && ev.target.attributes.type.value === "object") {
            const method_name = ev.target.attributes.name.value;
            const method_params = ev.target.attributes.method_args ? `,${JSON.parse(ev.target.attributes.method_args.value).join()}` : "";

            const record = this.env.model.root;
            await record.update({todo_command: `button_clicked,${method_name}${method_params}`});
            const nextActionTodo = record.data.next_action_todo;
            if(nextActionTodo && ["ir.actions.client", "ir.actions.act_window"].includes(nextActionTodo.type)){
                this.bankRecService.trigger("kanban-do-action", nextActionTodo);
            }
        }
    }
}
BankRecWidgetHTML.template = "account_accountant.BankRecWidgetHTML";

registry.category("fields").add("bank_rec_html", BankRecWidgetHTML);
