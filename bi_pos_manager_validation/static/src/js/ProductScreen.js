
odoo.define('bi_pos_manager_validation.BiProductScreen', function(require) {
	'use strict';

	const PosComponent = require('point_of_sale.PosComponent');
	const ProductScreen = require('point_of_sale.ProductScreen');
	const Registries = require('point_of_sale.Registries');

	let check_pay = true;
	let check_dol = true;

	const BiProductScreen = (ProductScreen) =>
		class extends ProductScreen {
			setup() {
            	super.setup();
			}

			async _onClickPay() {
				let config = this.env.pos.config;
				let config_otp = config.one_time_valid;
				let result = true;
				let otp =this.env.pos.otp;
				let order = this.env.pos.get_order();

				if(config.payment_perm && check_pay){
					if(config_otp && !otp){
						result = await order.checkPswd();
					}
					if(!config_otp){
						result = await order.checkPswd();
					}
				}
				if(result){
					super._onClickPay();
				}
			}

			// async _setValue(val) {
			// 	let config = this.env.pos.config;
			// 	let config_otp = config.one_time_valid;
			// 	let result = true;
			// 	let otp =this.env.pos.otp;
			// 	let order = this.env.pos.get_order();

			// 	if(val == 'remove'){
			// 		if(config.order_line_delete && check_dol){
			// 			if(config_otp && !otp){
			// 				result = await order.checkPswd();
			// 			}
			// 			if(!config_otp){
			// 				result = await order.checkPswd();

			// 			}
			// 		}
			// 	}
			// 	if(val != 'remove'){
			// 		if(config_otp && !otp){
			// 			if (this.currentOrder.get_selected_orderline()) {
			//                 if (config.qty_detail && this.env.pos.numpadMode === 'quantity') {
			//                     result = await order.checkPswd();
			//                     const result1 = this.currentOrder.get_selected_orderline().set_quantity(val);
			//                     if (!result1) NumberBuffer.reset();
			//                 } else if (config.discount_app && this.env.pos.numpadMode === 'discount') {
			//                     result = await order.checkPswd();
			//                     this.currentOrder.get_selected_orderline().set_discount(val);
			//                 } else if (config.price_change && this.env.pos.numpadMode === 'price') {
			//                     var selected_orderline = this.currentOrder.get_selected_orderline();
			//                     result = await order.checkPswd();
			//                     selected_orderline.price_manually_set = true;
			//                     selected_orderline.set_unit_price(val);
			//                 }
			//             }
			// 		}
			// 		if(!config_otp){
			//             if (this.currentOrder.get_selected_orderline()) {
			//                 if (config.qty_detail && this.env.pos.numpadMode === 'quantity') {
			//                     result = await order.checkPswd();
			//                     const result1 = this.currentOrder.get_selected_orderline().set_quantity(val);
			//                     if (!result1) NumberBuffer.reset();
			//                 } else if (config.discount_app && this.env.pos.numpadMode === 'discount') {
			//                     result = await order.checkPswd();
			//                     this.currentOrder.get_selected_orderline().set_discount(val);
			//                 } else if (config.price_change && this.env.pos.numpadMode === 'price') {
			//                     var selected_orderline = this.currentOrder.get_selected_orderline();
			//                     result = await order.checkPswd();
			//                     selected_orderline.price_manually_set = true;
			//                     selected_orderline.set_unit_price(val);
			//                 }
			//             }
			// 		}
			// 	}
			// 	if(result){
			// 		super._setValue(val);
			// 	}
	  //       }
	};
	Registries.Component.extend(ProductScreen, BiProductScreen);

	return ProductScreen;

});
