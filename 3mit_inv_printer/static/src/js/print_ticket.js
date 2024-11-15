odoo.define("3mit_pos_printer.print_ticket", function (require) {
  "use strict";

  //const screens = require("point_of_sale.screens");

  const ReceiptScreen = require("point_of_sale.ReceiptScreen");
  const PaymentScreen = require("point_of_sale.PaymentScreen");
  const Registries = require("point_of_sale.Registries");

  const models = require("point_of_sale.models");
  const core = require("web.core");
  const _t = core._t;

  var _Order = models.Order.prototype;
  var _Orderline = models.Orderline.prototype;

  const ExtendReceiptScreen = (ReceiptScreen) =>
    class extends ReceiptScreen {
      _shouldCloseImmediately() {
        const ret = super._shouldCloseImmediately();
        if (ret != undefined) {
          return ret;
        }
        //
        var invoiced_finalized = this.currentOrder.is_to_invoice()
          ? this.currentOrder.finalized
          : true;
        return (
          this.env.pos.config.iface_print_skip_screen && invoiced_finalized
        );
      }

      print_3mit(order) {
        if (window._debug) return Promise.resolve();

        const json = this._3mit_prepare_json(order);
        const printer_host = this.env.pos.config.printer_host;

        return new Promise((resolve, reject) => {
          $.post({
            url: `http://${printer_host}/api/imprimir/factura`,
            data: JSON.stringify(json),
            contentType: "application/json",
            dataType: "json",
          })
            .then((data) => {
              console.log("3mit_send_to_printer: Ok", data);
              resolve(data);
            })
            .catch((err) => {
              console.log("3mit_send_to_printer: Error", err);
              reject(err);
            });
        });
      }

      _3mit_prepare_json(order) {
        var json = order.export_for_printing();
        //
        if (!json.client) json.client = {};
        var receipt = {
          backendRef: json.name,
          idFiscal: json.client.vat || json.client.identification_id || "",
          razonSocial: json.client.name,
          direccion: json.client.address || json.client.city,
          telefono: json.client.phone,
        };
        receipt.items = json.orderlines.map((r) => {
          return {
            nombre: r.product_name,
            cantidad: r.quantity,
            precio: r.price,
            impuesto: r.iva_rate,
          };
        });
        return receipt;
      }

      async _printReceipt() {
        if (!this.env.pos.config.printer_host) {
          return await super._printReceipt();
        }
        const order = this.currentOrder;

        if (order._printed) {
          await this.showPopup("ErrorPopup", {
            title: "Ticket Fiscal",
            body: "El ticket ya fue enviado a la impresora.",
          });
          return Promise.resolve();
        }
        return this.print_3mit(order)
          .then((data) => {
            order._printed = true;
          })
          .catch(async (err) => {
            await this.showPopup("ErrorPopup", {
              title: "No se Envió Ticket Fiscal",
              body: "Error en " + this.env.pos.config.printer_host,
            });
            throw err;
          });
      }
    };
  Registries.Component.extend(ReceiptScreen, ExtendReceiptScreen);

  const ExtendPaymentScreen = (PaymentScreen) =>
    class extends PaymentScreen {
      async _isOrderValid(isForceValidate) {
        const ret = await super._isOrderValid(isForceValidate);
        const isPrintServerOnline = await this.validate_3mitServer();

        this.currentOrder.ticket_fiscal = "f"; //TODO: Revisar objeto de este campo

        return ret && isPrintServerOnline;
      }
      // solo verifica si el print_server está on-line
      validate_3mitServer() {
        if (window._debug) return true;

        const printer_host = this.env.pos.config.printer_host;

        return new Promise((resolve, reject) => {
          $.get(`http://${printer_host}/api/ping`)
            .then(() => {
              resolve(true);
            })
            .catch(async () => {
              await this.showPopup("ErrorPopup", {
                title: "No se encontró el servicio de impresión",
                body:
                  "Revisar configuración de " +
                  this.env.pos.config.printer_host,
              });

              resolve(false);
            });
        });
      }
    };
  Registries.Component.extend(PaymentScreen, ExtendPaymentScreen);

  models.Order = models.Order.extend({
    initialize: function () {
      _Order.initialize.apply(this, arguments);
      this.ticket_fiscal = null;
    },

    init_from_JSON: function (json) {
      this.ticket_fiscal = json.ticket_fiscal;
      _Order.init_from_JSON.call(this, json);
    },

    export_as_JSON: function () {
      var data = _Order.export_as_JSON.apply(this, arguments);
      data.ticket_fiscal = this.ticket_fiscal;
      return data;
    },

    export_for_printing: function () {
      var receipt = _Order.export_for_printing.apply(this, arguments);
      // agrega info de cliente
      receipt.client = this.get_client();
      //
      return receipt;
    },
  });

  models.Orderline = models.Orderline.extend({
    export_for_printing: function () {
      var line = _Orderline.export_for_printing.apply(this, arguments);
      // agrega info de IVA
      var taxes = this.get_taxes();
      if (taxes.length === 0) {
        line.iva_rate = 0;
      } else {
        line.iva_rate = taxes[0].amount;
      }
      //
      return line;
    },
  });
});
