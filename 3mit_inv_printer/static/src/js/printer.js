/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

export async function PrintFacturaAction(env, action) {
    try {
        const result = await doPrintFactura(env, action.data);
        // Enviar directamente result.data a setTicket
        const ticket_result = await env.services.orm.call(
            "account.move",
            "setTicket",
            [action.context.active_id, {data: result.data}]
        );
        if (ticket_result) {
            await env.services.action.doAction({type: 'ir.actions.act_window_close'});
        }
    } catch (err) {
        console.error("Error en PrintFacturaAction:", err);
        await env.services.action.doAction({type: 'ir.actions.act_window_close'});
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
