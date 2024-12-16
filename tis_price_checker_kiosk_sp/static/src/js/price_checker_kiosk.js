odoo.define('tis_price_checker_kiosk_sp.price_checker', function (require) {
"use strict";
setTimeout(function(){ self.$(".o_hr_attendance_PINbox").focus() }, 1000);
setInterval(function(){ this.$(".o_hr_attendance_PINbox").change() }, 1800);
var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var QWeb = core.qweb;

var price_checker = AbstractAction.extend({
    events: {
        "click .o_hr_attendance_back_button": function () { this.do_action(this.next_action, {clear_breadcrumbs: true}); },
        'click .o_hr_attendance_pin_pad_button_0': function() { this.$('.o_hr_attendance_PINbox').val(this.$('.o_hr_attendance_PINbox').val() + 0); },
        'click .o_hr_attendance_pin_pad_button_1': function() { this.$('.o_hr_attendance_PINbox').val(this.$('.o_hr_attendance_PINbox').val() + 1); },
        'click .o_hr_attendance_pin_pad_button_2': function() { this.$('.o_hr_attendance_PINbox').val(this.$('.o_hr_attendance_PINbox').val() + 2); },
        'click .o_hr_attendance_pin_pad_button_3': function() { this.$('.o_hr_attendance_PINbox').val(this.$('.o_hr_attendance_PINbox').val() + 3); },
        'click .o_hr_attendance_pin_pad_button_4': function() { this.$('.o_hr_attendance_PINbox').val(this.$('.o_hr_attendance_PINbox').val() + 4); },
        'click .o_hr_attendance_pin_pad_button_5': function() { this.$('.o_hr_attendance_PINbox').val(this.$('.o_hr_attendance_PINbox').val() + 5); },
        'click .o_hr_attendance_pin_pad_button_6': function() { this.$('.o_hr_attendance_PINbox').val(this.$('.o_hr_attendance_PINbox').val() + 6); },
        'click .o_hr_attendance_pin_pad_button_7': function() { this.$('.o_hr_attendance_PINbox').val(this.$('.o_hr_attendance_PINbox').val() + 7); },
        'click .o_hr_attendance_pin_pad_button_8': function() { this.$('.o_hr_attendance_PINbox').val(this.$('.o_hr_attendance_PINbox').val() + 8); },
        'click .o_hr_attendance_pin_pad_button_9': function() { this.$('.o_hr_attendance_PINbox').val(this.$('.o_hr_attendance_PINbox').val() + 9); },
        'click .o_hr_attendance_pin_pad_button_C': function() { this.$('.o_hr_attendance_PINbox').val(''); },
        'click .o_hr_attendance_pin_pad_button_ok': function() {
            var self = this;
                self._rpc({
                model: 'product.product',
                method: 'get_details',
                args: [self.$('.o_hr_attendance_PINbox').val()],
                }, []).then(function (settings){
                if(settings[0]==false){
                    self.$('div.modal').show();
                    setTimeout(function() {
                          self.$('div.modal').hide();
                    }, 5000);
                }
                if(settings[0]!=false && self.$('.o_hr_attendance_PINbox').val()!=""){
                      for (var i = 0; i < settings.length; i++) {
                        if(settings[i]==false)
                            {
                            settings[i]=""
                            }
                        }
                    self.product_id=settings[0];
                    self.product_name=settings[1];
                    self.product_price=settings[2];
                    self.product_barcode=settings[3];
                    self.default_code=settings[4];
                    self.categ_id=settings[5];
                    self.uom_id=settings[6];
                    self.text_field=""
                    self.$el.html(QWeb.render("PriceCheckerKioskModesp", {widget: self}));
                   }
               else if(settings[0]=false && self.$('.o_hr_attendance_PINbox').val()!=""){
                  for (var i = 0; i < settings.length; i++) {
                    if(settings[i]==false)
                        {
                        settings[i]=""
                        }
                    }
                self.product_id=""
                self.product_name=""
                self.product_price=""
                self.product_barcode=""
                self.default_code=""
                self.text_field=self.$('.o_hr_attendance_PINbox').val()
                self.$el.html(QWeb.render("PriceCheckerKioskModesp", {widget: self}));
               }
                }).then(function () {
                    self.clock_start = setInterval(function() {self.$(".o_hr_attendance_clock").text(new Date().toLocaleTimeString(navigator.language, {hour: '2-digit', minute:'2-digit', second:'2-digit'}));}, 500);
                    // First clock refresh before interval to avoid delay
                    self.$(".o_hr_attendance_clock").show().text(new Date().toLocaleTimeString(navigator.language, {hour: '2-digit', minute:'2-digit', second:'2-digit'}));
                });
        },
        'change .o_hr_attendance_PINbox': function() {
            this.$(".o_hr_attendance_PINbox").focus()
            if(this.$('.o_hr_attendance_PINbox').val()!=""){
                var self = this;
                    self._rpc({
                    model: 'product.product',
                    method: 'get_details',
                    args: [self.$('.o_hr_attendance_PINbox').val()],
                    }, []).then(function (settings){
                    console.log('hola', settings)
                    if(settings[0]!=false && self.$('.o_hr_attendance_PINbox').val()!=""){
                          for (var i = 0; i < settings.length; i++) {
                            if(settings[i]==false)
                                {
                                settings[i]=""
                                }
                            }
                        self.product_id=settings[0];
                        self.product_name=settings[1];
                        self.product_price=settings[2];
                        self.product_barcode=settings[3];
                        self.default_code=settings[4];
                        self.special_price=settings[5];
                        self.currency_id=settings[6];
                        self.uom_id=settings[7];

                        self.text_field=""
                        self.$el.html(QWeb.render("PriceCheckerKioskModesp", {widget: self}));
                       }
                       else if(settings[0]==false && self.$('.o_hr_attendance_PINbox').val()!=""){
                          for (var i = 0; i < settings.length; i++) {
                            if(settings[i]==false)
                                {
                                settings[i]=""
                                }
                            }
                        self.product_id=""
                        self.product_name=""
                        self.product_price=""
                        self.product_barcode=""
                        self.currency_id=""
                        self.special_price=""
                        self.uom_id=""
                        self.default_code=""
                        self.text_field=self.$('.o_hr_attendance_PINbox').val()
                        self.$el.html(QWeb.render("PriceCheckerKioskModesp", {widget: self}));
                        self.$('div.modal').show();
                        setTimeout(function() {
                              self.$('div.modal').hide();
                        }, 5000);
                        self.$('.o_hr_attendance_PINbox').val('')
                       }
                    }).then(function () {
                        self.clock_start = setInterval(function() {self.$(".o_hr_attendance_clock").text(new Date().toLocaleTimeString(navigator.language, {hour: '2-digit', minute:'2-digit', second:'2-digit'}));}, 500);
                        // First clock refresh before interval to avoid delay
                        self.$(".o_hr_attendance_clock").show().text(new Date().toLocaleTimeString(navigator.language, {hour: '2-digit', minute:'2-digit', second:'2-digit'}));
                         self.$(".o_hr_attendance_PINbox").focus()
                    });
                }
            },

    },
    start: function () {
        var self = this;
            self.$el.html(QWeb.render("PriceCheckerKioskModesp", {widget: self}));
            self.start_clock();
    },
    start_clock: function () {
        this.clock_start = setInterval(function() {this.$(".o_hr_attendance_clock").text(new Date().toLocaleTimeString(navigator.language, {hour: '2-digit', minute:'2-digit', second:'2-digit'}));}, 500);
        // First clock refresh before interval to avoid delay
        this.$(".o_hr_attendance_clock").show().text(new Date().toLocaleTimeString(navigator.language, {hour: '2-digit', minute:'2-digit', second:'2-digit'}));
    },
    destroy: function () {
        clearInterval(this.clock_start);
        this._super.apply(this, arguments);
    },
});

core.action_registry.add('price_checker_kiosk_sp', price_checker);

return price_checker;

});
