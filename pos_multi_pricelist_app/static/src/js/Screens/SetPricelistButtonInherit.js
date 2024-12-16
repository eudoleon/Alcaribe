odoo.define('pos_multi_pricelist_app.SetPricelistButtonInherit', function(require) {
	'use strict';

	const PosComponent = require('point_of_sale.PosComponent');
	const ProductScreen = require('point_of_sale.ProductScreen');
	const Registries = require('point_of_sale.Registries');
	const SetPricelistButton = require('point_of_sale.SetPricelistButton');
	var converted_amount = 0.0;

	const PosPricelistButton = (SetPricelistButton) =>
		class extends SetPricelistButton {
			async onClick() {
				// Create the list to be passed to the SelectionPopup.
	            // Pricelist object is passed as item in the list because it
	            // is the object that will be returned when the popup is confirmed.
	            const selectionList = this.env.pos.pricelists.map(pricelist => ({
	                id: pricelist.id,
	                label: pricelist.name,
	                isSelected: pricelist.id === this.currentOrder.pricelist.id,
	                item: pricelist,
	            }));

	            const { confirmed, payload: selectedPricelist } = await this.showPopup(
	                'SelectionPopup',
	                {
	                    title: this.env._t('Select the pricelist'),
	                    list: selectionList,
	                }
	            );

	            if (confirmed) {
	            	var order = this.currentOrder;
					var new_currency = {};

					for (var i = 0; i < this.env.pos.currencies.length; i++) {
						if(this.env.pos.currencies[i].id == selectedPricelist.currency_id[0]){
							new_currency = this.env.pos.currencies[i];
							break;
						}
					}

					if (new_currency.rounding > 0 && new_currency.rounding < 1) {
						new_currency.decimals = Math.ceil(Math.log(1.0 / new_currency.rounding) / Math.log(10));
					} else {
						new_currency.decimals = 0;
					}
					converted_amount = new_currency['converted_currency'];
					this.env.pos.currency = new_currency;
					order.new_currency = new_currency;
	                this.currentOrder.set_pricelist(selectedPricelist);
	            }
			}
		};
	Registries.Component.extend(SetPricelistButton, PosPricelistButton);

	return PosPricelistButton;

});