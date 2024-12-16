/* global Sha1 */
odoo.define('pos_blackbox_be.pos_blackbox_be', function (require) {
    const Registries = require('point_of_sale.Registries');
    const { PosGlobalState, Order, Orderline } = require('point_of_sale.models');
    const { Gui } = require('point_of_sale.Gui');

    const core = require('web.core');
    const _t = core._t;

    const PosBlackboxPosGlobalState = (PosGlobalState) => class PosBlackboxPosGlobalState extends PosGlobalState {
        async _processData(loadedData) {
            await super._processData(loadedData);
            this.workInProduct = this.db.product_by_id[loadedData['product_product_work_in']];
            this.workOutProduct = this.db.product_by_id[loadedData['product_product_work_out']]
        }
        useBlackBoxBe() {
            return this.config.iface_fiscal_data_module;
        }
        checkIfUserClocked() {
            const cashierId = this.get_cashier().id;
            if (this.env.pos.config.module_pos_hr) {
                return this.pos_session.employees_clocked_ids.find(elem => elem === cashierId);
            }
            return this.pos_session.users_clocked_ids.find(elem => elem === cashierId);
        }
        disallowLineQuantityChange() {
            const result = super.disallowLineQuantityChange.apply(this, arguments);
            return this.useBlackBoxBe() || result;
        }
        doNotAllowRefundAndSales() {
            const result = super.doNotAllowRefundAndSales.apply(this, arguments);
            return this.useBlackBoxBe() || result;
        }
        async pushProFormaOrder(order) {
            order.receipt_type = order.get_total_with_tax() >= 0 ? "PS" : "PR";
            await this.env.pos.push_single_order(order);
            order.receipt_type = false;
        }
        async push_single_order(order, opts) {
            if (this.useBlackBoxBe() && order) {
                if(!order.receipt_type) {
                    order.receipt_type = order.get_total_with_tax() >= 0 ? 'NS' : 'NR';
                }
                try {
                    order.blackbox_tax_category_a = order.getSpecificTax(21);
                    order.blackbox_tax_category_b = order.getSpecificTax(12);
                    order.blackbox_tax_category_c = order.getSpecificTax(6);
                    order.blackbox_tax_category_d = order.getSpecificTax(0);
                    const data = await this.pushOrderToBlackbox(order);
                    if (data.value.error && data.value.error.errorCode != "000000") {
                        throw data.value.error;
                    }
                    this.setDataForPushOrderFromBlackbox(order, data);
                    this.last_order = order.receipt_type === 'NS'? order: false;
                    return await super.push_single_order.apply(this, [order, opts]);
                } catch(err) {
                    throw {
                        code: 701,
                        error: err,
                    }
               }
            }
            return await super.push_orders.apply(this, arguments);
        }
        async pushOrderToBlackbox(order) {
            const fdm = this.env.proxy.iot_device_proxies.fiscal_data_module;
            const data = {
                'date': moment(order.creation_date).format("YYYYMMDD"),
                'ticket_time': moment(order.creation_date).format("HHmmss"),
                'insz_or_bis_number': this.config.module_pos_hr ? this.get_cashier().insz_or_bis_number : this.user.insz_or_bis_number,
                'ticket_number': order.sequence_number.toString(),
                'type': order.receipt_type,
                'receipt_total': Math.abs(order.get_total_with_tax()).toFixed(2).toString().replace(".",""),
                'vat1': order.blackbox_tax_category_a ? Math.abs(order.blackbox_tax_category_a).toFixed(2).replace(".","") : "",
                'vat2': order.blackbox_tax_category_b ? Math.abs(order.blackbox_tax_category_b).toFixed(2).replace(".","") : "",
                'vat3': order.blackbox_tax_category_c ? Math.abs(order.blackbox_tax_category_c).toFixed(2).replace(".","") : "",
                'vat4': order.blackbox_tax_category_d ? Math.abs(order.blackbox_tax_category_d).toFixed(2).replace(".","") : "",
                'plu': order.getPlu(),
                'clock': order.clock? order.clock : false,
            }

            return new Promise(async (resolve, reject) => {
                fdm.add_listener(data => data.status.status === "connected"? resolve(data): reject(data));
                await fdm.action({
                    action: 'registerReceipt',
                    high_level_message: data,
                });
                // fdm.remove_listener();
            });
        }
        setDataForPushOrderFromBlackbox(order, data) {
            order.blackbox_signature = data.value.signature;
            order.blackbox_unit_id = data.value.vsc;
            order.blackbox_plu_hash = order.getPlu();
            order.blackbox_vsc_identification_number = data.value.vsc;
            order.blackbox_unique_fdm_production_number = data.value.fdm_number;
            order.blackbox_ticket_counter = data.value.ticket_counter;
            order.blackbox_total_ticket_counter = data.value.total_ticket_counter;
            order.blackbox_ticket_counters = order.receipt_type + " " + data.value.ticket_counter + "/" + data.value.total_ticket_counter;
            order.blackbox_time = data.value.time.replace(/(\d{2})(\d{2})(\d{2})/g, '$1:$2:$3');
            order.blackbox_date = data.value.date.replace(/(\d{4})(\d{2})(\d{2})/g, '$3-$2-$1');
        }
        async push_and_invoice_order(order) {
            if (this.useBlackBoxBe()) {
                try {
                    order.receipt_type = order.get_total_with_tax() >= 0 ? 'NS' : 'NR';
                    const data = await this.pushOrderToBlackbox(order);
                    this.setDataForPushOrderFromBlackbox(order, data);
                } catch (err) {
                    return Promise.reject({code:400, message:'Blackbox error', data:{}, status: err.status});
                }
            }
            return super.push_and_invoice_order.apply(this, [order]);
        }
        async getOrderSequenceNumber() {
            return await this.env.services.rpc({
                model: 'pos.config',
                method: 'getOrderSequenceNumber',
                args: [this.config.id],
            });
        }
        async _syncTableOrdersToServer() {
            for (const order of this.ordersToUpdateSet) {
                await this.pushProFormaOrder(order);
            }
            super._syncTableOrdersToServer();
        }
    }
    Registries.Model.extend(PosGlobalState, PosBlackboxPosGlobalState);

    const PosBlackboxOrder = (Order) => class PosBlackboxOrder extends Order {
        getSpecificTax(amount) {
            const tax = this.get_tax_details().find(tax => tax.tax.amount === amount);
            return tax ? tax.amount : false;
        }
        add_product(product, options) {
            if (this.pos.useBlackBoxBe() && product.lst_price < 0) {
                Gui.showPopup('ErrorPopup',{
                    'title': _t("POS error"),
                    'body':  _t("Product has a negative price. Perform a refund instead."),
                });
                return;
            }
            if (this.pos.useBlackBoxBe() && product.taxes_id.length === 0) {
                Gui.showPopup('ErrorPopup',{
                    'title': _t("POS error"),
                    'body':  _t("Product has no tax associated with it."),
                });
                return;
            } else if (this.pos.useBlackBoxBe() && !this.pos.checkIfUserClocked() && product !== this.pos.workInProduct) {
                Gui.showPopup('ErrorPopup',{
                    'title': _t("POS error"),
                    'body':  _t("User must be clocked in."),
                });
                return;
            } else if (this.pos.useBlackBoxBe() && !this.pos.taxes_by_id[product.taxes_id[0]].identification_letter) {
                Gui.showPopup('ErrorPopup',{
                    'title': _t("POS error"),
                    'body':  _t("Product has an invalid tax amount. Only 21%, 12%, 6% and 0% are allowed."),
                });
                return;
            } else if (this.pos.useBlackBoxBe() && product.id === this.pos.workInProduct.id && !options.force) {
                Gui.showPopup('ErrorPopup',{
                    'title': _t("POS error"),
                    'body':  _t("This product is not allowed to be sold"),
                });
                return;
            } else if (this.pos.useBlackBoxBe() && product.id === this.pos.workOutProduct.id && !options.force) {
                Gui.showPopup('ErrorPopup',{
                    'title': _t("POS error"),
                    'body':  _t("This product is not allowed to be sold"),
                });
                return;
            }
            return super.add_product.apply(this, arguments);
        }
        wait_for_push_order() {
            const result = super.wait_for_push_order.apply(this,arguments);
            return Boolean(this.pos.useBlackBoxBe() || result);
        }
        export_as_JSON() {
            let json = super.export_as_JSON(...arguments);

            if (this.pos.useBlackBoxBe()) {
                json = _.extend(json, {
                    'receipt_type': this.receipt_type,
                    'blackbox_unit_id': this.blackbox_unit_id,
                    'blackbox_pos_receipt_time': this.blackbox_pos_receipt_time,
                    'blackbox_ticket_counter': this.blackbox_ticket_counter,
                    'blackbox_total_ticket_counter': this.blackbox_total_ticket_counter,
                    'blackbox_ticket_counters': this.blackbox_ticket_counters,
                    'blackbox_signature': this.blackbox_signature,
                    'blackbox_tax_category_a': this.blackbox_tax_category_a,
                    'blackbox_tax_category_b': this.blackbox_tax_category_b,
                    'blackbox_tax_category_c': this.blackbox_tax_category_c,
                    'blackbox_tax_category_d': this.blackbox_tax_category_d,
                    'blackbox_date': this.blackbox_date,
                    'blackbox_time': this.blackbox_time,
                    'blackbox_unique_fdm_production_number': this.blackbox_unique_fdm_production_number,
                    'blackbox_vsc_identification_number': this.blackbox_vsc_identification_number,
                    'blackbox_plu_hash': this.getPlu(),
                    'blackbox_pos_version': this.pos.version.server_serie
                });
             }
            return json;
        }
        getPlu() {
            let order_str = "";
            this.get_orderlines().forEach(line => order_str += line.generatePluLine());
            const sha1 = Sha1.hash(order_str);
            return sha1.slice(sha1.length - 8);
        }
    }
    Registries.Model.extend(Order, PosBlackboxOrder);

    const PosBlackboxOrderline = (Orderline) => class PosBlackboxOrderline extends Orderline {
        can_be_merged_with(orderline) {
            // The Blackbox doesn't allow lines with a quantity of 5 numbers.
            if (!this.pos.useBlackBoxBe() || (this.pos.useBlackBoxBe() && this.get_quantity() < 9999)) {
                return super.can_be_merged_with.apply(this, arguments);
            }
            return false;
        }
        _generateTranslationTable() {
            var replacements = [
                ["ÄÅÂÁÀâäáàã", "A"],
                ["Ææ", "AE"],
                ["ß", "SS"],
                ["çÇ", "C"],
                ["ÎÏÍÌïîìí", "I"],
                ["€", "E"],
                ["ÊËÉÈêëéè", "E"],
                ["ÛÜÚÙüûúù", "U"],
                ["ÔÖÓÒöôóò", "O"],
                ["Œœ", "OE"],
                ["ñÑ", "N"],
                ["ýÝÿ", "Y"]
            ];

            const lowercase_to_uppercase = _.range("a".charCodeAt(0), "z".charCodeAt(0) + 1).map(function (lowercase_ascii_code) {
                return [String.fromCharCode(lowercase_ascii_code), String.fromCharCode(lowercase_ascii_code).toUpperCase()];
            });
            replacements = replacements.concat(lowercase_to_uppercase);

            let lookup_table = {};

            _.forEach(replacements, function (letter_group) {
                _.forEach(letter_group[0], function (special_char) {
                    lookup_table[special_char] = letter_group[1];
                });
            });

            return lookup_table;
        }
        generatePluLine() {
            // |--------+-------------+-------+-----|
            // | AMOUNT | DESCRIPTION | PRICE | VAT |
            // |      4 |          20 |     8 |   1 |
            // |--------+-------------+-------+-----|

            // steps:
            // 1. replace all chars
            // 2. filter out forbidden chars
            // 3. build PLU line

            let amount = this._getAmountForPlu();
            let description = this.get_product().display_name;
            let price_in_eurocent = this.get_display_price() * 100;
            const vat_letter = this.getVatLetter();

            amount = this._prepareNumberForPlu(amount, 4);
            description = this._prepareDescriptionForPlu(description);
            price_in_eurocent = this._prepareNumberForPlu(price_in_eurocent, 8);

            return amount + description + price_in_eurocent + vat_letter;
        }
        _prepareNumberForPlu(number, field_length) {
            number = Math.abs(number);
            number = Math.round(number);

            let number_string = number.toFixed(0);

            number_string = this._replaceHashAndSignChars(number_string);
            number_string = this._filterAllowedHashAndSignChars(number_string);

            // get the required amount of least significant characters
            number_string = number_string.substr(-field_length);

            // pad left with 0 to required size
            while (number_string.length < field_length) {
                number_string = "0" + number_string;
            }

            return number_string;
        }
        _prepareDescriptionForPlu(description) {
            description = this._replaceHashAndSignChars(description);
            description = this._filterAllowedHashAndSignChars(description);

            // get the 20 most significant characters
            description = description.substr(0, 20);

            // pad right with SPACE to required size of 20
            while (description.length < 20) {
                description = description + " ";
            }

            return description;
        }
        _getAmountForPlu() {
            // three options:
            // 1. unit => need integer
            // 2. weight => need integer gram
            // 3. volume => need integer milliliter

            let amount = this.get_quantity();
            const uom = this.get_unit();

            if (uom.is_unit) {
                return amount;
            } else {
                if (uom.category_id[1] === "Weight") {
                   const uom_gram = _.find(this.pos.units_by_id, function (unit) {
                        return unit.category_id[1] === "Weight" && unit.name === "g";
                    });
                    amount = (amount / uom.factor) * uom_gram.factor;
                } else if (uom.category_id[1] === "Volume") {
                    var uom_milliliter = _.find(this.pos.units_by_id, function (unit) {
                        return unit.category_id[1] === "Volume" && unit.name === "Milliliter(s)";
                    });
                    amount = (amount / uom.factor) * uom_milliliter.factor;
                }

                return amount;
            }
        }
        getVatLetter() {
            const tax = this.get_taxes()[0];
            return tax.identification_letter;
        }
        _replaceHashAndSignChars(str) {
            if (typeof str !== 'string') {
                throw "Can only handle strings";
            }

            var translationTable = this._generateTranslationTable();

            var replaced_char_array = _.map(str, function (char) {
                const translation = translationTable[char];
                return translation ? translation : char;
            });

            return replaced_char_array.join("");
        }
        // for hash and sign the allowed range for DATA is:
        //   - A-Z
        //   - 0-9
        // and SPACE as well. We filter SPACE out here though, because
        // SPACE will only be used in DATA of hash and sign as description
        // padding
        _filterAllowedHashAndSignChars(str) {
            if (typeof str !== 'string') {
                throw "Can only handle strings";
            }

            var filtered_char_array = _.filter(str, function (char) {
                const ascii_code = char.charCodeAt(0);

                if ((ascii_code >= "A".charCodeAt(0) && ascii_code <= "Z".charCodeAt(0)) ||
                    (ascii_code >= "0".charCodeAt(0) && ascii_code <= "9".charCodeAt(0))) {
                    return true;
                } else {
                    return false;
                }
            });

            return filtered_char_array.join("");
        }
        export_as_JSON() {
            let json = super.export_as_JSON(...arguments);

            if (this.pos.useBlackBoxBe()) {
                json.vat_letter = this.getVatLetter();
            }

            return json;
        }
        export_for_printing() {
            const line = super.export_for_printing(...arguments);
            if (this.pos.useBlackBoxBe()) {
                line.vat_letter = this.getVatLetter();
            }
            return line;
        }
    }
    Registries.Model.extend(Orderline, PosBlackboxOrderline);
});
