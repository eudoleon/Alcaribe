/** @odoo-module **/

import { PosGlobalState, Payment, Order } from 'point_of_sale.models';
import PaymentScreen from "point_of_sale.PaymentScreen";
import AbstractReceiptScreen from 'point_of_sale.AbstractReceiptScreen';
import ReceiptScreen from 'point_of_sale.ReceiptScreen';
import Registries from 'point_of_sale.Registries';
import { PrintingMixin } from './PrintingMixin';
import ClosePosPopup from "point_of_sale.ClosePosPopup";

export function convert(amount, fixed = 2) {
    return (amount || 0).toFixed(fixed).replace(".",",");
}

Registries.Model.extend(Payment, (Parent) => class extends Parent {
    x_printer_code = null;

    constructor(obj, options) {
        super(obj, options);

        this.x_printer_code ||= this.payment_method.x_printer_code;
    }

    init_from_JSON(json) {
        super.init_from_JSON(json);

        this.x_printer_code = json.x_printer_code;
    }
});

Registries.Model.extend(Order, (Parent) => class extends Parent {
    impresa = null;
    num_factura = null
    constructor(obj, options) {
        super(obj, options);
        this.num_factura ||= false;
        this.impresa ||= false;
    }

    init_from_JSON(json) {
        super.init_from_JSON(json);
        this.num_factura = json.num_factura;
        this.impresa = json.impresa;
    }

    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.num_factura = this.num_factura;
        return json;
    }
});

Registries.Model.extend(PosGlobalState, (Parent) => class extends Parent {
    serialPort = null;

    async _processData(loadedData) {
        await super._processData(...arguments);
        this.city_id = loadedData['res.city'];
    }
});


Registries.Component.extend(ClosePosPopup, (Parent) => class extends PrintingMixin(Parent) {
    openDetailsPopup() {
        this.state.zReport = ""
        return super.openDetailsPopup();
    }

    async closeSession() {
        if(this.state.zReport === "" || !this.state.zReport) {
            console.log("closeSession sin reporte Z");
        }else{
            console.log("closeSession con reporte Z");
            await this.rpc({
                model: 'pos.session',
                method: 'set_z_report',
                args: [this.env.pos.pos_session.id, this.state.zReport],
            });
        }
        return super.closeSession();
    }

    async printZReport() {
        if(this.env.pos.config.connection_type === "api") {
            this.printZViaApi();
        }else{
            this.printerCommands = [];
            this.read_Z = false;
            this.printerCommands.push("I0Z");
            this.actionPrint();
        }
    }
    async printXReport() {
        if(this.env.pos.config.connection_type === "api") {
            this.printXViaApi();
        }else{
            this.printerCommands = [];
            this.read_Z = false;
            this.printerCommands.push("I0X");
            this.actionPrint();
        }
    }
});
Registries.Component.extend(PaymentScreen, (Parent) => class extends Parent {
    async validateOrder(isForceValidate) {
        if(!this.currentOrder.partner) {
            this.showPopup('ErrorPopup', {
                title: "Error",
                body: "El cliente es obligatorio para proceder",
            });
            return;
        }

        return super.validateOrder(isForceValidate);
    }
});

Registries.Component.extend(ReceiptScreen, (Parent) => class extends Parent {
    orderDone() {
        if(this.currentOrder.impresa) {
                this.env.pos.removeOrder(this.currentOrder);
                this._addNewOrder();
                const { name, props } = this.nextScreen;
                this.showScreen(name, props);
                if (this.env.pos.config.iface_customer_facing_display) {
                    this.env.pos.send_current_order_to_customer_facing_display();
                }
        }else{
            this.showPopup('ErrorPopup', {
                title: "Error",
                body: "Debe imprimir el documento fiscal",
            });
        }
     }
});

const AbstractReceiptScreenNew = (Parent) => class extends PrintingMixin(Parent) {
    get order() {
        return (this.constructor.name === "ReprintReceiptScreen")
            ? this.props.order
            : this.env.pos.get_order();
    }

    async doPrinting(mode) {
        if(!(this.order.get_paymentlines().every(({ x_printer_code }) => Boolean(x_printer_code)))) {
            this.showPopup('ErrorPopup', {
                title: "Error",
                body: "Algunos métodos de pago no tienen código de impresora",
            });
            return;
        }
        if(this.order.impresa) {
           this.showPopup('ErrorPopup', {
                        title: "Error",
                        body: "Documento impreso en máquina fiscal",
                    });
           return;
        }
        this.printerCommands = [];
        switch(mode) {
            case "noFiscal":
                this.printNoFiscal();
                break;
            case "fiscal":
                this.read_s2 = true;
                this.printFiscal();
                break;
            case "notaCredito":
                this.read_s2 = true;
                const result = await this.printNotaCredito();

                if(!result) return;

                break;
        }

        //this.printerCommands.unshift("7");

        //debugger;
        if (this.env.pos.config.connection_type === "usb") {
           this.printViaUSB();
        }else if (this.env.pos.config.connection_type === "serial") {
           this.actionPrint();
        }else if (this.env.pos.config.connection_type === "usb_serial") {
           this.actionPrint();
        } else if(this.env.pos.config.connection_type === "api") {
           this.printViaApi();
        }else{
           this.actionPrint();
        }


    }

    setHeader(payload) {
        const client = this.order.partner;



        if(payload) {
            this.printerCommands.push("iF*" + payload.invoiceNumber.padStart(11, "0"));
            this.printerCommands.push("iD*" + payload.date);
            this.printerCommands.push("iI*" + payload.printerCode);
        }

        this.printerCommands.push("iR*" + (client.vat || "No tiene"));
        this.printerCommands.push("iS*" + client.name);

        this.printerCommands.push("i00Teléfono: " + (client.phone || "No tiene"));
        this.printerCommands.push("i01Dirección: " + (client.street || "No tiene"));
        this.printerCommands.push("i02Email: " + (client.email || "No tiene"));
        if(this.order.name){
            this.printerCommands.push("i03Ref: " + this.order.name);
        }

    }

    setTotal() {
        this.printerCommands.push("3");
        const aplicar_igtf = this.env.pos.config.aplicar_igtf;
        const isAboveThreshold = (amount) => amount > 0;
        //validar si todo en divisas
        const es_nota = this.order.get_orderlines().every(({ refunded_orderline_id }) => Boolean(refunded_orderline_id) );
        console.log("es_nota", es_nota);
        if(es_nota) {
            if(this.order.get_paymentlines().filter(({ amount }) => Boolean(amount < 0)).every(({ isForeignExchange}) => Boolean(isForeignExchange) ) && aplicar_igtf) {
                this.printerCommands.push("122");
            }else{
                this.order.get_paymentlines().filter(({ amount }) => Boolean(amount < 0)).forEach((payment, i, array) => {
                    if(payment.amount < 0){
                        if((i + 1) === array.length && this.order.get_paymentlines().filter(({ amount }) => Boolean(amount < 0)).length === 1) {
                            this.printerCommands.push("1" + payment.x_printer_code);
                        } else {
                            let amount = convert(payment.amount);

                            amount = amount.split(",");
                            amount[0] = Math.abs(amount[0]).toString();
                            amount[0] = this.env.pos.config.flag_21 === '30' ? amount[0].padStart(15, "0"):amount[0].padStart(10, "0");
                            amount = amount.join("");
                            this.printerCommands.push("2" + payment.x_printer_code + amount);

                        }
                    }
                });
            }
        }else{
            if(this.order.get_paymentlines().filter(({ amount }) => Boolean(amount > 0)).every(({ isForeignExchange}) => Boolean(isForeignExchange) ) && aplicar_igtf) {
                this.printerCommands.push("122");
            }else{
                this.order.get_paymentlines().filter(({ amount }) => Boolean(amount > 0)).forEach((payment, i, array) => {
                    if(payment.amount > 0){
                        if((i + 1) === array.length && this.order.get_paymentlines().filter(({ amount }) => Boolean(amount > 0)).length === 1) {
                            this.printerCommands.push("1" + payment.x_printer_code);
                        } else {
                            let amount = convert(payment.amount);

                            amount = amount.split(",");
                            amount[0] = Math.abs(amount[0]).toString();
                            amount[0] = this.env.pos.config.flag_21 === '30' ? amount[0].padStart(15, "0"):amount[0].padStart(10, "0");
                            amount = amount.join("");
                            this.printerCommands.push("2" + payment.x_printer_code + amount);

                        }
                    }
                });
            }
        }


        if (aplicar_igtf) {
            this.printerCommands.push("199");
        }else{
            console.log("ultimo comando");
            console.log(this.printerCommands.slice(-1));
            if(this.printerCommands.slice(-1) == '101'){
                console.log("no se agrega 101");
            }else{
                this.printerCommands.push("101");
            }
        }
        //this.printerCommands.push("3");
    }

    printFiscal() {
        this.setHeader();
        this.setLines("GF");
        this.setTotal();
    }

    setLines(char) {
        this.order
            .get_orderlines()
            .filter(({ x_is_igtf_line }) => !x_is_igtf_line)
            .forEach((line) => {
                //let command = char + "+";
                let command = "";
                const taxes = line.get_taxes();

                if(!(taxes.length) || taxes.every(({ x_tipo_alicuota }) => x_tipo_alicuota === "exento")) {
                    command += "";
                    if(char === "GC") {
                        command += "d0";
                    }else{
                        command += " ";
                    }
                } else if(taxes.every(({ x_tipo_alicuota }) => x_tipo_alicuota === "general")) {

                    if(char === "GC") {
                        command += "d1";
                    }else{
                        command += "!";
                    }
                }else{
                    if(char === "GC") {
                        command += "d0";
                    }else{
                        command += " ";
                    }
                }
                /*else if(taxes.every(({ x_tipo_alicuota }) => x_tipo_alicuota === "reducido")) {
                    command += "2";
                } else {
                    command += "3";
                }*/


                let amount = convert(line.get_price_without_tax()/line.quantity).split(",");
                let quantity = convert(Math.abs(line.quantity), 3).split(",");

                amount[0] = this.env.pos.config.flag_21 === '30' ? amount[0].padStart(14, "0"):amount[0].padStart(8, "0");
                quantity[0] = this.env.pos.config.flag_21 === '30' ? quantity[0].padStart(14, "0"):quantity[0].padStart(5, "0");

                amount = amount.join("");
                quantity = quantity.join("");

                command += amount;
                command += `${quantity}`;

                const { product } = line;

                if(product.default_code) {
                    command += `|${product.default_code}|`;
                }

                command += product.display_name;

                this.printerCommands.push(command);
                //comando tester error
                //this.printerCommands.push('-' + command);

                if(line.discount > 0) {
                    this.printerCommands.push("q-" + convert(line.discount));
                }

                if(line.customerNote) {
                    if(char === "GC") {
                        this.printerCommands.push(`A##${line.customerNote}##`);
                    } else {
                        this.printerCommands.push(`@##${line.customerNote}##`);
                    }
                }

            });
    }

    printNoFiscal() {
        this.order
            .get_orderlines()
            .filter(({ x_is_igtf_line }) => !x_is_igtf_line)
            .forEach((line) => {
                const { product } = line;
                this.printerCommands.push(`80 ${product.display_name} [${product.default_code}]`);
                this.printerCommands.push(
                    `80*x${line.quantityStr} ${convert(line.get_price_with_tax())} (${convert(line.get_taxed_lst_unit_price())} C/U)`
                );
            });

        if(this.order.get_change()) {
            this.printerCommands.push("80*CAMBIO: " + convert(this.order.get_change()));
        }

        this.printerCommands.push("81$TOTAL: " + convert(this.order.get_total_with_tax()));
    }

    async printNotaCredito() {
        const { confirmed, payload } = await this.showPopup("NotaCreditoPopUp");

        if(!confirmed) return false;

        this.setHeader(payload);
        this.setLines("GC");
        this.setTotal();

        return true;
    }
};

Registries.Component.extend(AbstractReceiptScreen, AbstractReceiptScreenNew);