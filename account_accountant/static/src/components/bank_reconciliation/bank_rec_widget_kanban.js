/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { scrollTo } from "@web/core/utils/scrolling";
import { CallbackRecorder } from "@web/webclient/actions/action_hook";

import { View } from "@web/views/view";
import { useSetupView } from "@web/views/view_hook";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { KanbanRecord } from "@web/views/kanban/kanban_record";

import { BankRecWidgetGlobalInfo } from "./bank_rec_widget_global_info";
import { BankRecActionHelper } from "./bank_rec_widget_action_helper";

import { useState, useRef, useChildSubEnv } from "@odoo/owl";

export class BankRecKanbanRecord extends KanbanRecord {

    async setup() {
        super.setup();

        this.bankRecService = useService("bank_rec_widget");
        this.kanbanState = useState(this.bankRecService.kanbanState);
        this.stLineState = useState(this.bankRecService.getStLineState(this.props.record.resId));

    }

    /** @override **/
    getRecordClasses() {
        let classes = `${super.getRecordClasses()} w-100 o_bank_rec_st_line`;
        if (this.props.record.resId === this.kanbanState.selectedStLineId) {
            classes = `${classes} o_bank_rec_selected_st_line`;
        }
        return classes;
    }
}
BankRecKanbanRecord.template = "account.BankRecKanbanRecord";

export class BankRecKanbanController extends KanbanController {
    async setup() {
        super.setup();

        // we don't care about subview states but we want to avoid them to record
        // some callbacks in the BankRecKanbanController callback recorders passed
        // by the action service
        useChildSubEnv({
            __beforeLeave__: new CallbackRecorder(),
            __getLocalState__: new CallbackRecorder(),
            __getGlobalState__: new CallbackRecorder(),
            __getContext__: new CallbackRecorder(),
        });

        this.action = useService("action");

        this.bankRecService = useService("bank_rec_widget");
        this.state = useState({
            selectedStLineId: null,
            currentJournalId: null,
        });
        this.bankRecService.kanbanState = this.state;
        this.bankRecService.initReconCounter();

        // Move to the next available statement line after a click on a button form.
        this.bankRecService.useTodoCommand("kanban-move-to-next-line", () => {
            const stLineId = this.state.selectedStLineId;

            // Select the next available statement line.
            this.mountStLineInEdit(this.getNextAvailableStLineId(stLineId));
        });

        // Process a newly validated statement line.
        this.bankRecService.useTodoCommand("kanban-validate-st-line", async () => {
            // In case the newly validated record is no longer passing some filters like 'Not Matched', we need to
            // find the next available line based on the records before update. Otherwise, we will not be able to
            // find the next line "after".
            let records = this.records;

            this.bankRecService.incrementReconCounter();
            await this.bankRecService.trigger("kanban-reload", true);

            const stLineId = this.state.selectedStLineId;

            // Select the next available statement line.
            this.mountStLineInEdit(this.getNextAvailableStLineId(stLineId, records));
        });

        this.bankRecService.useTodoCommand("kanban-reload", async (deep) => {
            await this.model.root.load();
            if (deep) {
                this.model.notify();
            } else {
                this.bankRecService.trigger('kanban-render');
            }
        });

        // Redirect the view to another using a window/client action.
        this.bankRecService.useTodoCommand("kanban-do-action", (actionData) => {
            this.action.doAction(actionData);
        });

        this.bankRecService.useTodoCommand("kanban-create-backup", async (linesWidget) => {
            const stLineState = this.bankRecService.getStLineState(this.state.selectedStLineId);
            const selectedKanbanRecord = this.records.find((stLine) => stLine.data.id === this.state.selectedStLineId);
            stLineState.formRestoreData = selectedKanbanRecord ? {
                lines_widget: linesWidget,
                applies_to: selectedKanbanRecord.data,
            } : null;
        });

        // Mount the first available statement line when the model is fully loaded.
        this.model.addEventListener(
            "update",
            () => {
                const propsState = this.props.state || {};
                let stLineIdToRestore = propsState.selectedStLineId;
                const stLineStateToRestore = this.bankRecService.stLineStates[stLineIdToRestore];

                this.bankRecService.stLineStates = {};
                if(stLineStateToRestore){
                    // Check if View/Match buttons from list view have been clicked
                    if(!this.props.selectedStLineId || this.props.selectedStLineId === stLineIdToRestore){
                        this.bankRecService.stLineStates[stLineIdToRestore] = stLineStateToRestore;
                    }else{
                        stLineIdToRestore = null;
                    }
                }

                // Select a statement line.
                if (stLineIdToRestore && this.records.find((stLine) => stLine.data.id === stLineIdToRestore)) {
                    this.mountStLineInEdit(stLineIdToRestore);
                } else {
                    this.mountStLineInEdit(this.getNextAvailableStLineId());
                }
            },
            { once: true },
        );

        // Mount the correct statement line when the search panel changed
        this.env.searchModel.addEventListener(
            "update",
            () => {
                this.model.addEventListener(
                    "update",
                    () => {
                        // keep the current selected line if it's still in the list of st lines
                        let nextStLineId;
                        const currentStLineId = this.state.selectedStLineId;

                        if (this.records.find((stLine) => stLine.data.id === currentStLineId)) {
                            nextStLineId = currentStLineId;
                        } else {
                            nextStLineId = this.getNextAvailableStLineId();
                        }

                        if (nextStLineId !== currentStLineId) {
                            this.mountStLineInEdit(nextStLineId);
                        }
                    },
                    { once: true },
                );
            },
        );

        this.viewRef = useRef("root");
        useSetupView({
            rootRef: this.viewRef,
            getLocalState: () => {
                return {selectedStLineId: this.state.selectedStLineId};
            }
        });
    }

    // -----------------------------------------------------------------------------
    // EVENTS
    // -----------------------------------------------------------------------------

    /**
    Method called when the user changes the search pager.
    **/
    async onUpdatedPager() {
        this.mountStLineInEdit(this.getNextAvailableStLineId());
    }

    /**
    Method called when the user clicks on a card.
    **/
    async openRecord(record, mode) {
        this.mountStLineInEdit(record.resId);
    }

    // -----------------------------------------------------------------------------
    // HELPERS
    // -----------------------------------------------------------------------------

    scrollToSelectedStLine(stLineId) {
        // Scroll to the next kanban card iff the view is mounted, a line is selected  and the kanban
        // card is in the view (cannot use .o_bank_rec_selected_st_line as the dom may not be patched yet)
        if (this.viewRef.el && stLineId) {
            const selectedKanbanCardEl = this.viewRef.el.querySelector(`[st-line-id="${stLineId}"]`);
            if (selectedKanbanCardEl) {
                scrollTo(selectedKanbanCardEl, {});
            }
        }
    }

    /**
    Mount the statement line passed as parameter into the edition form on the right.
    @param stLineId: The id of the statement line to mount.
    **/
    mountStLineInEdit(stLineId){
        const currentStLineId = this.state.selectedStLineId;
        const isSameStLineId = currentStLineId && currentStLineId === stLineId;
        if (!isSameStLineId) {

            // Mount it inside the right-side form.
            this.state.selectedStLineId = stLineId;

            // Scroll to card
            this.scrollToSelectedStLine(this.state.selectedStLineId);

            // Reset the previous st line state
            this.bankRecService.resetStLineState(currentStLineId);

            // Compute currentJournalId.
            if(stLineId){
                const stLine = this.records.find((stLine) => stLine.data.id === stLineId);
                this.state.currentJournalId = stLine.data.journal_id[0];
            }else if(this.props.context.default_journal_id){
                this.state.currentJournalId = this.props.context.default_journal_id;
            }else{
                if(this.records.length > 0){
                    this.state.currentJournalId = this.records[0].data.journal_id[0];
                }else{
                    this.state.currentJournalId = null;
                }
            }
        }
    }

    /**
    Get the next eligible statement line for reconciliation.
    @param afterStLineId:   An optional id of a statement line indicating we want the
                            next available line after this one.
    @param records:         An optional list of records.
    **/
    getNextAvailableStLineId(afterStLineId=null, records=null) {
        const stLines = this.records;

        // Find all available records that need to be validated.
        const isRecordReady = (x) => (!x.data.is_reconciled || x.data.to_check);
        let waitBeforeReturn = Boolean(afterStLineId);
        let availableRecordIds = [];
        for (const stLine of (records || stLines)) {
            if (waitBeforeReturn) {
                if (stLine.resId === afterStLineId) {
                    waitBeforeReturn = false;
                }
            } else if (isRecordReady(stLine)) {
                availableRecordIds.push(stLine.resId);
            }
        }

        // No records left, focus the first record instead. This behavior is mainly there when clicking on "View" from
        // the list view to show an already reconciled line.
        if (!availableRecordIds.length && stLines.length === 1) {
            availableRecordIds = [stLines[0].resId];
        }

        if (availableRecordIds.length){
            return availableRecordIds[0];
        } else if(stLines.length) {
            return stLines[0].resId;
        } else {
            return null;
        }
    }

    mountNextStLineInEdit(){
        this.mountStLineInEdit(this.getNextAvailableStLineId(this.state.selectedStLineId));
    }

    getValidBackup(){
        const selectedKanbanRecord = this.records.find((stLine) => stLine.data.id === this.state.selectedStLineId);
        const formRestoreData = this.bankRecService.getStLineState(this.state.selectedStLineId).formRestoreData;
        const useBackup = selectedKanbanRecord
                          && formRestoreData
                          && _.isEqual(formRestoreData.applies_to, selectedKanbanRecord.data);
        return useBackup ? formRestoreData : null;
    }

    /**
    Give the props when creating the embedded form view.
    **/
    prepareFormProps(){
        // If a local state has been backup, reuse it instead of triggering the matching rules.
        // Otherwise, try to find a match automatically.
        let extraContext = {default_todo_command: "trigger_matching_rules"};

        const formRestoreData = this.getValidBackup();
        if (formRestoreData) {
            extraContext = {
                default_todo_command: null,
                default_lines_widget: formRestoreData.lines_widget,
            };
        }

        return {
            type: "form",
            views: [[false, "form"]],
            context: {
                form_view_ref: "account_accountant.view_bank_rec_widget_form",
                default_st_line_id: this.state.selectedStLineId,
                ...extraContext,
            },
            display: { controlPanel: false, noBreadcrumbs: true},
            mode: "edit",
            resModel: "bank.rec.widget",
        }
    }

    get records() {
        return this.model.root.records;
    }
}
BankRecKanbanController.template = "account.BankReconKanbanController";
BankRecKanbanController.props = {
    ...KanbanController.props,
    selectedStLineId: { optional: true },
}
BankRecKanbanController.components = {
    ...BankRecKanbanController.components,
    BankRecWidgetGlobalInfo,
    View,
}

export class BankRecKanbanRenderer extends KanbanRenderer {
    setup() {
        super.setup();
        this.bankRecService = useService("bank_rec_widget");
        this.bankRecService.useTodoCommand("kanban-render", () => {
            this.render();
        });
    }
}
BankRecKanbanRenderer.template = "account.BankRecKanbanRenderer";
BankRecKanbanRenderer.components = {
    ...KanbanRenderer.components,
    KanbanRecord: BankRecKanbanRecord,
    BankRecActionHelper: BankRecActionHelper,
}

export const BankRecKanbanView = {
    ...kanbanView,
    Controller: BankRecKanbanController,
    Renderer: BankRecKanbanRenderer,
    buttonTemplate: "account.BankRecKanbanRenderer.Buttons",
    searchMenuTypes: ["filter"],
};

registry.category("views").add('bank_rec_widget_kanban', BankRecKanbanView);
