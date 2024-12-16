/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

export async function PrintFacturaAction(env, action) {
    try {
        // Enviar datos al servicio de impresión
        const result = await doPrintFactura(env, action.context.data);

        console.log("Respuesta del servicio de impresión:", result);

        // Verificar que la respuesta contenga los campos esperados
        if (result.nroFiscal && result.serial && result.fecha) {
            // Actualizar los campos en account.move
            await env.services.orm.call("account.move", "setTicket", [
                action.context.active_id,
                { data: result },
            ]);
        } else {
            throw new Error(
                "Faltan datos en la respuesta del servicio de impresión: " +
                    JSON.stringify(result)
            );
        }

        await env.services.action.doAction({ type: "ir.actions.act_window_close" });
    } catch (err) {
        console.error("Error en PrintFacturaAction:", err);
        env.services.notification.add("Error al imprimir la factura.", {
            type: "danger",
   });
}
}

const doPrintFactura = async (env, data) => {
    const printer_host = "localhost:5000";
    const isValid = await validate_3mitServer(env, printer_host);
    if (isValid) {
        try {
            const response = await fetch(`http://${printer_host}/api/imprimir/factura`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const result = await response.json();
            console.log("3mit_send_to_printer: Ok", result);
            console.log("Datos enviados a la impresora fiscal:", data); // <-- Añadido
            return result;
        } catch (err) {
            console.log("3mit_send_to_printer: Error", err);
            env.services.notification.add("Ticket Fiscal", { type: "danger" });
            throw err;
        }
    }
};

const validate_3mitServer = async (env, printer_host) => {
    try {
        const response = await fetch(`http://${printer_host}/api/ping`);
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return true;
    } catch (err) {
        const notif = _t("Revisar configuración de " + printer_host);
        env.services.notification.add(`${notif}`, { type: "danger" });
        return false;
    }
};

registry.category("actions").add("printFactura", PrintFacturaAction);
