odoo.define("3mit_print_server.DiscountButton", function (require) {
  "use strict";

  const DiscountButton = require("pos_discount.DiscountButton");
  const Registries = require("point_of_sale.Registries");

  const ExtendedDiscountButton = (DiscountButton) =>
    class extends DiscountButton {
      async apply_discount(pc) {
        let order = this.env.pos.get_order()
        order.pc_discount = pc;
        await super.apply_discount(pc);
      }
    };

  Registries.Component.extend(DiscountButton, ExtendedDiscountButton);

  return ExtendedDiscountButton;
});
