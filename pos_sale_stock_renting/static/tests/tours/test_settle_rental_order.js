odoo.define('point_of_sale.tour.RentalTour', function (require) {
    'use strict';

    const { ProductScreen } = require('pos_sale_stock_renting.tour.ProductScreenTourMethods');
    const { PaymentScreen } = require('point_of_sale.tour.PaymentScreenTourMethods');
    const { ReceiptScreen } = require('point_of_sale.tour.ReceiptScreenTourMethods');
    const { getSteps, startSteps } = require('point_of_sale.tour.utils');
    var Tour = require('web_tour.tour');

    startSteps();

    ProductScreen.do.clickQuotationButton();
    ProductScreen.do.selectFirstOrder();
    ProductScreen.do.enterSerialNumber('123456789');
    ProductScreen.do.clickPayButton();
    PaymentScreen.do.clickPaymentMethod('Cash');
    PaymentScreen.do.clickValidate();
    ReceiptScreen.check.isShown();

    Tour.register('OrderLotsRentalTour', { test: true, url: '/pos/ui' }, getSteps());

    startSteps();

    ProductScreen.do.clickQuotationButton();
    ProductScreen.do.selectFirstOrder();
    ProductScreen.do.clickPayButton();
    PaymentScreen.do.clickPaymentMethod('Bank');
    PaymentScreen.do.clickValidate();
    ReceiptScreen.check.isShown();

    Tour.register('PosSettleRentalOrderWithImport', { test: true, url: '/pos/ui' }, getSteps());
});
