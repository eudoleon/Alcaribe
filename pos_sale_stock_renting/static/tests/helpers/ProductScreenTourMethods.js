odoo.define('pos_sale_stock_renting.tour.ProductScreenTourMethods', function (require) {
    'use strict';

    const { createTourMethods } = require('point_of_sale.tour.utils');
    const { Do, Check, Execute } = require('pos_sale.tour.ProductScreenTourMethods');

    class DoExt extends Do {
        enterSerialNumber(serialNumber) {
            return [
                {
                    content: `click serial number icon'`,
                    trigger: '.line-lot-icon',
                    run: 'click',
                },
                {
                    content: `insert serial number '${serialNumber}'`,
                    trigger: '.popup-input.list-line-input',
                    run: 'text ' + serialNumber,
                },
                {
                    content: `click validate button'`,
                    trigger: '.button.confirm',
                    run: 'click',
                },
            ];
        }
    }
    return createTourMethods('ProductScreen', DoExt, Check, Execute);
});
