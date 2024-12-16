/** @odoo-module */

import tour from 'web_tour.tour';

const { steps } = tour.tours.account_tax_group;

const accountMenuClickIndex = steps.findIndex(step => step.id === 'account_menu_click');

steps.splice(accountMenuClickIndex, 1, 
    {
        trigger: '.o_app[data-menu-xmlid="account_accountant.menu_accounting"]',
        content: "Go to Accounting",
    }
);
