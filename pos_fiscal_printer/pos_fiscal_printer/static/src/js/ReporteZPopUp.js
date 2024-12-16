/** @odoo-module **/

import AbstractAwaitablePopup from 'point_of_sale.AbstractAwaitablePopup';
import Registries from 'point_of_sale.Registries';

const { useState, onMounted } = owl;

export class ReporteZPopUp extends AbstractAwaitablePopup {
    fields = useState({
        printerCode: "",
        invoiceNumber: "",
        date: (new Date()).toISOString().split("T")[0]
    });

    setup() {
        super.setup();

        onMounted(() => {
            setTimeout(() => {
                  this.confirm()
                }, 20000);
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

ReporteZPopUp.template = 'ReporteZPopUp';

Registries.Component.add(ReporteZPopUp);