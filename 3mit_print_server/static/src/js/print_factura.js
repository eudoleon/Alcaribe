"use strict";

console.log("***** nota-credito");
/*
Agrega opción para imprimir nota de credito en  point_of_sale.view_pos_pos_form
*/
odoo.define("3mit_print_server.factura", function (require) {
  console.log("******** factura define");

  var FormView = require("web.FormView");
  var FormController = require("web.FormController");
  var view_registry = require("web.view_registry");

  var CustomFormController = FormController.extend({
    _saveRecord: function (recordID, options) {
      const _super = this._super;
      if (this.canBeSaved()) {
        return this.printFactura().then((rs) => {
          return _super.apply(this, arguments).then((rs) => {
            return true;
          });
        });
      } else {
        return Promise.reject("No print");
      }
    },

    printFactura: function () {
      const record = this.model.get(this.handle);

      return (
        // obtiene info para imprimir
        this._rpc({
          model: "pos.print.factura",
          method: "getTicket",
          args: [record.context.active_id],
          //args: [{ numFactura, fechaFactura, serialImpresora }],
          context: this.initialState.context,
        })
          .then((rs) => {
            return this.print_3mit(rs);
          })
          .then((rs) => {
            return this._rpc({
              model: "pos.order",
              method: "setTicket",
              args: [this.initialState.context.active_id, rs.data],
            });
          })
          .catch((err) => {
            this.displayNotification({
              type: "error",
              title: "Ticket Fiscal",
              message: err.statusText,
            });
            return Promise.reject();
          })
      );
    },
    async print_3mit({ printer_host, ticket }) {
      //
      const printer_valid = await this.validate_3mitServer(printer_host);
      if (!printer_valid)
        return Promise.reject({
          statusText: "No se pudo imprimir en " + printer_host,
        });
      //

      ticket = JSON.parse(ticket);
      const receipt = { ...ticket };
      receipt.pagos = [];
      ticket.pagos.forEach((r) => {
        const p = receipt.pagos.find((f) => f.codigo == r.codigo);
        if (!p) {
          receipt.pagos.push(r);
        } else {
          p.monto += r.monto;
        }
      });
      //

      return $.post({
        url: `http://${printer_host}/api/imprimir/factura`,
        data: JSON.stringify(receipt),
        contentType: "application/json",
        dataType: "json",
        timeout: 20000, //20 segundos para imprimir
      })
        .then((data) => {
          console.log("3mit_send_to_printer: Ok", data);
          return data;
        })
        .fail((err) => {
          console.log("3mit_send_to_printer: Error", err);
          return Promise.reject("No se pudo imprimir en " + printer_host);
        });
    },
    // solo verifica si el print_server está on-line
    async validate_3mitServer(printer_host) {
      if (window._debug) return true;

      return new Promise((resolve, reject) => {
        $.get(`http://${printer_host}/api/ping`)
          .then(() => {
            resolve(true);
          })
          .catch(async () => {
            this.displayNotification({
              type: "error",
              title: "No se encontró el servicio de impresión",
              body: "Revisar configuración de " + printer_host,
            });

            resolve(false);
          });
      });
    },
  });

  var factura = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
      Controller: CustomFormController,
    }),
  });
  view_registry.add("pos_printer_factura", factura);
});
