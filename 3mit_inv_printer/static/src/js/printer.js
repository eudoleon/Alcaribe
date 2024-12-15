odoo.define("3mit_inv_printer", function (require) {
    const ActionManager = require("web.ActionManager");
    const AbstractAction = require("web.AbstractAction");
  
    const core = require("web.core");
    var framework = require("web.framework");
    var session = require("web.session");
  
    const printer_host = "localhost:5000";
  
    ActionManager.include({
      _handleAction: function (action, options) {
        window.p = this;
        const self = this;
  
        if (action.tag == "printFactura") {
          return this.doPrintFactura(action.data).then((rs) => {
            //actualiza factura con flag impreso
            return this._rpc({
              model: action.res_model,
              method: "setTicket",
              args: [action.context.active_id, rs],
              //context: this.initialState.context,
            }).then((rs) => {
              //return this.do_action("reload");
              return this.getCurrentController().widget.reload();
            });
          });
        }
  
        return this._super.apply(this, arguments);
      },
  
      doPrintFactura: function (data) {
        if (window._debug) return Promise.resolve();
        console.log("json completo: Ok", data);
  
        return this.validate_3mitServer(printer_host).then(() => {
          //framework.blockUI();
  
          return $.post({
            url: `http://${printer_host}/api/imprimir/factura`,
            data: JSON.stringify(data),
            contentType: "application/json",
            dataType: "json",
          })
            .then((data) => {
              console.log("3mit_send_to_printer: Ok", data);
              //framework.unblockUI();
              return Promise.resolve(data);
            })
            .catch((err) => {
              console.log("3mit_send_to_printer: Error", err);
              //framework.unblockUI();
              this.displayNotification({
                type: "alert",
                title: "Ticket Fiscal",
                message: err,
              });
  
              return Promise.reject(err);
            });
        });
      },
  
      // solo verifica si el print_server está on-line
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
  
    const notaCredito = AbstractAction.extend({
      start: async function () {
        console.log("start NotaCredito");
        await this._super(...arguments);
        //this.$el.html("hello");
        alert("hello");
      },
    });
  
    core.action_registry.add("notaCredito", notaCredito);
  });
  