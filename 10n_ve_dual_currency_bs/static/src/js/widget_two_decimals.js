/** @odoo-module **/
import fieldRegistry from 'web.field_registry';
import { FieldBasics} from 'web.basic_fields';



export const MonetaryDecimals = FieldBasics.FieldMonetary.extend({

    init: function () {
        this._super.apply(this, arguments);
        console.log("PRUEBA");
    },

    _format: function (value) {
        console.log("1111111111")
        console.log(value)
        var formattedValue = this._super.apply(this, arguments);
        console.log(formattedValue)
        if (typeof formattedValue === 'string') {
            var parts = formattedValue.split('.');
            if (parts.length > 1) {
                parts[1] = parts[1].substring(0, 2);  // Limitar a dos decimales
            } else {
                parts.push('00');  // Agregar decimales si no hay ninguno
            }
            formattedValue = parts.join('.');
        }
        return formattedValue;
    },
});

fieldRegistry.add("two_decimals", MonetaryDecimals);
