odoo.define('bi_pos_manager_validation.HeaderButtonValidation', function(require) {
	'use strict';

	const PosComponent = require('point_of_sale.PosComponent');
	const HeaderButton = require('point_of_sale.HeaderButton');
	const Registries = require('point_of_sale.Registries');

	let check_close = true;

	const HeaderButtonValidation = (HeaderButton) =>
		class extends HeaderButton {
			setup() {
            	super.setup();
			}

			async onClick() {
				let self = this;
				let config = this.env.pos.config;
				let config_otp = config.one_time_valid;
				let result = true;
				let otp =this.env.pos.otp;
				let order = this.env.pos.get_order();

				if(config.close_pos && check_close){
					if(config_otp && !otp){
						result = await order.checkPswd();
					}
					if(!config_otp){
						result = await order.checkPswd();
					}
				}

				if(result){
					check_close = false;
					super.onClick();
				}
			}
	};
	Registries.Component.extend(HeaderButton, HeaderButtonValidation);

	return HeaderButton;

});
