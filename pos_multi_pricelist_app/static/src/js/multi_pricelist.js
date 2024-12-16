odoo.define('pos_multi_pricelist_app.multi_pricelist', function(require) {
	"use strict";

	var { PosGlobalState, Product, Order } = require('point_of_sale.models');
	const Registries = require('point_of_sale.Registries');
	const core = require('web.core');
	const utils = require('web.utils');
	const _t = core._t;
	const round_di = utils.round_decimals;
	const round_pr = utils.round_precision;
	const field_utils = require('web.field_utils');
	var config_currency;
	var config_id;
	var my_pos = "";

	const PosHomePosGlobalState = (PosGlobalState) => class PosHomePosGlobalState extends PosGlobalState {
	    async _processData(loadedData) {
	        await super._processData(...arguments);
			this._loadProductPricelistItem(loadedData['product.pricelist.item'])
            this._loadResCurrency(loadedData['currencies'])
	    }  

	    _loadProductPricelistItem(pricelist_items){
	    	var self = this;
	    	self.pricelist_items = pricelist_items;
			var pricelist_by_id = {};

			_.each(self.pricelists, function (pricelist) {
				pricelist_by_id[pricelist.id] = pricelist;
			});

			_.each(pricelist_items, function (item) {
				var pricelist = pricelist_by_id[item.pricelist_id[0]];
				pricelist.items.push(item);
				item.base_pricelist = pricelist_by_id[item.base_pricelist_id[0]];
			});
	    }

	    _loadResCurrency(currencies){
	    	var self = this;
	    	self.currency = currencies[0];
			self.company_currency = currencies[1];
			for (var i = 0; i < currencies.length; i++) {
				if(currencies[i].id == self.config.currency_id[0]){
					self.currency = currencies[i];
					break;
				}
			}
			for (var i = 0; i < currencies.length; i++) {
				if(currencies[i].id == self.company.currency_id[0]){
					self.company_currency = currencies[i];
					break;
				}
			}
			self.currency['decimals'] = 2;
			if (self.currency.rounding > 0 && self.currency.rounding < 1) {
				self.currency.decimals = Math.ceil(Math.log(1.0 / self.currency.rounding) / Math.log(10));
			} else {
				self.currency.decimals = 0;
			}
			config_currency = self.config.currency_id[0];
			config_id = self.config.id;
			self.currencies = currencies;
	    }
	}
	Registries.Model.extend(PosGlobalState, PosHomePosGlobalState);

	const PosProduct = (Product) => class PosProduct extends Product {
		get_price(pricelist, quantity, price_extra){
	        var self = this;


	        var date = moment();
	        if(this.company_id){
	        	var amount = pricelist.rate
	        }else{
				var amount = pricelist.converted_currency
	        }

	        // In case of nested pricelists, it is necessary that all pricelists are made available in
	        // the POS. Display a basic alert to the user in this case.
	        if (!pricelist) {
	            alert(_t(
	                'An error occurred when loading product prices. ' +
	                'Make sure all pricelists are available in the POS.'
	            ));
	        }

	        var category_ids = [];
	        var get_rates = {};
	        var category = this.categ;
	        while (category) {
	            category_ids.push(category.id);
	            category = category.parent;
	        }

	        var pricelist_items = _.filter(self.applicablePricelistItems[pricelist.id], function (item) {
	            return (! item.categ_id || _.contains(category_ids, item.categ_id[0])) &&
	                   (! item.date_start || moment.utc(item.date_start).isSameOrBefore(date)) &&
	                   (! item.date_end || moment.utc(item.date_end).isSameOrAfter(date));
	        });

	        var price = self.lst_price;
			var pricelist_currency = pricelist.currency_id[0];

			// if(my_pos.config.currency_id[0] != pricelist_currency)
			// {
			var new_rate = price;
			if(amount !=0){
				new_rate = (amount * price);
			}
			price =  new_rate;
				
			// }
			
	        _.find(pricelist_items, function (rule) {
	            if (rule.min_quantity && quantity < rule.min_quantity) {
	                return false;
	            }

				if (rule.base === 'pricelist' && rule.base_pricelist_id){
					price = self.get_price(rule.base_pricelist, quantity);
					_.each(self.pos.currencies, function (line) {
						if (line.id == rule.currency_id[0]){
							get_rates[line.id] = line.rate;	
						}
						if (line.id == rule.base_pricelist.currency_id[0]){
							get_rates[line.id] = line.rate;
						}
						if (get_rates[rule.currency_id[0]] != undefined){
							var res = get_rates[rule.currency_id[0]] / get_rates[rule.base_pricelist.currency_id[0]];
							price = price * res;
						}
					});
				}else if (rule.base === 'pricelist') {
	                let base_pricelist = _.find(self.pos.pricelists, function (pricelist) {
	                    return pricelist.id === rule.base_pricelist_id[0];});
	                if (base_pricelist) {
	                    price = self.get_price(base_pricelist, quantity);
	                }
	            } else if (rule.base === 'standard_price') {
	                price = self.standard_price;
	            }

	            if (rule.compute_price === 'fixed') {
	                price = rule.fixed_price;
	                return true;
	            } else if (rule.compute_price === 'percentage') {
	                price = price - (price * (rule.percent_price / 100));
	                return true;
	            } else {
	                var price_limit = price;
	                price = price - (price * (rule.price_discount / 100));
	                if (rule.price_round) {
	                    price = round_pr(price, rule.price_round);
	                }
	                if (rule.price_surcharge) {
	                    price += rule.price_surcharge;
	                }
	                if (rule.price_min_margin) {
	                    price = Math.max(price, price_limit + rule.price_min_margin);
	                }
	                if (rule.price_max_margin) {
	                    price = Math.min(price, price_limit + rule.price_max_margin);
	                }
	                return true;
	            }

	            return false;
	        });

	        return price;
	    }

	}
	Registries.Model.extend(Product, PosProduct);

	const PosOrder = (Order) => class PosOrder extends Order {
		constructor(obj, options) {
			super(...arguments);
			var self = this;
			if (!options.json) {
				for (var i = 0; i < self.pos.currencies.length; i++) {
					if(self.pos.currencies[i].id == this.pos.default_pricelist.currency_id[0]){
						self.pos.currency = self.pos.currencies[i];
						break;
					}
				}
			}
		}

		set_pricelist (pricelist) {
	        var self = this;
	        this.pricelist = pricelist;

			for (var i = 0; i < self.pos.currencies.length; i++) {
				if(self.pos.currencies[i].id == pricelist.currency_id[0]){
					self.pos.currency = self.pos.currencies[i];
					break;
				}
			}

	        var lines_to_recompute = _.filter(this.get_orderlines(), function (line) {
	            return ! line.price_manually_set;
	        });
	        _.each(lines_to_recompute, function (line) {
	            line.set_unit_price(line.product.get_price(self.pricelist, line.get_quantity(), line.get_price_extra()));
	            self.fix_tax_included_price(line);
	        });
	    }

        export_as_JSON() {
            const json = super.export_as_JSON(...arguments);
			json.new_currency = this.pos.currency;
			my_pos = this.pos;
            return json;
        }

        init_from_JSON(json){
			super.init_from_JSON(...arguments);
			var self = this
			var n_crncy = {};
			var config_currencies = [];
			for (var i = 0; i < self.pos.pricelists.length; i++) {
				config_currencies.push(self.pos.pricelists[i].currency_id[0])
			}
			for (var i = 0; i < self.pos.currencies.length; i++) {
				if (json.new_currency != undefined){
					if(self.pos.currencies[i].id == json.new_currency.id){
						n_crncy= self.pos.currencies[i];
						break;
					}
				}
			}
			var have = config_currencies.includes(json.new_currency);

			if(have)
			{
				this.new_currency = n_crncy;
				this.pos.currency = n_crncy;
			}
			else{
				this.pricelist = this.pos.default_pricelist;
				this.new_currency = this.pos.currency;
			}	
		}
    }
	Registries.Model.extend(Order, PosOrder);
});
