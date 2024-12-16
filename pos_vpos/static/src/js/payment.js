odoo.define("pos_vpos.payment", function (require) {
  "use strict";

  console.log("pos_vpos.payment");

  var core = require("web.core");
  var rpc = require("web.rpc");
  var PaymentInterface = require("point_of_sale.PaymentInterface");
  const { Gui } = require("point_of_sale.Gui");

  var _t = core._t;

  var PaymentVpos = PaymentInterface.extend({
    send_payment_request: async function (cid) {
      this._super.apply(this, arguments);
      return this._vpos_payment();
    },
    send_payment_cancel: function () {
      this._super.apply(this, arguments);
      return Promise.reject();
    },

    /********** */

    prepareCedula(partner) {
      try {
        return (partner.identity_card || partner.identification_id || partner.vat || null).replace(
          /\D/g,
          ""
        );
      } catch (e) {
        return "";
      }
    },


    async _vpos_payment() {
      function isValidToChange(payment_method) {
        if (payment_method.valid_to_change == "undefined") {
          return true;
        }
        return payment_method.valid_to_change;
      }

      var order = this.pos.get_order();
      var pay_line = order.selected_paymentline;

      if (!isValidToChange(this.payment_method) && pay_line.amount <= 0) {
        this._show_error(
          _t("Cannot process transactions with zero or negative amount.")
        );
        return Promise.resolve(false);
      }

      var partner = order.get_partner();
      if (!partner) {
        this._show_error(_t("El Cliente debe estar Seleccionado."));
        return Promise.resolve(false);
      }

      var amount = Math.abs(Math.round(pay_line.get_amount() * 100));
      const cedula = this.prepareCedula(partner);
      if (this.payment_method.vpos_methodType == "compraConCards") {
        const monedas = { USD: 4, VES: 5, EU: 9 };
        var data = {
          accion: "compraConCards",
          cedula: cedula,
          numeroTarjeta: cedula,
          saldoPagar: amount,
          tipoMonedero: monedas["VES"],
        };
        return this._vpos_execute("metodo_cards", data)
          .then(this.vpos_ok)
          .catch((err) => false);
      } else {
        var data = {
          accion: this.payment_method.vpos_methodType,
          montoTransaccion: amount,
          cedula: cedula,
        };
        return this._vpos_execute("metodo", data)
          .then(this.vpos_ok)
          .catch((err) => false);
      }
    },

    async vpos_ok(rs) {
      return true;
    },

    async _vpos_execute(metodo, data) {
      const vpos_restApi = this.pos.config.vpos_restApi;
      const params = {
        async: true,
        crossDomain: true,
        method: "POST",
        headers: {
          "content-type": "application/json",
        },
        processData: false,
        url: `${vpos_restApi}/vpos/${metodo}`,
        data: JSON.stringify(data),
      };
      return new Promise((resolve, reject) => {
        $.ajax(params)
          .then((rs) => {
            if (["00", "100"].indexOf(rs.codRespuesta) > -1) {
              console.log("*** inicio: respuesta del merchant ***");
	      console.log(rs);
	      console.log("*** fin: respuesta del merchant ***");
	      	    
	      return resolve(rs);
            } else {
              this._show_error(rs.mensajeRespuesta);
              return reject(false);
            }
          })
          .fail((err) => {
            this._show_error(_t("Cannot connect with vpos"));
            return reject(false);
          });
      });
    },

    _show_error: function (msg, title) {
      Gui.showPopup("ErrorPopup", {
        title: title || _t("Payment Terminal Error"),
        body: msg,
      });
    },
  });

  return PaymentVpos;
});
