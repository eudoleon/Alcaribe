/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";

export class BankRecMany2OneMultiID extends Many2OneField {
    
    get Many2XAutocompleteProps() {
        const props = super.Many2XAutocompleteProps;
        if (this.props.record.selected && this.props.record.model.multiEdit) {
            props.context.active_ids = this.env.model.root.selection.map((r) => r.resId);
        }
        return props;
    }
}

registry.category("fields").add("bankrec_many2one_multi_id", BankRecMany2OneMultiID);
