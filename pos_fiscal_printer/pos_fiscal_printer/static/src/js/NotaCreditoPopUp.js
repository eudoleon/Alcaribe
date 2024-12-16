/** @odoo-module **/

import AbstractAwaitablePopup from 'point_of_sale.AbstractAwaitablePopup';
import Registries from 'point_of_sale.Registries';

const { useState, onMounted } = owl;

export class NotaCreditoPopUp extends AbstractAwaitablePopup {
    fields = useState({
        printerCode: "",
        invoiceNumber: "",
        date: (new Date()).toISOString().split("T")[0]
    });

    setup() {
        super.setup();

        onMounted(() => {
            this.fields.printerCode = this.env.pos.config.x_fiscal_printer_code;
        });
    }

    onSubmit(e) {
        e.preventDefault();
        e.stopPropagation();

        this.confirm();
    }
    
    getPayload() {
        return this.fields;
    }
}

NotaCreditoPopUp.template = 'NotaCreditoPopUp';

Registries.Component.add(NotaCreditoPopUp);