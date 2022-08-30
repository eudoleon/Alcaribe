odoo.define("3mit_print_server.print_ticket", function (require) {
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

  models.load_fields("res.partner", ["rif"]);

  var utils = require("web.utils");
  var round_di = utils.round_decimals;
  var round_pr = utils.round_precision;

  var fixMoney = (window.fixMoney = function fixMoney(n) {
    return Math.round(n * 100) / 100;
    //return round_di(n, 2);
  });

  const ExtendReceiptScreen = (ReceiptScreen) =>
    class extends ReceiptScreen {
      mounted() {
        super.mounted(...arguments);
        $(".button.next", this.el).hide();
      }

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

      // devuelve data reportada por la impresora
      async print_3mit(order) {
        const json = this._3mit_prepare_json(order);
        const printer_host = this.env.pos.config.printer_host;

        try {
          const rs = await $.post({
            url: `http://${printer_host}/api/imprimir/factura`,
            data: JSON.stringify(json),
            contentType: "application/json",
            dataType: "json",
            timeout: 20000, //20 segundos para imprimir
          });
          console.log("3mit_send_to_printer:", rs);
          if (rs.status == "OK") {
            return rs.data;
          } else {
            return rs.status + ":" + rs.message;
          }
        } catch (err) {
          await this.showPopup("ErrorPopup", {
            title: "Ticket Fiscal",
            body: err.statusText,
          });
          console.log("3mit_send_to_printer: Error", err);
          return err.statusText;
        }
      }

      _3mit_prepare_json(order) {
        var json = order.export_for_printing();
        //
        if (!json.client) json.client = {};
        var receipt = {
          backendRef: json.name || null,
          idFiscal:
            json.client.vat ||
            json.client.rif ||
            json.client.identification_id ||
            null,
          razonSocial: json.client.name || null,
          direccion: json.client.street || null,
          telefono: json.client.phone || null,
        };
        // items-products/
        receipt.items = json.orderlines.map((r) => {
          return {
            nombre: r.product_name,
            cantidad: r.quantity,
            precio: r.price,
            impuesto: r.iva_rate,
            descuento: r.discount,
            tipoDescuento: "p",
          };
        });

        const bi_igtf = order.bi_igtf || 0;
        receipt.pagos = [];
        // consolida por código en la impresora
        const pagos = json.paymentlines.map((r) => {
          return {
            codigo: r.fiscal_print_code || (r.dolar_active ? "20" : "01"),
            nombre: r.fiscal_print_name || r.payment_method,
            monto: fixMoney(r.amount),
          };
        });
        pagos.forEach((r) => {
          const p = receipt.pagos.find((f) => f.codigo == r.codigo);
          if (!p) {
            receipt.pagos.push(r);
          } else {
            p.monto += r.monto;
          }
        });
        //

        return receipt;
      }
      //
      async handleAutoPrint() {
        if (this._shouldAutoPrint()) {
          await this.printReceipt();
          if (this.currentOrder._printed && this._shouldCloseImmediately()) {
            this.orderDone();
          }
        }
      }
      async printReceipt() {
        const b3Mit = await this.validate_3mitServer();
        if (!b3Mit) {
          return;
        }

        $(".button.next", this.el).hide();

        const isPrinted = await this._printReceipt();

        if (isPrinted) {
          this.currentOrder._printed = true;
          $(".button.next", this.el).show();
        } else {
          $(".button.next", this.el).hide();
        }
      }
      //

      async _printReceipt() {
        const order = this.currentOrder;

        if (order._printed) {
          await this.showPopup("ErrorPopup", {
            title: "Ticket Fiscal",
            body: "El ticket ya fue enviado a la impresora.",
          });
          return true;
        }

        const dataFiscal = await this.print_3mit(order);

        if (!dataFiscal || !dataFiscal.nroFiscal) {
          await this.showPopup("ErrorPopup", {
            title: "Error imprimiendo",
            body:
              "Revise la impresora y reintente imprimir para continuar\n\n" +
              dataFiscal,
          });
          console.log("Error obteniendo dataFiscal", dataFiscal);
          return false;
        }
        // Se imprimió y se obtuvo respuesta de la impresora en dataFiscal
        order._printed = true;
        //
        try {
          await this.rpc({
            model: "pos.order",
            method: "setTicket",
            args: [
              false,
              {
                orderUID: order.uid,
                nroFiscal: dataFiscal.nroFiscal,
                fecha: dataFiscal.fecha,
                serial: dataFiscal.serial,
              },
            ],
          });
        } catch (err) {
          await this.showPopup("ErrorPopup", {
            title: "Error de backend",
            body: "No se pudo guardar la información fiscal",
          });
        } finally {
          // Devuelve true si pudo imprimirse ,aunque no se pueda guardar la info fiscal
          return true;
        }
      }

      async validate_3mitServer() {
        if (window._debug) return true;

        const printer_host = this.env.pos.config.printer_host;

        return new Promise((resolve, reject) => {
          $.get({
            url: `http://${printer_host}/api/ping`,
            timeout: 2000,
          })
            .then(() => {
              resolve(true);
            })
            .catch(async () => {
              await this.showPopup("ErrorPopup", {
                title: "Servicio de Impresión",
                body: `No se encontró el servicio de impresión ${printer_host}.\n\n Revisar configuración o reiniciar el servicio`,
              });
              resolve(false);
            });
        });
      }
    };
  Registries.Component.extend(ReceiptScreen, ExtendReceiptScreen);

  const ExtendPaymentScreen = (PaymentScreen) =>
    class extends PaymentScreen {
      async _isOrderValid(isForceValidate) {
        const ret = await super._isOrderValid(isForceValidate);
        const isPrintServerOnline = await this.validate_3mitServer();

        this.currentOrder.ticket_fiscal = null;

        // para forzar la creación de la factura
        this.to_invoice = true;

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
                body: "Revisar configuración de la caja",
              });

              resolve(false);
            });
        });
      }
    };
  Registries.Component.extend(PaymentScreen, ExtendPaymentScreen);

  models.Order = models.Order.extend({
    initialize: function () {
      console.log("------ order.initialize");
      _Order.initialize.apply(this, arguments);
      this.ticket_fiscal = null;
      this.serial_fiscal = null;
      this.fecha_fiscal = null;
    },

    init_from_JSON: function (json) {
      this.ticket_fiscal = json.ticket_fiscal;
      this.serial_fiscal = json.serial_fiscal;
      this.fecha_fiscal = json.fecha_fiscal;
      _Order.init_from_JSON.call(this, json);
    },

    export_as_JSON: function () {
      var data = _Order.export_as_JSON.apply(this, arguments);
      data.ticket_fiscal = this.ticket_fiscal;
      data.serial_fiscal = this.serial_fiscal;
      data.fecha_fiscal = this.fecha_fiscal;
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
