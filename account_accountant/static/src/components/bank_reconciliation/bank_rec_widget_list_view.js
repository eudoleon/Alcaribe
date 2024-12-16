/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { View } from "@web/views/view";

const { Component, useSubEnv } = owl;

/**
 * This widget allows to embed a list view in the form view
 */
class FormEmbeddedListView extends Component {

    setup() {
        // Little hack while better solution from framework js.
        // Reset the config, especially the ControlPanel which was coming from a parent form view.
        // It also reset the view switchers which was necessary to make them disappear.
        useSubEnv({
            config: {},
        });

        this.bankRecService = useService("bank_rec_widget");
    }

    get bankRecListViewProps() {
        // retrieve the saved search state based on the res model and restore it to the embedded list view
        let globalState = this.bankRecService.getSearchState(this.bankRecService.kanbanState.selectedStLineId, this.props.resModel);

        return {
            type: "list",
            display: { 
                controlPanel: { 
                    "top-left": false,
                    "bottom-left": false,
                }
            },
            resModel: this.props.resModel,
            searchMenuTypes: ["filter"],
            domain: this.props.record.data[this.props.dataField].domain,
            dynamicFilters: this.props.record.data[this.props.dataField].dynamic_filters,
            context: {
                ...this.props.record.data[this.props.dataField].context,
            },
            allowSelectors: false,
            searchViewId: false, // little hack: force to load the search view info
            globalState: globalState,
        }
    }
}

FormEmbeddedListView.template = "account_accountant.FormEmbeddedListView";
FormEmbeddedListView.props = {
    ...standardWidgetProps,
    resModel: { type: String },
    dataField: { type: String },
}
FormEmbeddedListView.extractProps = ({ attrs }) => ({
    resModel: attrs.resModel,
    dataField: attrs.dataField,
});
FormEmbeddedListView.components = { View }

registry.category("view_widgets").add("bank_rec_form_list", FormEmbeddedListView);
