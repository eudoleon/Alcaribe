/** @odoo-module **/

import AbstractAwaitablePopup from 'point_of_sale.AbstractAwaitablePopup';
import Registries from 'point_of_sale.Registries';
import { PrintingMixin } from './PrintingMixin';
import PosComponent from "point_of_sale.PosComponent";

const { useState } = owl;

export class ReprintingButton extends PrintingMixin(PosComponent) {
    async doReprinting() {
        const { confirmed, payload } = await this.showPopup("ReprintingPopUp");
        
        if(!confirmed) return;

        this.printerCommands = payload;

        this.actionPrint();
    }
}

ReprintingButton.template = 'ReprintingButton';

Registries.Component.add(ReprintingButton);

export class ReprintingPopUp extends AbstractAwaitablePopup {
    fields = useState({
        printingMode: "numero",
        document: "f",
        cedula: "",
        fromDate: "",
        toDate: "",
        fromNumber: "",
        toNumber: "",
    });

    onSubmit(e) {
        e.preventDefault();
        e.stopPropagation();

        this.confirm();
    }

    getPayload() {
        const { document, printingMode } = this.fields;

        switch(printingMode) {
            case "ultimo":
                return ["RU00000000000000"];
            case "numero":
                const padding = (str) => str.padStart(7, "0");

                return [
                    "R",
                    (document === "*") ? "@" : document.toUpperCase(),
                    padding(this.fields.fromNumber),
                    padding(this.fields.toNumber),
                ].join("");
            case "cedula":
                return ["RK" + this.fields.cedula];
            case "fecha":
                const datestr = (date) => moment(date).format("0YYMMDD");

                return ["R", document, datestr(this.fields.fromDate), datestr(this.fields.toDate)];
        }
    }
}

ReprintingPopUp.template = 'ReprintingPopUp';

Registries.Component.add(ReprintingPopUp);