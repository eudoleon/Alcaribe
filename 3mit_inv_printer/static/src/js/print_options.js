"use strict";

console.log("***** print_options");
odoo.define("3mit_inv_printer.options", function (require) {
  console.log("******** print_options define");

  var FormView = require("web.FormView");
  var FormController = require("web.FormController");
  var view_registry = require("web.view_registry");

  var CustomFormController = FormController.extend({
    on_attach_callback: function () {
      this._super.apply(this, arguments);

      this.printer_host = $("input[name=printer_host]").val();
      $("button#reporteX", this.$el).on("click", this.print_reportX.bind(this));
      $("button#reporteZ", this.$el).on("click", this.print_reportZ.bind(this));
      $("button#reporteZporNumero", this.$el).on(
        "click",
        this.print_reportZporNumero.bind(this)
      );
      $("button#reporteZporFecha", this.$el).on(
        "click",
        this.print_reportZporFecha.bind(this)
      );
      $("button#reporteFacturas", this.$el).on(
        "click",
        this.print_facturas.bind(this)
      );
    },
    print_reportX() {
      this.print_3mit("/api/imprimir/reporte_x");
    },
    print_reportZ() {
      this.print_3mit("/api/imprimir/reporte_z")
        .then((rs) => {
          return this.print_3mit("/api/data_z");
        })
        .then((rs) => {
          return this._rpc({
            model: "datos.zeta.diario",
            method: "create",
            args: [rs],
            context: this.initialState.context,
          });
        });
    },
    print_reportZporNumero() {
      const startParam = $('input[name="numZInicio"]').val();
      const endParam = $('input[name="numZFin"]').val();
      this.print_3mit("/api/imprimir/reporte_z/por_numero", {
        startParam,
        endParam,
      });
    },
    print_reportZporFecha() {
      const isoDate = function (sf) {
        const s = sf.split("/");
        return `${s[2]}-${s[1]}-${s[0]}`;
      };
      const startParam = $('input[name="fechaZInicio"]').val();
      const endParam = $('input[name="fechaZFin"]').val();
      this.print_3mit("/api/imprimir/reporte_z/por_fecha", {
        startParam: isoDate(startParam),
        endParam: isoDate(endParam),
      });
    },
    print_facturas() {
      const startParam = $('input[name="numFacturaInicio"]').val();
      const endParam = $('input[name="numFacturaFin"]').val();
      this.print_3mit("/api/imprimir/factura", {
        numDesde: startParam,
        numHasta: endParam,
      });
    },
    print_3mit(endpoint, data) {
      const json = data;
      const host = $("[name=printer_host]").val();
      const printer_host = "http://" + host + endpoint;

      return new Promise((resolve, reject) => {
        $.get(printer_host, json)
          .then((data) => {
            console.log("3mit_send_to_printer: Ok", data);
            resolve(data);
          })
          .catch((err) => {
            this.displayNotification({
              type: "alert",
              title: "Impresora Fiscal",
              message: "No se pudo imprimir en " + host,
            });
            reject(err);
          });
      });
    },
  });

  var printer_options = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
      Controller: CustomFormController,
    }),
  });
  view_registry.add("printer_options", printer_options);
});
