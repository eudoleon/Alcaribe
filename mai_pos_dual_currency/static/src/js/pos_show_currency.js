odoo.define('mai_pos_dual_currency.OrderWidget', function (require) {
	'use strict';

	const OrderWidget = require('point_of_sale.OrderWidget');
	const Registries = require('point_of_sale.Registries');
	const { useState, useRef, onPatched } = owl.hooks;
	const { useListener } = require('web.custom_hooks');
	
	const CurrencyOrderWidget = (OrderWidget) =>
		class extends OrderWidget {
			constructor() {
				super(...arguments);
				this.state = useState({ 
					total: 0, 
					tax: 0 , 
					subtotal : 0,
					total_amt : 0,
					tax_amt : 0,
					total_currency_text : '',
					taxes_currency_text : '',
					total_currency : 0,
					taxes_currency : 0,
					subtotal_currency_text : '',
				});
			}

			_updateSummary(){
				const total = this.order ? this.order.get_total_with_tax() : 0;
				const tax = this.order ? total - this.order.get_total_without_tax() : 0;
				if(this.env.pos.config.show_dual_currency){
					let total_currency = 0;
					let taxes_currency = 0;
					let rate_company = parseFloat(this.env.pos.config.rate_company);
					let show_currency_rate = parseFloat(this.env.pos.config.show_currency_rate);
					if(this.env.pos.currency.name == "VEF"){
						if(rate_company > show_currency_rate){
							total_currency = total / rate_company;
							taxes_currency = tax / rate_company;
						}else if(rate_company < show_currency_rate){
							if(show_currency_rate>0){
								total_currency = total / show_currency_rate;
								taxes_currency = tax / show_currency_rate;
							}
						}else{
							total_currency = total;
							taxes_currency = tax;
						}
					}else{
						total_currency = total;
						taxes_currency = tax;
					}
					let total_currency_text = '';
					let taxes_currency_text = '';
					if(this.env.pos.config.show_currency_position=='before'){
						total_currency_text = this.env.pos.config.show_currency_symbol+' '+total_currency.toFixed(2);
						taxes_currency_text = this.env.pos.config.show_currency_symbol+' '+taxes_currency.toFixed(2);
					}else{
						total_currency_text = total_currency.toFixed(2) +' '+this.env.pos.config.show_currency_symbol;
						taxes_currency_text = taxes_currency.toFixed(2) +' '+this.env.pos.config.show_currency_symbol;
					}

					this.state.total_currency = total_currency ;
					this.state.taxes_currency = taxes_currency ;

					this.state.total_amt = total ;
					this.state.tax_amt = tax ;
					this.state.subtotal = this.env.pos.format_currency(total-tax);

					this.state.total = this.env.pos.format_currency(total);
					this.state.total_currency_text = total_currency_text;
					this.state.tax = this.env.pos.format_currency(tax);
					this.state.taxes_currency_text = taxes_currency_text;
					this.state.subtotal_currency_text = this.env.pos.config.show_currency_symbol  +' '+ (total_currency-taxes_currency).toFixed(2);
					
					this.render();
				}else{

					this.state.total_amt = total ;
					this.state.tax_amt = tax ;

					this.state.subtotal = this.env.pos.format_currency(total-tax);
					this.state.total = this.env.pos.format_currency(total);
					this.state.tax = this.env.pos.format_currency(tax);
					this.render();
				}
			}

		}
	Registries.Component.extend(OrderWidget, CurrencyOrderWidget);

	return OrderWidget;
});



