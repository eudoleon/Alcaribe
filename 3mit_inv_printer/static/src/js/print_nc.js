"use strict";

console.log("***** nota-credito");
/*
Agrega opción para imprimir nota de credito en  point_of_sale.view_pos_pos_form
*/
odoo.define("3mit_inv_printer.nota_credito", function (require) {
  console.log("******** inv nota_credito define");

  var FormView = require("web.FormView");
  var FormController = require("web.FormController");
  var view_registry = require("web.view_registry");

  const printer_host = "localhost:5000";

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
      const fechaFactura = record.data.fechaFactura;
      // Si necesitas formatear la fecha, asegúrate de que esté en el formato correcto
      const fechaFacturaFormatted = moment(fechaFactura).format("YYYY-MM-DD HH:mm");
      const serialImpresora = record.data.serialImpresora;

      console.log("Datos a enviar al servidor de impresión:", {
        numFactura,
        fechaFactura,
        serialImpresora
      });
      console.log("Fecha de la Factura enviada:", fechaFactura);

      return this.validate_3mitServer(printer_host).then(() => {
        return this._rpc({
          model: "invoice.print.notacredito",
          method: "getTicket",
          args: [{ numFactura, fechaFactura, serialImpresora }],
          context: this.initialState.context,
        })
          .then(this.print_3mit)
          .then((rs) => {
            return this._rpc({
              model: "account.move",
              method: "setTicket",
              args: [this.initialState.context.active_id, rs],
            });
          })
          .catch((err) => {
            this.displayNotification({
              type: "alert",
              title: "Ticket Fiscal",
              message: err,
            });
            return Promise.reject();
          });
      });
    },
    print_3mit({ ticket }) {
      console.log("JSON de ticket enviado a la impresora:", ticket);

      return $.post({
        url: `http://${printer_host}/api/imprimir/nota-credito`,
        data: ticket,
        contentType: "application/json",
        dataType: "json",
      })
        .then((data) => {
          console.log("3mit_send_to_printer: Ok", data);
          console.log("Datos enviados a la impresora fiscal:", data);
          return data;
        })
        .catch((err) => {
          console.log("3mit_send_to_printer: Error", err);
          Promise.reject("No se pudo imprimir en " + printer_host);
        });
    },
    validate_3mitServer(printer_host) {
      if (window._debug) return Promise.resolve(true);

      return $.get(`http://${printer_host}/api/ping`).catch(async () => {
        this.displayNotification({
          type: "error",
          title: "No se encontró el servicio de impresión",
          message: "Revisar configuración de impresora fiscal",
        });
        return Promise.reject();
      });
    },
  });

  var nota_credito = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
      Controller: CustomFormController,
    }),
  });
  view_registry.add("inv_printer_nota_credito", nota_credito);
});
