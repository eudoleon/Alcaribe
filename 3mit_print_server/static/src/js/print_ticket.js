odoo.define("3mit_print_server.print_ticket", function (require) {
  "use strict";

  //const screens = require("point_of_sale.screens");

  const ReceiptScreen = require("point_of_sale.ReceiptScreen");
  const PaymentScreen = require("point_of_sale.PaymentScreen");
  const Registries = require("point_of_sale.Registries");

  // const models = require("point_of_sale.models");
  var { Order, Orderline, PosGlobalState} = require('point_of_sale.models');
  const core = require("web.core");
  const rpc = require('web.rpc');
  const _t = core._t;


  	const POSOrderMit = (PosGlobalState) => class POSOrderMit extends PosGlobalState {

		async _processData(loadedData) {
	        await super._processData(...arguments);
	        this.pos_order = loadedData['pos_order'] || [];
        }
    }

	Registries.Model.extend(PosGlobalState, POSOrderMit);

  // var _Order = models.Order.prototype;
  // var _Orderline = models.Orderline.prototype;

  // models.load_fields("res.partner", ["vat"]);

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
				var invoiced_finalized = this.currentOrder.is_to_invoice()
				  ? this.currentOrder.finalized
				  : true;
				return (
				  this.env.pos.config.iface_print_skip_screen && invoiced_finalized
				);
			}

	  // devuelve data reportada por la impresora
	  	async print_3mit(order) {
				const json = await this._3mit_prepare_json(order);
				console.log("json:", json)
				const printer_host = this.env.pos.config.printer_host;

				try {
				  	const rs = await $.post({
						url: `http://${printer_host}/api/imprimir/factura`,
						data: JSON.stringify(json),
						contentType: "application/json",
						dataType: "json",
						timeout: 60000, //30 segundos para imprimir
				  	});
				  	console.log("3mit_send_to_printer:", rs);
				  	if (rs.status == "OK") {
						return rs.data;
				  	} else {
						return rs.status + ":" + rs.message;
				  	}
				} catch (err) {
					console.log("3mit_send_to_printer: Error", err);
				  	await this.showPopup("ErrorPopup", {
						title: "Ticket Fiscal",
						body: err.statusText,
					});
				  	console.log("3mit_send_to_printer: Error", err);
				  	return err.statusText;
				}
	  	}

	  	async _3mit_prepare_json(order) {
			var json = order.export_for_printing();
			console.log('order', order);
			if (!json.client) json.client = {};
			var receipt = {
				backendRef: json.name || null,
				idFiscal: json.client.vat ||
					json.client.identification_id ||
					null,
				razonSocial: json.client.name || null,
				direccion: json.client.street || null,
				telefono: json.client.phone || null,
			};
			// items-products/
			const discount_product_id = this.env.pos.config.discount_product_id[0]
			var prods = json.orderlines.filter(r=>r.product_id!=discount_product_id);
			receipt.items = prods.map((r) => {
				return {
					nombre: r.product_name,
					cantidad: r.quantity,
					precio: fixMoney(r.product_price * order.rate_order),
					impuesto: r.iva_rate,
					descuento: r.discount,
					tipoDescuento: 'p',
					comentario: r.customer_note || "", // Aquí añadimos los comentarios de los productos
				};
			});
			
			if(order.pc_discount){
				receipt.descuento = order.pc_discount;
				receipt.tipoDescuento = 'p';
			}
		
			const bi_igtf = order.bi_igtf || 0;
			receipt.pagos = [];
			async function getPaymentMethodData(paymentMethodName) {
				let paymentMethodId = await rpc.query({
					model: 'pos.payment.method',
					method: 'search',
					args: [[['name', '=', paymentMethodName]]]
				});
				
				let fields = ['dolar_active', 'fiscal_print_code'];
				
				let paymentMethodData = await rpc.query({
					model: 'pos.payment.method',
					method: 'read',
					args: [paymentMethodId, fields]
				});
				
				return paymentMethodData[0];
			}
		
			// Consolida por código en la impresora
			const pagos = await Promise.all(json.paymentlines.map(async (r) => {
				let data_payment = await getPaymentMethodData(r.name);
				console.log(data_payment);
				console.log("dolar_active:",data_payment.dolar_active);
				console.log("Code:",data_payment.fiscal_print_code);
				console.log("Objeto r:", r);
		
				let monto = 0;
				let igtf = 0;
				if(data_payment.dolar_active == true){
					igtf = fixMoney(r.amount * 0.03);
					monto = fixMoney(r.amount * order.rate_order);
				} else {
					monto = fixMoney(r.amount * order.rate_order);
				}
				console.log('tasa', order.rate_order);
				console.log('igtf', igtf);
				console.log('amount', r.amount);
				console.log('monto', monto);
				return {
					codigo: data_payment.fiscal_print_code,
					nombre: r.name,
					monto: monto,
					//monto: fixMoney(r.amount * order.rate_order),
				};
			}));
		
			pagos.forEach((r) => {
				const p = receipt.pagos.find((f) => f.codigo == r.codigo);
				if (!p) {
					receipt.pagos.push(r);
				} else {
					p.monto += r.monto;
				}
			});
		
			// Añade los comentarios del pedido
			receipt.comentarios = json.note ? [json.note] : [];
		
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

		async printNewButtonFiscal() {
      const bfiscal = await this.validate_3mitServer();
      if (!bfiscal) {
        return;
      }

      $(".button.next", this.el).hide();

      const isPrinted = await this._printNewButtonFiscal();

      if (isPrinted) {
        this.currentOrder._printed_fiscal = true;
        $(".button.next", this.el).show();
      } else {
        $(".button.next", this.el).hide();
      }
    }

    




	  async _printNewButtonFiscal() {
      const order = this.currentOrder;

      if (order._printed_fiscal) {
        await this.showPopup("ErrorPopup", {
          title: "Ticket Fiscal",
          body: "El ticket ya fue enviado a la impresora.",
        });
        return true;
      }

      var json = order.export_for_printing();
      var rate_order = await this.rpc({
          model: "pos.order",
          method: "get_rate_order",
          args: [false,json.name]
        });
      order.rate_order = rate_order
      const dataFiscal = await this.print_3mit(order);

      if (!dataFiscal || !dataFiscal.nroFiscal) {
        await this.showPopup("ErrorPopup", {
          title: "Error imprimiendo",
          body:
            "Revise la impresora y reintente imprimir para continuar\n\n" +
            dataFiscal,
        });
        return false;
      }
      // Se imprimió y se obtuvo respuesta de la impresora en dataFiscal
      order._printed_fiscal = true;
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


  	const MitCustomOrder = (Order) => class MitCustomOrder extends Order{
        constructor(obj, options) {
        	super(...arguments);
        	this.ticket_fiscal = null;
	  		this.serial_fiscal = null;
	  		this.fecha_fiscal = null;
			this.pc_discount=0;
		}

		init_from_JSON(json) {
		  	this.ticket_fiscal = json.ticket_fiscal;
		  	this.serial_fiscal = json.serial_fiscal;
		  	this.fecha_fiscal = json.fecha_fiscal;
			this.pc_discount = json.pc_discount;
		  	super.init_from_JSON(...arguments);
		}

		export_as_JSON() {
		  	var data = super.export_as_JSON(...arguments);
		  	data.ticket_fiscal = this.ticket_fiscal;
		  	data.serial_fiscal = this.serial_fiscal;
		  	data.fecha_fiscal = this.fecha_fiscal;
			data.pc_discount = this.pc_discount;
		  	return data;
		}

		export_for_printing() {
		  	var receipt = super.export_for_printing(...arguments);
		  	// agrega info de cliente
		  	receipt.client = this.get_partner();
		  	//
		  	return receipt;
		}
   	}
   	Registries.Model.extend(Order, MitCustomOrder);



  const CustomOrderLine = (Orderline) => class CustomOrderLine extends Orderline{

        export_for_printing() {
        	var line = super.export_for_printing(...arguments);
			var taxes = this.get_taxes();
			if (taxes.length === 0) {
				line.iva_rate = 0;
			} else {
				line.iva_rate = taxes[0].amount;
			}
			  //
			line.product_price = this.price
			line.product_id = this.product.id; //luego se usará para determinar si es una línea de Descuento
			return line;
	    }
	    
	}
	Registries.Model.extend(Orderline, CustomOrderLine);
});
