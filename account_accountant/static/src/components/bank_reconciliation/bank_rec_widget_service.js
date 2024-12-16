/** @odoo-module **/
import { registry } from "@web/core/registry";
import { reactive } from "@odoo/owl";
const { DateTime } = luxon;

export class BankRecWidget {

    constructor(orm, action) {
        this.orm = orm;
        this.action = action;

        this.todoCommandListeners = {};

        this.kanbanState = null;
        this.stLineStates = {};
        this.reconciliationCounter = {};
    }

    /** Reset the timing and reconciliation counter */
    initReconCounter() {
        this.reconciliationCounter = {
            startTime: DateTime.now(),
            reconciledCount: 0,
            timeDiff: null,
        }
    }

    incrementReconCounter() {
        const start = this.reconciliationCounter.startTime.set({millisecond: 0});
        const end = DateTime.now().set({millisecond: 0});
        this.reconciliationCounter.timeDiff = end.diff(start, "seconds");
        this.reconciliationCounter.reconciledCount++;
    }

    /** Get the default values for the state representing the form. **/
    getDefaultFormState(){
        return {
            stLineRecord: null,
            formRootRef: null,
            lastFormData: null,
            notebookPage: null,
            notebookFirstPage: null,
            notebookManualOperationPage: null,
        }
    }

    // -----------------------------------------------------------------------------
    // HELPERS
    // -----------------------------------------------------------------------------

    /** Get the default values for the state representing the mounted statement line into the form. **/
    getDefaultStLineState(){
        return {
            isLoading: false,
            selectedAmlIds: new Set(),
            formRestoreData: null,
            listAmlsSearchState: null,
        }
    }

    /** Get the state corresponding to the statement line passed as parameter. **/
    getStLineState(stLineId){
        if(stLineId && !this.stLineStates[stLineId]){
            this.resetStLineState(stLineId);
        }
        return this.stLineStates[stLineId];
    }

    /**
      * Cleanup the state corresponding to the statement line passed as parameter.
      * @param {integer} stLineId: The id of a statement line.
      */
    resetStLineState(stLineId) {
        if (!stLineId) {
            return;
        }
        this.stLineStates[stLineId] = reactive(this.getDefaultStLineState());
    }

    /**
      * Retrieve the backup of the search facets for an embedded list view.
      * @param {integer} stLineId: The id of a statement line.
      * @param {string} modelName: The model of the embedded list view.
      */
    getSearchState(stLineId, modelName) {
        return modelName === 'account.move.line' ? { searchModel: this.stLineStates[stLineId].listAmlsSearchState } : undefined;
    }

    /**
      * Allow the horizontal communication between all components composing the bank reconciliation widget.
      * This method associates an event's name to a callback method.
      * @param {string} eventName: The event's name.
      * @param {function} callback: The method to be invoked when the event is triggered.
      */
    useTodoCommand(eventName, callback){
        this.todoCommandListeners[eventName] = callback;
    }

    /**
      * Trigger the callback method registered using the 'useTodoCommand' method.
      * @param {string} eventName: The event's name.
      * @param {object} data: The data to be passed to the callback method.
      */
    async trigger(eventName, data){
        const listener = this.todoCommandListeners[eventName];
        if(listener){
            await listener(data);
        }
    }
}

export const BankRecWidgetService = {
    dependencies: ["orm", "action"],

    start(env, { orm, action }) {
        return new BankRecWidget(orm, action);
    },
}

registry.category("services").add("bank_rec_widget", BankRecWidgetService);
