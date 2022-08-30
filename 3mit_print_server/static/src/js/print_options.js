"use strict";

console.log("***** print_options");
odoo.define("print_options", function (require) {
  console.log("******** print_options define");

  var FormView = require("web.FormView");
  var FormController = require("web.FormController");
  var view_registry = require("web.view_registry");

  var Dialog = require("3mit.dialog");

  var CustomFormController = FormController.extend({
    on_attach_callback: function () {
      this._super.apply(this, arguments);

      this.printer_host = $("input[name=printer_host]").val();
      $("button#reporteX").on("click", this.print_reportX.bind(this));
      $("button#reporteZ").on("click", this.print_reportZ.bind(this));
      $("button#reporteZporNumero").on(
        "click",
        this.print_reportZporNumero.bind(this)
      );
      $("button#reporteZporFecha").on(
        "click",
        this.print_reportZporFecha.bind(this)
      );
      $("button#reporteFacturas").on("click", this.print_facturas.bind(this));
      $("button#reporteNC").on("click", this.print_notas_credito.bind(this));
      $("button#numeroDocs").on("click", this, this.ultimos_numeros.bind(this));
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
      this.print_3mit("/api/imprimir/reporte_z_por_numero", {
        numDesde: startParam,
        numHasta: endParam,
      });
    },
    print_reportZporFecha() {
      const isoDate = function (sf) {
        const s = sf.split("/");
        return `${s[2]}-${s[1]}-${s[0]}`;
      };
      const startParam = $('input[name="fechaZInicio"]').val();
      const endParam = $('input[name="fechaZFin"]').val();
      this.print_3mit("/api/imprimir/reporte_z_por_fecha", {
        fechaDesde: isoDate(startParam),
        fechaHasta: isoDate(endParam),
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
    print_notas_credito() {
      const startParam = $('input[name="numFacturaInicio"]').val();
      const endParam = $('input[name="numFacturaFin"]').val();
      this.print_3mit("/api/imprimir/nota-credito", {
        numDesde: startParam,
        numHasta: endParam,
      });
    },
    ultimos_numeros() {
      this.print_3mit("/api/data_numeracion", {}).then((rs) => {
        Dialog.alert(self, {
          title: "Últimos números impresos",
          print: false,
          body: `<br>
Última factura: ${rs.ultimaFactura}<br>
Última nota de crédito: ${rs.ultimaNotaCredito}<br>
Último documento no fiscal: ${rs.ultimoDocumentoNoFiscal}<br>
          `,
        });
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
            resolve(data.data);
          })
          .catch((err) => {
            this.displayNotification({
              type: "alert",
              title: "Impresora Fiscal",
              message: "No se detectó el servicio de impresión",
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
  view_registry.add("pos_printer_options", printer_options);
});
