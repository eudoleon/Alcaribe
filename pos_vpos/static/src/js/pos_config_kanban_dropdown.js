/** @odoo-module */ 

import { useService } from "@web/core/utils/hooks";
import { KanbanDropdownMenuWrapper } from "@web/views/kanban/kanban_dropdown_menu_wrapper"
import { patch } from "@web/core/utils/patch";

patch(KanbanDropdownMenuWrapper.prototype, "my_kanban_view_patch", {
    setup(){
        this.orm = useService("orm");
        this._super.apply(this, arguments);
    },
    onClick(ev) {
        ev.preventDefault()
        
        const _event = ev.target.getAttribute('vpos_action'); 
        if (_event && this.props.slots.default.__ctx.record.vpos.raw_value) {
            this._vpos_execute("metodo",{accion:_event});
        }
        console.log(_event);
        this._super.apply(this, arguments);
    },
    async _vpos_execute(metodo, data) {
        const url = this.props.slots.default.__ctx.record.vpos_restApi.raw_value

        const params = {
        async: true,
        crossDomain: true,
        method: "POST",
        headers: {
            "content-type": "application/json",
        },
        processData: false,
        url: `${url}/vpos/${metodo}`,
        data: JSON.stringify(data),
        };
        return new Promise((resolve, reject) => {
        $.ajax(params)
            .then((rs)=> {
            if (["00", "100"].indexOf(rs.codRespuesta) > -1) {
                return resolve(rs);
            } else {
                console.error(rs.mensajeRespuesta);//this._show_error(rs.mensajeRespuesta);
                return reject(false);
            }
            })
            .fail((err) => {
            console.error(err);//this._show_error(_t("Cannot connect with vpos"));
            return reject(false);
            });
        });
    },
});