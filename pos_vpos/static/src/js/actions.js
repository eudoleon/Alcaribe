/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

const { Component, whenReady, xml, mount, useState } = owl;

export class PosConfigKanbanOptions extends Component {
  static template = xml`
      <div>
          <a href="#" t-on-click.prevent="showOpcion1">Opción 1</a>
          <a href="#" t-on-click.prevent="showOpcion2">Opción 2</a>
      </div>
  `;
  setup() {
    console.log("setup ***");
    super.setup();
  }

  showOpcion1(ev) {
    // Lógica para Opción 1
    console.log("Opción 1 seleccionada");
  }

  showOpcion2(ev) {
    // Lógica para Opción 2
    console.log("Opción 2 seleccionada");
  }
}

PosConfigKanbanOptions.template = "pos_vpos.PosConfigKanbanOptions";

registry
  .category("components")
  .add("pos_vpos.PosConfigKanbanOptions", PosConfigKanbanOptions);



whenReady().then(() => {
  //mount(PosConfigKanbanOptions, document.body);
});
