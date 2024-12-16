odoo.define('vzla_currency_rate.CurrencyRate', function (require) {
    'use strict';

    var core = require('web.core');
    var session = require('web.session');
    var SystrayMenu = require('web.SystrayMenu');
    var Widget = require('web.Widget');
    var Qweb = core.qweb;
    var _t = core._t;

    var CurrencyRate = Widget.extend({
        name: 'currency_rate_menu',
        template: 'vzla_currency_rate.CurrencyRate',
        events: {
            "click .o_update_rate": "_onUpdateRateClick",
            "click .o_update_rate_range": "_onUpdateRateRangeClick",
            "click .o_show_rates": "_onShowRatesClick",
            'show.bs.dropdown': '_onCurrencyRateShow',
            'hide.bs.dropdown': '_onCurrencyRateHide',
        },
        start: async function() {
            var self = this;
            await Promise.all([this._super.apply(this, arguments),
            this._getCurrencyRateData()]);
            // self.$('.o_exchange_rate').addClass(self.currency_rate_data['rate']);
            self.$('.o_exchange_rate').text(self.currency_rate_data['rate']);
            self.$('.o_exchange_rate_euro').text(self.currency_rate_data['rate_euro']);
            self.$('.currency_rate_date').text(self.currency_rate_data['date']);
            self.$('.currency_rate_sell').text(self.currency_rate_data['sell']);
            self.$('.currency_rate_buy').text(self.currency_rate_data['buy']);
        },
        _getCurrencyRateData: function() {
            var self = this;
            var dt = new Date();
            return this._rpc({
                model: 'res.currency.rate',
                method: 'get_systray_dict',
                args: [self.id, dt],
                kwargs: {context: session.user_context},
            }).then(function (data) {
                self.currency_rate_data = data;
            })
        },
        _onCurrencyRateShow: function () {
            document.body.classList.add('modal-open');
            this.start();
        },
        _onCurrencyRateHide: function () {
            document.body.classList.remove('modal-open');
        },
        _onUpdateRateClick: async function() {
            await Promise.all([this._onUpdateRatePromise()]);
            this.start();
        },
        _onUpdateRateRangeClick: async function() {
            await Promise.all([this._onUpdateRateRangePromise()]);
            this.start();
            this._onUpdateRateClick();
        },
        _onShowRatesClick: async function() {
            await Promise.all([this._onShowRatesPromise()]);
            this.start();
        },
        _onUpdateRatePromise: function() {
            var self = this;
            return this._rpc({
                model: 'res.company',
                method: 'update_currency_rates_sunat',
                args: [self.id],
                kwargs: {context: session.user_context},
            })
        },
        _onUpdateRateRangePromise: function() {
            var self = this;
            self.do_action({
                name: 'Update range',
                type: 'ir.actions.act_window',
                res_model: 'range.wizard',
                view_type: 'form',
                view_mode: 'form',
                view_id: 'view_range_wizard',
                views: [[false, 'form'],],
                target: 'new'
            });
        },
        _onShowRatesPromise: function() {
            var self = this;
            self.do_action({
                name: _t('Currency rates'),
                type: 'ir.actions.act_window',
                res_model: 'res.currency.rate',
                view_type: 'list',
                view_mode: 'list',
                view_id: 'base.view_currency_rate_tree',
                views: [[false, 'list'],],
                // Se debe obtener el id de la moneda dolares para no
                // tenerlo en duro en el código. Ya que el id de la
                // moneda 'USD' puede cambiar.
                domain: [['currency_id','=', 2]],
                context: {default_currency_id: 2},
                target: 'current'
            });
        },
    });
    CurrencyRate.prototype.sequence = 100;
    SystrayMenu.Items.push(CurrencyRate);

    return CurrencyRate;
});