/** @odoo-module */

import {registry} from "@web/core/registry";
import {standardFieldProps} from "@web/views/fields/standard_field_props";
import {_lt} from "@web/core/l10n/translation";
import {FloatField} from "@web/views/fields/float/float_field";
import { useService } from '@web/core/utils/hooks';
import { reactive, Component, tags } from '@odoo/owl';
const { onPatched } = owl;


console.log("CARGO")
export class NumericSTotalsBs extends FloatField {
    setup() {
        this.rpc = useService('rpc');
        this.orm = useService('orm');
        
        super.setup();
        console.log(this.props)
        this.workorderId = this.props.record.data.id;
        this.additionalContext = this.props.record.resModel;
        
        this.vals = reactive({ value: 1 });
        this.taxs = {};

        onPatched(this, async () => {
            console.log("TEST");
            const modelName = this.props.record.modelName;
            if (modelName === 'sale.order') {
                await this._updateTotals();
            }
        });

        this._updateTotals();
        console.log(this.taxs);
    }
    _onStepClick(ev) {
        let value = this.vals.value++;
        Promise.resolve(this.props.update(value));
    }
    async _updateTotals() {
        console.log("Nombre del modelo:", this.workorderId);
        console.log("ID del registro:",  this.additionalContext);
        this.taxs =  await this.orm.call(
            this.additionalContext,
            'calcular_totales_por_impuesto',
            [this.workorderId],
        );
    } 

   
}

NumericSTotalsBs.template = "10n_ve_dual_currency_bs.AmountTaxBsField";
NumericSTotalsBs.props = {
    ...standardFieldProps,
    name: {type: String, optional: true},
    inputType: {type: String, optional: true},
    step: {type: Number, optional: true},
    min: {type: Number, optional: true},
    max: {type: Number, optional: true},
    placeholder: {type: String, optional: true},
    digits: { type: Number, optional: true },
};

NumericSTotalsBs.displayName = _lt("Numeric Step");
NumericSTotalsBs.supportedTypes = ["float"];
NumericSTotalsBs.defaultProps = {
    inputType: "text",
};

registry.category("fields").add("total_currency_bs", NumericSTotalsBs);
