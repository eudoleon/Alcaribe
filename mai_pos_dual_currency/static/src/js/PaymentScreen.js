odoo.define('mai_pos_dual_currency.CustomPaymentScreen', function(require) {
	'use strict';

	const PaymentScreen = require('point_of_sale.PaymentScreen');
	const Registries = require('point_of_sale.Registries');
	const NumberBuffer = require('point_of_sale.NumberBuffer');
	const session = require('web.session');
	var core = require('web.core');
	var _t = core._t;
	
	const CustomPaymentScreen = PaymentScreen => 
		class extends PaymentScreen {
			constructor() {
				super(...arguments);
			}
			
			_updateSelectedPaymentline() {
				let self = this;
				let rate_company = this.env.pos.config.rate_company;
				let show_currency_rate = this.env.pos.config.show_currency_rate;
						
				if (this.paymentLines.every((line) => line.paid)) {
					this.currentOrder.add_paymentline(this.payment_methods_from_config[0]);
				}
				if (!this.selectedPaymentLine) return; // do nothing if no selected payment line
				// disable changing amount on paymentlines with running or done payments on a payment terminal
				const payment_terminal = this.selectedPaymentLine.payment_method.payment_terminal;
				if (
					payment_terminal &&
					!['pending', 'retry'].includes(this.selectedPaymentLine.get_payment_status())
				) {
					return;
				}
				if (NumberBuffer.get() === null) {
					this.deletePaymentLine({ detail: { cid: this.selectedPaymentLine.cid } });
				} else {
					let	price_other_currency = NumberBuffer.getFloat();
					if(this.selectedPaymentLine.payment_method.pago_usd){
						price_other_currency = price_other_currency * rate_company;
						this.selectedPaymentLine.set_usd_amt(NumberBuffer.getFloat());
					}
					this.selectedPaymentLine.set_amount(price_other_currency);
					
				}
			}


		}
	Registries.Component.extend(PaymentScreen, CustomPaymentScreen);
	return PaymentScreen;

});