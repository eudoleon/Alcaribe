"use strict";

console.log("***** nota-credito");
/*
Agrega opción para imprimir nota de credito en  point_of_sale.view_pos_pos_form
*/
odoo.define("3mit_print_server.nota_credito", function (require) {
  console.log("******** nota_credito define");

  var FormView = require("web.FormView");
  var FormController = require("web.FormController");
  var view_registry = require("web.view_registry");

  var CustomFormController = FormController.extend({
    _saveRecord: function (recordID, options) {
      const _super = this._super;
      if (this.canBeSaved()) {
        return this.printNC().then((rs) => {
          return _super.apply(this, arguments).then((rs) => {
            return rs;
          });
        });
      } else {
        return Promise.reject("No print");
      }
    },

    printNC: function () {
      const record = this.model.get(this.handle);
      const numFactura = record.data.numFactura;
      const fechaFactura = moment(record.data.fechaFactura._i).format(
        "YYYY-MM-DD HH:mm"
      );
      const serialImpresora = record.data.serialImpresora;

      return (
        // obtiene info para imprimir
        this._rpc({
          model: "pos.print.notacredito",
          method: "getTicket",
          //args: [record.res_id],
          args: [{ numFactura, fechaFactura, serialImpresora }],
          context: this.initialState.context,
        })
          .then(this.print_3mit)
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
    print_3mit({ printer_host, ticket }) {
      return $.post({
        url: `http://${printer_host}/api/imprimir/nota-credito`,
        data: ticket,
        contentType: "application/json",
        dataType: "json",
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
    validate_3mitServer(printer_host) {
      if (window._debug) return true;

      return new Promise((resolve, reject) => {
        $.get(`http://${printer_host}/api/ping`)
          .then(() => {
            resolve(true);
          })
          .catch(async () => {
            await this.showPopup("ErrorPopup", {
              title: "No se encontró el servicio de impresión",
              body:
                "Revisar configuración de " + this.env.pos.config.printer_host,
            });

            resolve(false);
          });
      });
    },
  });

  var nota_credito = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
      Controller: CustomFormController,
    }),
  });
  view_registry.add("pos_printer_nota_credito", nota_credito);
});
