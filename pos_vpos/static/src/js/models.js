odoo.define("pos_vpos.models", function (require) {
  console.log("pos_vpos.models");
  const { register_payment_method, Payment } = require("point_of_sale.models");
  const PaymentVpos = require("pos_vpos.payment");
  const Registries = require("point_of_sale.Registries");

  register_payment_method("vpos", PaymentVpos);

  const PosVposPayment = (Payment) =>
    class PosVposPayment extends Payment {
      constructor() {
        super(...arguments);
        this.terminalServiceId = this.terminalServiceId || null;
      }
      init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.terminalServiceId = json.terminal_service_id;
      }
      export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.terminal_service_id = this.terminalServiceId;
        return json;
      }
      setTerminalServiceId(id) {
        this.terminalServiceId = id;
      }
    };
  Registries.Model.extend(Payment, PosVposPayment);
});
