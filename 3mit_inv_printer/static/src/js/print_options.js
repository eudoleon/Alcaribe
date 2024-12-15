/** @odoo-module **/

import { formView } from "@web/views/form/form_view";
import { registry } from "@web/core/registry";
import { FormController } from "@web/views/form/form_controller";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from '@web/core/dialog/dialog';

export class CustomInvFormController extends FormController {

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.notificationService = useService("notification");
    }

    on_attach_callback() {
        super.on_attach_callback();

        this.printer_host = this.el.querySelector("input[name=printer_host]").value;

        this.el.querySelector("button#reporteX").addEventListener("click", this.print_reportX.bind(this));
        this.el.querySelector("button#reporteZ").addEventListener("click", this.print_reportZ.bind(this));
        this.el.querySelector("button#reporteZporNumero").addEventListener(
            "click",
            this.print_reportZporNumero.bind(this)
        );
        this.el.querySelector("button#reporteZporFecha").addEventListener(
            "click",
            this.print_reportZporFecha.bind(this)
        );
        this.el.querySelector("button#reporteFacturas").addEventListener("click", this.print_facturas.bind(this));
        this.el.querySelector("button#reporteNC").addEventListener("click", this.print_notas_credito.bind(this));
        this.el.querySelector("button#numeroDocs").addEventListener("click", this.ultimos_numeros.bind(this));
    }

    print_reportX() {
        this.print_3mit("/api/imprimir/reporte_x");
    }

    print_reportZ() {
        this.print_3mit("/api/imprimir/reporte_z")
            .then(() => {
                return this.print_3mit("/api/data_z");
            })
            .then((rs) => {
                return this.orm.call(
                    "datos.zeta.diario",
                    "create",
                    [[], rs],
                    this.initialState.context
                );
            });
    }

    print_reportZporNumero() {
        const startParam = this.el.querySelector('input[name="numZInicio"]').value;
        const endParam = this.el.querySelector('input[name="numZFin"]').value;
        this.print_3mit("/api/imprimir/reporte_z_por_numero", {
            numDesde: startParam,
            numHasta: endParam,
        });
    }

    print_reportZporFecha() {
        const isoDate = (sf) => {
            const s = sf.split("-");
            return `${s[0]}-${s[1]}-${s[2]}`;
        };
        const startParam = this.el.querySelector('input[name="fechaZInicio"]').value;
        const endParam = this.el.querySelector('input[name="fechaZFin"]').value;
        this.print_3mit("/api/imprimir/reporte_z_por_fecha", {
            fechaDesde: isoDate(startParam),
            fechaHasta: isoDate(endParam),
        });
    }

    print_facturas() {
        const startParam = this.el.querySelector('input[name="numFacturaInicio"]').value;
        const endParam = this.el.querySelector('input[name="numFacturaFin"]').value;
        this.print_3mit("/api/imprimir/factura", {
            numDesde: startParam,
            numHasta: endParam,
        });
    }

    print_notas_credito() {
        const startParam = this.el.querySelector('input[name="numFacturaInicio"]').value;
        const endParam = this.el.querySelector('input[name="numFacturaFin"]').value;
        this.print_3mit("/api/imprimir/nota-credito", {
            numDesde: startParam,
            numHasta: endParam,
        });
    }

    ultimos_numeros() {
        this.print_3mit("/api/data_numeracion", {}).then((rs) => {
            Dialog.alert(this, {
                title: _t("Últimos números impresos"),
                body: `
                    <br>Última factura: ${rs.ultimaFactura}
                    <br>Última nota de crédito: ${rs.ultimaNotaCredito}
                    <br>Último documento no fiscal: ${rs.ultimoDocumentoNoFiscal}
                `,
            });
        });
    }

    async print_3mit(endpoint, data = {}) {
        const json = JSON.stringify(data);
        const host = this.printer_host;
        const printer_host = `http://${host}${endpoint}`;

        try {
            const response = await fetch(printer_host, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: json
            });
            if (response.ok) {
                const result = await response.json();
                console.log("3mit_send_to_printer: Ok", result);
                return result.data;
            } else {
                throw new Error('Network response was not ok');
            }
        } catch (err) {
            this.notificationService.add(
                _t("No se detectó el servicio de impresión"),
                { type: "danger" }
            );
            console.error("Error en print_3mit:", err);
            throw err;
        }
    }
}

registry.category("views").add("printer_options", {
    ...formView,
    Controller: CustomInvFormController,
});
