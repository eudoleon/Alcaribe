odoo.define('bi_pos_manager_validation.pos', function (require) {
'use strict';

	var { PosGlobalState,Order } = require('point_of_sale.models');
	const Registries = require('point_of_sale.Registries');
	const { Gui } = require('point_of_sale.Gui');
	var core = require('web.core');
	var _t = core._t;

	const PosHomePosGlobalState = (PosGlobalState) => class PosHomePosGlobalState extends PosGlobalState {
		//@override
	    async _processData(loadedData) {
	        await super._processData(...arguments);
            this.users = loadedData['users'];
	    }
	}
	Registries.Model.extend(PosGlobalState, PosHomePosGlobalState);


	const CustomOrder = (Order) => class CustomOrder extends Order{
		constructor(obj, options) {
			super(...arguments);
			this.pos.otp = false
		}

		async checkPswd(){
			let self = this;
			let res = false;
			const { confirmed, payload } = await Gui.showPopup('NumberPopup', {
				title: _t('Manager Password'),
				isPassword: true,
			});
			if (confirmed) {
				let user_passd;
				let users = self.pos.config.user_id;
				for (let i = 0; i < self.pos.users.length; i++) {
					if (self.pos.users[i].id === users[0]) {
						user_passd = self.pos.users[i].pos_security_pin;
					}
				}
				if (payload == user_passd){
					res =  true;
					self.pos.otp = true;
				}else{
					Gui.showPopup('ErrorPopup', {
						title: _t('Invalid Password'),
						body: _t('Wrong Password'),
					});
					return false;
				}
			}
			return res;
		}
	}
	Registries.Model.extend(Order, CustomOrder);

});
