odoo.define('mai_pos_dual_currency.PaymentScreenStatus', function (require) {
	'use strict';

	const PaymentScreenStatus = require('point_of_sale.PaymentScreenStatus');
	const Registries = require('point_of_sale.Registries');
	const { useState, useRef, onPatched } = owl.hooks;
	const { useListener } = require('web.custom_hooks');
	
	const CurrencyPaymentScreenStatus = (PaymentScreenStatus) =>
		class extends PaymentScreenStatus {
			constructor() {
				super(...arguments);
			}

			value_in_other_currency(val){
				let self = this;
				let rate_company = this.env.pos.config.rate_company;
				let show_currency_rate = this.env.pos.config.show_currency_rate;
				let price = val;
				let	price_other_currency = price;
				if(this.env.pos.currency.name == "VEF"){
					if(rate_company > show_currency_rate){
						price_other_currency = price / rate_company;
					}
					else if(rate_company < show_currency_rate){
						price_other_currency = price / show_currency_rate;
					}
				}
				return price_other_currency;
			}

			get total_other_currency() {
				let self = this;
				let price = self.currentOrder.get_total_with_tax();
				return self.value_in_other_currency(price);
			}

			get totaldue_other_currency() {
				let self = this;
				let price = self.currentOrder.get_due();
				let res = self.value_in_other_currency(price);
				if (res < 0){
					return 0;
				}else{
					return res;
				}
			}

			get change_other_currency() {
				let self = this;
				let price = self.currentOrder.get_change();
				return self.value_in_other_currency(price);
			}
		}
	Registries.Component.extend(PaymentScreenStatus, CurrencyPaymentScreenStatus);

	return PaymentScreenStatus;
});



