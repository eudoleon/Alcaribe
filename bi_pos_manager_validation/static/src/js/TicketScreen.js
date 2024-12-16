odoo.define('bi_pos_manager_validation.BiTicketScreen', function(require) {
	'use strict';

	const TicketScreen = require('point_of_sale.TicketScreen');
	const Registries = require('point_of_sale.Registries');
	let check_do = true;

	const BiTicketScreen = (TicketScreen) =>
		class extends TicketScreen {
			setup() {
            	super.setup();
			}

			async _onDeleteOrder(order) {
				let self = this;
				let config = this.env.pos.config;
				let config_otp = config.one_time_valid;
				let result = true;
				let otp =this.env.pos.otp;
				let odr = this.env.pos.get_order();

				if(config.order_delete && check_do){
					if(config_otp && !otp){
						result = await odr.checkPswd();
					}
					if(!config_otp){
						result = await odr.checkPswd();
					}
				}

				if(result){
					super._onDeleteOrder(order);
				}
			}
	};
	Registries.Component.extend(TicketScreen, BiTicketScreen);

	return TicketScreen;

});
