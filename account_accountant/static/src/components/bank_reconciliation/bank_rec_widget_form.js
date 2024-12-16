/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

import { FormController } from "@web/views/form/form_controller";
import { FormRenderer } from "@web/views/form/form_renderer";
import { formView } from "@web/views/form/form_view";
import { Notebook } from  "@web/core/notebook/notebook"

const { onPatched, useState, useSubEnv, useRef } = owl;

export class BankRecWidgetFormController extends FormController {
    setup() {
        super.setup();

        useSubEnv({onClickViewButton: this.viewButtonClick.bind(this)});

        this.orm = useService("orm");
        this.rootRef = useRef("root");

        this.bankRecService = useService("bank_rec_widget");
        this.stLineState = useState(this.bankRecService.getStLineState(this.props.context.default_st_line_id));
        this.kanbanState = useState(this.bankRecService.kanbanState);

        // Execute a todo command.
        this.bankRecService.useTodoCommand("form-todo-command", async (todoCommand) => {
            await this.record.update({todo_command: todoCommand});
        });

        // Called at each onchange.
        this.model.addEventListener("update", () => this.onRecordChanged());

        // Allow to disable the buttons. It needs to be handled manually since the form is never saved.
        this.disabledButtons = [];
    }

    get record() {
        return this.model.root;
    }

    /** Called when the form model is fully loaded. **/
    async onRecordChanged(){
        // Update the selected amls.
        let selectedAmlIds = new Set();
        for(const aml of this.record.data.selected_aml_ids.records){
            selectedAmlIds.add(aml.data.id);
        }
        if (this.stLineState.selectedAmlIds !== selectedAmlIds) {
            this.stLineState.selectedAmlIds = selectedAmlIds;

            // Save the data.
            this.bankRecService.trigger("kanban-create-backup", this.record.data.lines_widget);
        }

        // Refresh Kanban if the liquidity line values changed
        if (["refresh_liquidity", "refresh_liquidity_balance"].includes(this.record.data.next_action_todo.type || '')) {
            await this.postProcessNextActionTodo(this.record.data.next_action_todo);
        };
    }

    /** Force the display name of the vue to avoid putting it manually every time in the action. **/
    displayName() {
        return this.env._t("Bank Reconciliation");
    }

    /**
     * Called when a statement line has been validated.
     * Perform the reconciliation of this line asynchronously (disabled at the moment) and asks to the
     * kanban to move to the next available line.
     */
    async actionValidate(){
        // Mark the kanban card as loading.
        this.stLineState.isLoading = true;

        await this.bankRecService.trigger("kanban-validate-st-line");

        // Mark the kanban card as no longer loading.
        this.stLineState.isLoading = false;
    }

    /**
     * Called when a statement line has been reset to its original state.
     * Select the first available notebook page since there are more than one when the statement line is editable.
     */
    async actionReset(){
        this.bankRecService.trigger("form-notebook-activate-first-page");
    }

    /** Asks the kanban to move to the next available statement line **/
    async actionMoveToNext(){
        this.bankRecService.trigger("kanban-move-to-next-line");
    }

    /** Asks the kanban to refresh the kanban card corresponding to the statement line mounted into the form. **/
    async actionRefreshStLineData(){
        // Mark the kanban card as loading.
        this.stLineState.isLoading = true;

        // Refresh the kanban
        await this.bankRecService.trigger("kanban-reload");

        // Mark the kanban card as no longer loading.
        this.stLineState.isLoading = false;
    }

    /** Asks the kanban to refresh the global info widget. **/
    async actionRefreshGlobalInfo() {
        this.bankRecService.trigger("globalinfo-refresh");
    }

    /** Process the nextActionTodo passed as parameter and filled python-side using the next_todo_command field. **/
    async postProcessNextActionTodo(nextActionTodo){
        if (["ir.actions.client", "ir.actions.act_window"].includes(nextActionTodo.type)) {
            this.bankRecService.trigger("kanban-do-action", nextActionTodo);
        } else if (nextActionTodo.type == "reconcile_st_line"){
            await this.actionValidate();
        } else if (nextActionTodo.type == "reset_form") {
            await this.actionReset();
            await this.actionRefreshStLineData();
        } else if (nextActionTodo.type == "move_to_next") {
            await this.actionRefreshStLineData();
            await this.actionMoveToNext();
        } else if (nextActionTodo.type === "refresh_liquidity_balance") {
            await this.actionRefreshStLineData();
            await this.actionRefreshGlobalInfo();
        } else if (["refresh_statement_line", "refresh_liquidity"].includes(nextActionTodo.type) ) {
            await this.actionRefreshStLineData();
        }

        // reset the nextActionTodo as it has been done
        if (this.record.data.nextActionTodo === nextActionTodo) {
            this.record.update({'next_action_todo': {}});
        }
    }

    /** Enable the buttons that are previously be disabled by the 'disableButtons' method. **/
    enableButtons() {
        for (const btn of this.disabledButtons) {
            btn.removeAttribute("disabled");
        }
        this.disabledButtons = [];
    }

    /** Disable the buttons to prevent a spam clicks from the user. **/
    disableButtons() {
        // inspired by view_button_hook
        const btns = [...this.rootRef.el.querySelectorAll(".o_statusbar_buttons button:not([disabled])")];
        for (const btn of btns) {
            btn.setAttribute("disabled", "1");
        }
        this.disabledButtons = btns;
    }

    /** Called when the user clicks on a button. **/
    async viewButtonClick({ clickParams }) {
        // prevent buttons from executing the action directly, use the onchange mechanism instead
        // this was done to enable async reconciliations (subsequently disabled. TODO: revisit)
        this.disableButtons();
        await this.record.update({todo_command: `button_clicked,${clickParams.name}`});

        const nextActionTodo = this.record.data.next_action_todo;
        if (nextActionTodo) {
            this.postProcessNextActionTodo(nextActionTodo);
        }
        this.enableButtons();
    }

    /**
      * @override
      * Prevent to save the form since this model has no table.
      */
    beforeUnload() {
        return;
    }
}
BankRecWidgetFormController.props = {
    ...FormController.props,
    // The views are needed because when loading the form view, owl tries to use it and if it is not available it
    // falls back to the action's views ending up in rendering wrong list view
    views: { optional: true },
}

export class BankRecNotebook extends Notebook {
    setup() {
        super.setup();

        this.bankRecService = useService("bank_rec_widget");

        // Focus a specific page.
        this.bankRecService.useTodoCommand("form-notebook-activate-manual-op-page", () => {
            if(this.manualOperationPage != this.state.currentPage){
                super.activatePage(this.manualOperationPage);
            }
        });

        // Focus the first available page.
        this.bankRecService.useTodoCommand("form-notebook-activate-first-page", () => {
            super.activatePage(this.firstPage);
        });

        // Focus the first available page if the manual operation page is active.
        this.bankRecService.useTodoCommand("form-notebook-exit-manual-op-if-active", () => {
            if(this.manualOperationPage == this.state.currentPage){
                super.activatePage(this.firstPage);
            }
        });
    }

    get manualOperationPage(){
        return this.pages.find((p) => p[1].name === "manual_operations_tab")[0];
    }

    get firstPage(){
        return this.pages[0][0];
    }

    /**
      * @override
      * Mount the last available line in edition when the manual operation tab becomes active.
      * Otherwise, clear the manual operation form if something is already mounted.
      */
    async activatePage(page) {
        super.activatePage(page);

        const record = this.env.model.root;
        if(record.data.state == "reconciled"){
            // No edition allowed when the statement line is already reconciled.
            return;
        }

        if(this.state.currentPage != this.manualOperationPage){
            const currentLineIndex = record.data.form_index;
            if(currentLineIndex){
                // Clear the line mounted into the manual operations page.
                await record.update({todo_command: "clear_edit_form"});
            }
            return;
        }

        const lastLineIndex = record.data.lines_widget.lines.slice(-1)[0].index.value;
        if(lastLineIndex){
            await record.update({todo_command: `mount_line_in_edit,${lastLineIndex}`});
        }
    }
}

export class BankRecFormRenderer extends FormRenderer {
    setup() {
        super.setup();

        this.roofRef = useRef("compiled_view_root");
        this.bankRecService = useService("bank_rec_widget");
        this.clickedColumn = null;

        // Focus the clicked column when the manual operations tab will be ready.
        // The corresponding field will be focused directly if the manual operations page is already active and the line was not changed by the click.
        // If not, this will be done by the onPatched just below.
        this.bankRecService.useTodoCommand("form-clicked-column", (clickInfo) => {
            if(clickInfo.lineChanged) {
                this.clickedColumn = clickInfo.clickedColumn;
            } else {
                this.focusManualOperationField(clickInfo.clickedColumn);
                this.clickedColumn = null;
            }
        });

        // Focus the clicked column when DOM is patched.
        onPatched(() => {
            if(this.clickedColumn){
                this.focusManualOperationField(this.clickedColumn);
                this.clickedColumn = null;
            }
        });
    }

    /**
    Focus the field corresponding to the column name passed as parameter inside the
    manual operation page.
    **/
    focusManualOperationField(clickedColumn){
        // Focus the field corresponding to the clicked column.
        if (['debit', 'credit'].includes(clickedColumn)) {
            if (this.focusElement("div[name='form_balance'] input")) {
                return true;
            }
            if (this.focusElement("div[name='form_amount_currency'] input")) {
                return true;
            }
        }

        if (this.focusElement(`div[name='form_${clickedColumn}'] input`)) {
            return true;
        }
        if (this.focusElement(`input[name='form_${clickedColumn}']`)) {
            return true;
        }
        return false;
    }

    /** Helper to find the corresponding field to focus inside the DOM. **/
    focusElement(selector) {
        const inputEl = this.roofRef.el.querySelector(selector);
        if (!inputEl) {
            return false;
        }

        if (inputEl.tagName === "INPUT") {
            inputEl.focus();
            inputEl.select();
        } else {
            inputEl.focus();
        }
        return true;
    }
}
BankRecFormRenderer.components = {
    ...FormRenderer.components,
    Notebook: BankRecNotebook,
}

export const BankRecWidgetForm = {
    ...formView,
    Controller: BankRecWidgetFormController,
    Renderer: BankRecFormRenderer,
    display: { controlPanel: false },
}

registry.category("views").add('bank_rec_widget_form', BankRecWidgetForm);
