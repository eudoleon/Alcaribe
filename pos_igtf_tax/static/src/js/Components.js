/** @odoo-module **/

import Registries from "point_of_sale.Registries";
import Orderline from "point_of_sale.Orderline";
import OrderlineDetails from "point_of_sale.OrderlineDetails";
import ProductScreen from "point_of_sale.ProductScreen";
import PaymentScreen from "point_of_sale.PaymentScreen";

const { onMounted, onWillUnmount } = owl;

const patchLine = (Parent) => class extends Parent {
    setup() {
        super.setup();

        onMounted(() => {
            if(this.props.line.x_is_igtf_line) {
                this.el.classList.add("igtf-line");
            }
        });
    }
};

Registries.Component.extend(PaymentScreen, (Parent) => class extends Parent {
    setup() {
        super.setup();

        onMounted(() => this.currentOrder.removeIGTF());
        onWillUnmount(() => (!(this.currentOrder.finalized)) && this.currentOrder.removeIGTF());
    }
});

Registries.Component.extend(ProductScreen, (Parent) => class extends Parent {
    async _clickProduct(event) {
        if(event.detail.isIgtfProduct) {
            return this.showPopup('ErrorPopup', {
                title: this.env._t('Invalid action'),
                body: this.env._t('No puedes agregar manualmente el producto IGTF'),
            });
        }
        
        return super._clickProduct(event);
    }
});

Registries.Component.extend(Orderline, patchLine);
Registries.Component.extend(OrderlineDetails, patchLine);