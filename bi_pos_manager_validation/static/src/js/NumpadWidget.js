
odoo.define('bi_pos_manager_validation.NumpadWidgetValidation', function(require) {
	'use strict';

	const PosComponent = require('point_of_sale.PosComponent');
	const ProductScreen = require('point_of_sale.ProductScreen');
	const NumpadWidget = require('point_of_sale.NumpadWidget');
	const Registries = require('point_of_sale.Registries');
	let check_dol = true;


	const NumpadWidgetValidation = (NumpadWidget) =>
		class extends NumpadWidget {
			setup() {
            	super.setup();
			}

			async sendInput(key) {
                let config = this.env.pos.config;
                let config_otp = config.one_time_valid;
                let result = true;
                let otp =this.env.pos.otp;
                let order = this.env.pos.get_order();

	            if(key === "Backspace"){
	            	if(config.order_line_delete && check_dol){
                        if(config_otp && !otp){
                            result = await order.checkPswd();
                        }
                        if(!config_otp){
                            result = await order.checkPswd();
                        }
                    }else if(config.qty_detail && check_dol){
                        if(config_otp && !otp){
                            result = await order.checkPswd();
                        }
                        if(!config_otp){
                            result = await order.checkPswd();
                        }
                    }
	            }
	            if(result){
                    super.sendInput(key);
                }
	        }

			async changeMode(mode) {
                var self = this;
				let order = this.env.pos.get_order();
				let config = this.env.pos.config;
				let config_otp = config.one_time_valid;
				let otp = this.env.pos.otp;
				let result = true;

            	if(config_otp && !otp){
					if (config.qty_detail && mode === 'quantity') {
	                    result = await order.checkPswd();
	                } else if (config.discount_app && mode === 'discount') {
	                    result = await order.checkPswd();
	                } else if (config.price_change && mode === 'price') {
	                    result = await order.checkPswd();
	                }
				}

				if(!config_otp){
					if (config.qty_detail && mode === 'quantity') {
	                    result = await order.checkPswd();
	                } else if (config.discount_app && mode === 'discount') {
	                    result = await order.checkPswd();
	                } else if (config.price_change && mode === 'price') {
	                    result = await order.checkPswd();
	                }
				}

				if(result){
	                super.changeMode(mode);
				}
            }

	};
	Registries.Component.extend(NumpadWidget, NumpadWidgetValidation);

	return NumpadWidget;

});
