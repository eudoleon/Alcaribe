odoo.define('mai_pos_dual_currency.models', function(require) {
	"use strict";

	var models = require('point_of_sale.models');
	var screens = require('point_of_sale.ProductScreen');
	var core = require('web.core');
	const { Gui } = require('point_of_sale.Gui');
	var popups = require('point_of_sale.ConfirmPopup');
	var QWeb = core.qweb;
	var utils = require('web.utils');
	var round_pr = utils.round_precision;
	var _t = core._t;

	models.load_fields('pos.payment.method', ['pago_usd'])

	var OrderSuper = models.Order;
	models.Order = models.Order.extend({

		init: function(parent, options) {
			var self = this;
			this._super(parent,options);
		},

		add_paymentline: function(payment_method) {
			this.assert_editable();
			if (this.electronic_payment_in_progress()) {
				return false;
			} else {
				var newPaymentline = new exports.Paymentline({},{order: this, payment_method:payment_method, pos: this.pos});
				newPaymentline.set_amount(this.get_due());
				this.paymentlines.add(newPaymentline);
				this.select_paymentline(newPaymentline);
				if(this.pos.config.cash_rounding){
				  this.selected_paymentline.set_amount(0);
				  this.selected_paymentline.set_amount(this.get_due());
				}

				if (payment_method.payment_terminal) {
					newPaymentline.set_payment_status('pending');
				}
				return newPaymentline;
			}
		},

		add_paymentline: function(payment_method) {
			this.assert_editable();
			let rate_company = this.pos.config.rate_company;
			if (this.electronic_payment_in_progress()) {
				return false;
			} else {
				var newPaymentline = new models.Paymentline({},{order: this, payment_method:payment_method, pos: this.pos});
				newPaymentline.set_amount(this.get_due());
				if(payment_method.pago_usd){
					newPaymentline.set_usd_amt(this.get_due()/rate_company);
				}
				this.paymentlines.add(newPaymentline);
				this.select_paymentline(newPaymentline);
				if(this.pos.config.cash_rounding){
					this.selected_paymentline.set_amount(0);
			 		this.selected_paymentline.set_amount(this.get_due());
				}

				if (payment_method.payment_terminal) {
					newPaymentline.set_payment_status('pending');
				}
				return newPaymentline;
			}
		},
	
	});

	var PaymentSuper = models.Paymentline;
	models.Paymentline = models.Paymentline.extend({
		init: function(parent,options){
			this._super(parent,options);
			this.usd_amt = this.usd_amt || "";
		},

		export_as_JSON: function() {
			var self = this;
			var loaded = PaymentSuper.prototype.export_as_JSON.call(this);
			loaded.usd_amt = this.usd_amt || 0.0;
			return loaded;
		},

		init_from_JSON: function(json){
			PaymentSuper.prototype.init_from_JSON.apply(this,arguments);
			this.usd_amt = json.usd_amt || "";
		},

		set_usd_amt: function(usd_amt){
			this.usd_amt = usd_amt;
			this.trigger('change',this);
		},

		get_usd_amt: function(){
			return this.usd_amt;
		},
	});

});
