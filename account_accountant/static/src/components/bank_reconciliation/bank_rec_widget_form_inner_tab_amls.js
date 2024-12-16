/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";

const { useState, onWillUnmount } = owl;

export class BankRecWidgetFormInnerTabAmlsRenderer extends ListRenderer {
    setup() {
        super.setup();
        this.bankRecService = useService("bank_rec_widget");
        this.stLineState = useState(this.bankRecService.getStLineState(this.bankRecService.kanbanState.selectedStLineId));
        onWillUnmount(this.saveSearchState);
    }

    /** @override **/
    getRowClass(record) {
        const classes = super.getRowClass(record);
        if (this.stLineState.selectedAmlIds.has(record.resId)){
            return `${classes} o_rec_widget_list_selected_item`;
        }
        return classes;
    }

    /** @override **/
    async onCellClicked(record, column, ev) {
        if (this.stLineState.selectedAmlIds.has(record.resId)) {
            await this.bankRecService.trigger("form-todo-command", `remove_new_aml,${record.resId}`);
        } else {
            await this.bankRecService.trigger("form-todo-command", `add_new_amls,${record.resId}`);
        }
    }

    /** Backup the search facets in order to restore them when the user comes back on this view. **/
    saveSearchState() {
        const searchModel = this.env.searchModel;
        this.stLineState.listAmlsSearchState = JSON.stringify(searchModel.exportState());
    }
}

export class BankRecWidgetFormEmbeddedListModel extends listView.Model {
    setup(params, { action, dialog, notification, rpc, user, view, company }) {
        super.setup(...arguments);
        this.storedDomainString = null;
    }

    /**
    * @override
    * the list of AMLs don't need to be fetched from the server every time the form view is re-rendered.
    * this disables the retrieval, while still ensuring that the search bar works.
    */
    async load(params = {}) {
        const currentDomain = params.domain.toString();
        if (currentDomain !== this.storedDomainString) {
            this.storedDomainString = currentDomain;
            return super.load(params);
        }
    }
}

export const BankRecWidgetFormInnerTabAmls = {
    ...listView,
    Renderer: BankRecWidgetFormInnerTabAmlsRenderer,
    Model: BankRecWidgetFormEmbeddedListModel,
}

registry.category("views").add("bank_rec_widget_form_amls_list", BankRecWidgetFormInnerTabAmls);
