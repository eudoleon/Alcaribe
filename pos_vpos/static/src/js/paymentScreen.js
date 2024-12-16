odoo.define("pos_vpos.PaymentScreen", function (require) {
  "use strict";

  const PaymentScreen = require("point_of_sale.PaymentScreen");

  const Registries = require("point_of_sale.Registries");

  const VposPaymmentScreen = (PaymentScreen) =>
    class extends PaymentScreen {
      get_payment_methods() {
        if (this.currentOrder.get_change() > 0) {
          return this.payment_methods_from_config.filter(
            (r) => r.valid_to_change
          );
        } else {
          return this.payment_methods_from_config;
        }
      }
    };

  Registries.Component.extend(PaymentScreen, VposPaymmentScreen);

  return VposPaymmentScreen;
});
