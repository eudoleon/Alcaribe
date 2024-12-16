/** @odoo-module **/

import tour from 'web_tour.tour';

tour.register('account_accountant_bank_rec_widget_ui',
    {
        url: '/web',
    },
    [
        tour.stepUtils.showAppsMenuItem(),
        ...tour.stepUtils.goToAppSteps('account_accountant.menu_accounting', "Open the accounting module"),

        // Open the widget. The first line should be selected by default.
        {
            content: "Open the bank reconciliation widget",
            extra_trigger: ".breadcrumb",
            trigger: "button.btn-primary[name='action_open_reconcile']",
        },
        {
            content: "'line1' should be selected and form mounted",
            extra_trigger: "div[name='lines_widget'] td[field='name']:contains('line1')",
            trigger: ".o_bank_rec_selected_st_line:contains('line1')",
            run: () => {},
        },
        // Select line2. It should remain selected when returning using the breadcrumbs.
        {
            content: "select 'line2'",
            extra_trigger: ".o_bank_rec_st_line:contains('line3')",
            trigger: ".o_bank_rec_st_line:contains('line2')",
        },
        {
            content: "'line2' should be selected",
            trigger: ".o_bank_rec_selected_st_line:contains('line2')",
            run: () => {},
        },
        {
            content: "View an invoice",
            trigger: "button.btn-secondary[name='action_open_business_doc']:eq(1)",
        },
        {
            content: "Breadcrumb back to Bank Reconciliation from INV/2019/00002",
            trigger: ".breadcrumb-item:contains('Bank Reconciliation')",
            extra_trigger: ".breadcrumb-item:contains('INV/2019/00002')",
            run: "click"
        },
        {
            content: "'line2' should be selected after returning",
            trigger: ".o_bank_rec_selected_st_line:contains('line2')",
            extra_trigger: ".o_bank_rec_st_line:contains('line1')",
        },
        {
            content: "'line2' form mounted",
            extra_trigger: "div[name='lines_widget'] td[field='name']:contains('line2')",
            trigger: ".o_bank_rec_selected_st_line:contains('line2')",
        },
        // Keep AML search, and prepared entry (lines_widget) when changing tabs, using breadcrumbs, and view switcher
        {
            content: "AMLs list has both invoices",
            extra_trigger: "div.bank_rec_widget_form_amls_list_anchor table.o_list_table tr:nth-child(3) td[name='move_id']:contains('INV/2019/00001')",
            trigger: "div.bank_rec_widget_form_amls_list_anchor table.o_list_table tr:nth-child(2) td[name='move_id']:contains('INV/2019/00002')",
            run: () => {},
        },
        {
            content: "Search for INV/2019/00001",
            extra_trigger: "a.active[name='amls_tab']",
            trigger: "div.bank_rec_widget_form_amls_list_anchor .o_searchview_input",
            run: "text INV/2019/00001",
        },
        {
            content: "Select the Journal Entry search option from the dropdown",
            trigger: ".o_searchview_autocomplete li:contains(Journal Entry)",
        },
        {
            content: "AMLs list only displays one invoice",
            trigger: "div.bank_rec_widget_form_amls_list_anchor table.o_list_table tr:nth-child(1) td[name='move_id']:contains('INV/2019/00001')",
            run: () => {},
        },
        {
            content: "Liquidity line displays debit '$ 1,000.00'",
            trigger: "div[name='lines_widget'] table.o_list_table tr.o_bank_rec_liquidity_line td[field='debit']:contains('$ 1,000.00')",
            run: () => {},
        },
        {
            content: "Select the liquidity line",
            trigger: "tr.o_bank_rec_liquidity_line td[field='debit']",
        },
        {
            content: "Modify the liquidity line amount",
            extra_trigger: "div.tab-pane.active input[id='form_balance']:focus",
            trigger: "div.tab-pane.active input[id='form_balance']",
            run: "text 100.00",
        },
        {
            content: "Liquidity line displays debit '$ 100.00'",
            trigger: "div[name='lines_widget'] table.o_list_table tr.o_bank_rec_liquidity_line td[field='debit']:contains('$ 100.00')",
            run: () => {},
        },
        {
            content: "Select 'amls_tab'",
            extra_trigger: "a.active[name='manual_operations_tab']",
            trigger: "a[name='amls_tab']",
        },
        {
            content: "AMLs list contains the search facet, and one invoice - select it",
            extra_trigger: "div.bank_rec_widget_form_amls_list_anchor .o_searchview_facet:nth-child(2) .o_facet_value:contains('INV/2019/00001')",
            trigger: "div.bank_rec_widget_form_amls_list_anchor table.o_list_table tr:nth-child(1) td[name='move_id']:contains('INV/2019/00001')",
            run: "click"
        },
        {
            content: "Check INV/2019/00001 is well marked as selected",
            extra_trigger: "div.bank_rec_widget_form_amls_list_anchor table.o_list_table tr.o_rec_widget_list_selected_item td[name='move_id']:contains('INV/2019/00001')",
            trigger: "div.bank_rec_widget_form_amls_list_anchor table.o_list_table tr.o_rec_widget_list_selected_item td[name='move_id']:contains('INV/2019/00001')",
            run: function() {},
        },
        {
            content: "View an invoice",
            trigger: "button.btn-secondary[name='action_open_business_doc']:nth-child(1)",
        },
        {
            content: "Breadcrumb back to Bank Reconciliation from INV/2019/00001",
            trigger: ".breadcrumb-item:contains('Bank Reconciliation')",
            extra_trigger: ".breadcrumb-item:contains('INV/2019/00001')",
        },
        {
            content: "Check INV/2019/00001 is selected and still contains the search facet",
            extra_trigger: "div.bank_rec_widget_form_amls_list_anchor .o_searchview_facet:nth-child(2) .o_facet_value:contains('INV/2019/00001')",
            trigger: "div.bank_rec_widget_form_amls_list_anchor table.o_list_table tr.o_rec_widget_list_selected_item td[name='move_id']:contains('INV/2019/00001')",
            run: () => {},
        },
        // Search should remove some lines, select the first unmatched record, and persist when returning with breadcrumbs
        {
            content: "Search for line2",
            extra_trigger: "a.active[name='amls_tab']",
            trigger: "div.o_kanban_view .o_searchview_input",
            run: "text line2",
        },
        {
            content: "Select the Transaction search option from the dropdown",
            trigger: ".o_searchview_autocomplete li:contains(Transaction)",
        },
        {
            content: "'line2' should be selected",
            trigger: ".o_bank_rec_st_line:last():contains('line2')",
            extra_trigger: "div[name='lines_widget'] td[field='name']:contains('line2')",
            run: () => {}
        },
        {
            content: "Nothing has changed: INV/2019/00001 is selected and still contains the search facet",
            extra_trigger: "div.bank_rec_widget_form_amls_list_anchor .o_searchview_facet:nth-child(2) .o_facet_value:contains('INV/2019/00001')",
            trigger: "div.bank_rec_widget_form_amls_list_anchor table.o_list_table tr.o_rec_widget_list_selected_item td[name='move_id']:contains('INV/2019/00001')",
            run: () => {},
        },
        {
            content: "Switch to list view",
            extra_trigger: ".o_switch_view.o_kanban.active",
            trigger: ".o_switch_view.o_list",
        },
        {
            content: "Switch back to kanban",
            extra_trigger: ".o_switch_view.o_list.active",
            trigger: ".o_switch_view.o_kanban",
        },
        {
            content: "Remove the kanban filter for line2",
            trigger: ".o_kanban_view .o_searchview_facet:nth-child(3) .o_facet_remove",
        },
        {
            content: "Nothing has changed: INV/2019/00001 is still selected and contains the search facet",
            extra_trigger: "div.bank_rec_widget_form_amls_list_anchor table.o_list_table tr:nth-child(1) td[name='move_id']:contains('INV/2019/00001')",
            trigger: "div.bank_rec_widget_form_amls_list_anchor table.o_list_table tr.o_rec_widget_list_selected_item td[name='move_id']:contains('INV/2019/00001')",
            run: () => {},
        },
        // AML Search Facet is removed, and lines_widget reset when changing line
        {
            content: "selecting 'line1' should reset the AML search filter ",
            extra_trigger: ".o_bank_rec_st_line:contains('line3')",
            trigger: ".o_bank_rec_st_line:contains('line1')",
        },
        {
            content: "select 'line2' again",
            extra_trigger: ".o_bank_rec_selected_st_line:contains('line1')",
            trigger: ".o_bank_rec_st_line:contains('line2')",
        },
        {
            content: "Bank Suspense Account is back",
            extra_trigger: "div[name='lines_widget'] td[field='name']:contains('line2')",
            trigger: "div[name='lines_widget'] .o_bank_rec_auto_balance_line",
            run: () => {},
        },
        {
            content: "AML Search Filter has been reset",
            trigger: ".o_list_view .o_facet_value:last-child:contains('Customer/Vendor')",
            run: () => {},
        },
        // Test statement line selection when using the pager
        {
            content: "Click Pager",
            trigger: ".o_pager_value:first()",
        },
        {
            content: "Change pager to display lines 1-2",
            trigger: "input.o_pager_value",
            run: "text 1-2",
        },
        {
            content: "Last St Line is line2",
            extra_trigger: ".o_pager_value:contains('1-2')",
            trigger: ".o_bank_rec_st_line:last():contains('line2')",
            run: () => {},
        },
        {
            content: "Page Next",
            trigger: ".o_pager_next:first()",
        },
        {
            content: "Statement line3 is selected",
            extra_trigger: ".o_pager_value:contains('3-3')",
            trigger: ".o_bank_rec_selected_st_line:contains('line3')",
            run: () => {},
        },
        {
            content: "Page to beginning",
            trigger: ".o_pager_next:first()",
        },
        {
            content: "Statement line1 is selected",
            extra_trigger: "div[name='lines_widget'] td[field='name']:contains('line1')",
            trigger: ".o_bank_rec_selected_st_line:contains('line1')",
            run: () => {},
        },
        // HTML buttons
        {
            content: "Mount an invoice",
            trigger: "div.bank_rec_widget_form_amls_list_anchor table.o_list_table td[name='move_id']:contains('INV/2019/00003')",
        },
        {
            content: "Select the mounted invoice line and check the strikethrough value",
            extra_trigger: "div[name='lines_widget']:has(.text-decoration-line-through:contains('$ 2,000.00'))",
            trigger: ".o_field_bank_rec_widget_form_lines_widget tr.o_data_row:last() td[field='name']:contains('INV/2019/00003')",
        },
        {
            content: "Fully Paid button",
            extra_trigger: "a.active[name='manual_operations_tab']",
            trigger: "button[name='button_form_apply_suggestion']",
        },
        {
            content: "Check the remainder",
            trigger: ".o_field_bank_rec_widget_form_lines_widget tr.o_data_row:contains('Suspense') td[field='debit']:contains('$ 1,000.00')",
            run: () => {},
        },
        {
            content: "Partial Payment",
            extra_trigger: "a.active[name='manual_operations_tab']",
            trigger: "button[name='button_form_apply_suggestion']:contains('partial payment')",
        },
        {
            content: "View Invoice 0003",
            trigger: "button[name='button_form_redirect_to_move_form']"
        },
        {
            content: "Breadcrumb back to Bank Reconciliation from INV/2019/00003",
            trigger: ".breadcrumb-item:contains('Bank Reconciliation')",
            extra_trigger: ".breadcrumb-item:contains('INV/2019/00003')",
        },
        {
            content: "Select the mounted invoice line INV/2019/00003",
            trigger: ".o_field_bank_rec_widget_form_lines_widget tr.o_data_row:last() td[field='name']:contains('INV/2019/00003')",
        },
        // Match Existing entries tab is activated when line is removed
        {
            content: "Remove the invoice",
            extra_trigger: "a.active[name='manual_operations_tab']",
            trigger: ".o_list_record_remove .fa-trash-o",
        },
        {
            content: "amls_tab is activated",
            trigger: "a.active[name='amls_tab']",
            run: () => {},
        },
        {
            content: "Activate Manual Operations to add manual entries",
            trigger: "a[name='manual_operations_tab']",
        },
        {
            content: "add manual entry 1",
            trigger: "input#form_balance",
            run: "text -600.0"
        },
        {
            content: "mount the remaining opening balance line",
            trigger: ".o_field_bank_rec_widget_form_lines_widget tr.o_data_row:contains('Suspense') td[field='credit']:contains('$ 400.00')",
        },
        {
            content: "Remove the manual entry",
            extra_trigger: "input#form_balance:text('-400.00'):focus",
            trigger: ".o_list_record_remove .fa-trash-o",
        },
        {
            content: "amls_tab is activated and auto balancing line is 1000",
            extra_trigger: ".o_field_bank_rec_widget_form_lines_widget tr.o_data_row:contains('Suspense') td[field='credit']:contains('$ 1,000.00')",
            trigger: "a.active[name='amls_tab']",
            run: () => {},
        },
        {
            content: "Mount another invoice",
            trigger: "div.bank_rec_widget_form_amls_list_anchor table.o_list_table td[name='move_id']:contains('INV/2019/00001')",
        },
        // After validating, line1 should disappear & line2 should be selected (due to filters)
        {
            content: "Validate line1",
            extra_trigger: "div.bank_rec_widget_form_amls_list_anchor table.o_list_table tr.o_rec_widget_list_selected_item td[name='move_id']:contains('INV/2019/00001')",
            trigger: "button[name='button_validate']",
        },
        {
            content: "The 'line2' is the first kanban record and is selected",
            extra_trigger: "div[name='lines_widget'] td[field='name']:contains('line2')",
            trigger: ".o_bank_rec_st_line:first():contains('line2')",
            run: () => {},
        },
        // Test Double-click, "Matched" badge and Reset
        {
            content: "Mount invoice 2 for line 2",
            trigger: "div.bank_rec_widget_form_amls_list_anchor table.o_list_table td[name='move_id']:contains('INV/2019/00002')",
        },
        {
            content: "Validate line2 with double click",
            extra_trigger: "div.bank_rec_widget_form_amls_list_anchor table.o_list_table tr.o_rec_widget_list_selected_item td[name='move_id']:contains('INV/2019/00002')",
            trigger: "button[name='button_validate']",
        },
        {
            content: "Ensure validate button is disabled to prevent double-click",
            trigger: "button[name='button_validate'][disabled]",
            run: () => {}
        },
        {
            content: "Remove the kanban filter for 'Not Matched'",
            extra_trigger: ".o_bank_rec_selected_st_line:contains('line3')",
            trigger: ".o_kanban_view .o_searchview_facet:nth-child(2) .o_facet_remove",
        },
        {
            content: "The 'line1' is the first kanban record with line1 selected",
            extra_trigger: "div[name='lines_widget'] td[field='name']:contains('line1')",
            trigger: ".o_bank_rec_st_line:first():contains('line1')",
            run: () => {},
        },
        {
            content: "Click Pager again after line2 is matched",
            extra_trigger: ".o_bank_rec_st_line:contains('line2') .badge.text-bg-success",
            trigger: ".o_pager_value:first()",
        },
        {
            content: "Change pager to display lines 1-3",
            trigger: "input.o_pager_value",
            run: "text 1-3",
        },
        {
            content: "manually select line2 again by clicking it's matched icon",
            extra_trigger: ".o_bank_rec_selected_st_line:contains('line3')",
            trigger: ".badge.text-bg-success:last()",
        },
        {
            content: "Reset line2",
            extra_trigger: "div[name='lines_widget']:not(:has(.fa-trash-o)) td[field='name']:contains('line2')",
            trigger: "button[name='button_reset']",
        },
        {
            content: "amls_tab is activated while still on line2 which doesn't contain a badge",
            extra_trigger: ".o_bank_rec_selected_st_line:contains('line2'):not(:has(div.badge))",
            trigger: "div[name='lines_widget']:has(.fa-trash-o)+.o_notebook a.active[name='amls_tab']",
            run: () => {},
        },
        // Test view_switcher
        {
            content: "Switch to list view",
            extra_trigger: ".o_switch_view.o_kanban.active",
            trigger: ".o_switch_view.o_list",
        },
        {
            content: "Select the first Match Button (line2)",
            extra_trigger: ".btn-secondary:contains('View')",
            trigger: ".btn-secondary:contains('Match')",
        },
        {
            content: "Last St Line is line2",
            extra_trigger: ".o_bank_rec_st_line:last():contains('line2')",
            trigger: ".o_bank_rec_selected_st_line:contains('line2')",
        },
        {
            content: "Button To Check will reconcile since partner is saved on line2",
            trigger: ".btn-secondary:contains('To Check')",
        },
        {
            content: "both badges are visible, trash icon is not, discuss tab is active",
            extra_trigger: ".o_bank_rec_selected_st_line:contains('line2'):has(div.badge:contains('Matched')):has(span.badge:contains('To check'))",
            trigger: "div[name='lines_widget']:not(:has(.fa-trash-o))+.o_notebook a.active[name='discuss_tab']",
            run: () => {},
        },
        {
            content: "Switch to list view",
            extra_trigger: ".o_switch_view.o_kanban.active",
            trigger: ".o_switch_view.o_list",
        },
        {
            content: "Remove the line filter",
            extra_trigger: ".o_switch_view.o_list.active",
            trigger: ".o_searchview_facet:contains('0002') .o_facet_remove",
        },
        {
            content: "Select the first Match Button (line3)",
            extra_trigger: ".o_data_row:contains('line2'):has(.btn-secondary:contains('View'))",
            trigger: ".btn-secondary:contains('Match')",
        },
        // Test Reco Model
        {
            content: "Choose a filter",
            extra_trigger: ".o_bank_rec_st_line:contains('line3')",
            trigger: ".o_filter_menu:first() i",
        },
        {
            content: "Not Matched Filter",
            extra_trigger: ".o-dropdown--menu",
            trigger: ".dropdown-item:contains('Not Matched')",
        },
        {
            content: "reco model dropdown",
            extra_trigger: ".o_switch_view.o_kanban.active",
            trigger: ".bank_rec_reco_model_dropdown i",
        },
        {
            content: "create model",
            extra_trigger: ".o-dropdown--menu",
            trigger: ".dropdown-item:contains('Create model')",
        },
        {
            content: "model name",
            trigger: "input#name",
            run: "text Bank Fees",
        },
        {
            content: "add an account",
            trigger: "a:contains('Add a line')",
        },
        {
            content: "search for bank fees account",
            extra_trigger: "[name='account_id'] input",
            trigger: "[name='account_id'] input",
            run: "text Bank Fees"
        },
        {
            content: "select the bank fees account",
            extra_trigger: ".o-autocomplete--dropdown-menu",
            trigger: ".o-autocomplete--dropdown-item:contains('Bank Fees')",
        },
        {
            content: "Breadcrumb back to Bank Reconciliation from the model",
            extra_trigger: ".breadcrumb-item:contains('New')",
            trigger: ".breadcrumb-item:contains('Bank Reconciliation')",
        },
        {
            content: "Choose Bank Fees Model",
            trigger: ".recon_model_button:contains('Bank Fees')",
        },
        {
            content: "Validate line3",
            extra_trigger: "button[name='button_validate']",
            trigger: "button[name='button_validate']",
        },
        {
            content: "Ensure validate button is disabled to prevent double-click",
            trigger: "button[name='button_validate'][disabled]",
            run: () => {}
        },
        {
            content: "Rainbow man",
            extra_trigger: ".o_view_nocontent",
            trigger: ".o_reward_rainbow_man",
            run: () => {}
        },
        // Test the next st line is always selected when Not Matched Filter is active
        {
            content: "Remove the kanbans st line filter",
            trigger: ".o_kanban_view .o_searchview_facet:nth-child(2) .o_facet_remove",
        },
        {
            content: "Remove the kanbans 'not matched' filter to reset all lines - use the rainbow man button",
            extra_trigger: ".o_kanban_view .o_searchview:first() .o_searchview_facet:nth-child(2):contains('Not Matched')",
            trigger: "p.btn-primary:contains('All Transactions')",
        },
        {
            content: "Wait for search model change and line3 to appear",
            extra_trigger: ".o_kanban_view .o_searchview:first() .o_searchview_facet:last():contains('Bank')",
            trigger: ".o_bank_rec_st_line:last():contains('line3')",
            run: () => {},
        },
        {
            content: "'line2' should be selected, reset it",
            extra_trigger: ".o_bank_rec_selected_st_line:contains('line2')",
            trigger: "button[name='button_reset']"
        },
        {
            content: "select matched 'line3'",
            trigger: ".o_bank_rec_st_line:contains('line3')",
        },
        {
            content: "'line3' should be selected, reset it",
            extra_trigger: ".o_bank_rec_selected_st_line:contains('line3')",
            trigger: "button[name='button_reset']"
        },
        {
            content: "select matched 'line1'",
            trigger: ".o_bank_rec_st_line:contains('line1')",
        },
        {
            content: "'line1' should be selected, reset it",
            extra_trigger: ".o_bank_rec_selected_st_line:contains('line1')",
            trigger: "button[name='button_reset']"
        },
        {
            content: "Filter Menu",
            extra_trigger: "button[name='button_validate']",
            trigger: ".o_filter_menu:first() i",
        },
        {
            content: "Activate the Not Matched filter",
            extra_trigger: ".o-dropdown--menu",
            trigger: ".dropdown-item:contains('Not Matched')",
        },
        {
            content: "Close the Filter Menu",
            extra_trigger: ".o_searchview_facet:contains('Not Matched')",
            trigger: ".o_filter_menu:first() i",
        },
        {
            content: "select 'line2'",
            extra_trigger: ".o_searchview_facet:contains('Not Matched')",
            trigger: ".o_bank_rec_st_line:contains('line2')",
        },
        {
            content: "Validate 'line2' again",
            extra_trigger: ".o_bank_rec_selected_st_line:contains('line2')",
            trigger: "button[name='button_validate']"
        },
        {
            content: "'line3' should be selected now",
            extra_trigger: ".o_bank_rec_selected_st_line:contains('line3')",
            trigger: ".o_bank_rec_selected_st_line:contains('line3')",
            run: () => {},
        },
        // Test the Balance when changing journal and liquidity line
        tour.stepUtils.toggleHomeMenu(),
        ...tour.stepUtils.goToAppSteps(
            'account_accountant.menu_accounting',
            "Reset back to accounting module"
        ),
        {
            content: "Open the bank reconciliation widget for Bank2",
            extra_trigger: ".breadcrumb",
            trigger: "button.btn-primary[name='action_open_reconcile']:last()",
        },
        {
            content: "Remove the kanbans 'not matched' filter",
            trigger: ".o_kanban_view .o_searchview_facet:nth-child(2) .o_facet_remove",
        },
        {
            content: "Remove the kanban 'journal' filter",
            trigger: ".o_kanban_view .o_searchview_facet:nth-child(1) .o_facet_remove",
        },
        {
            content: "select 'line1' from another journal",
            trigger: ".o_bank_rec_st_line:contains('line1')",
        },
        {
            content: "balance is 2100",
            extra_trigger: ".o_bank_rec_selected_st_line:contains('line1')",
            trigger: ".btn-secondary:contains('$ 2,100.00')",
        },
        {
            content: "Breadcrumb back to Bank Reconciliation from the report",
            trigger: ".breadcrumb-item a:contains('Bank Reconciliation')",
        },
        {
            content: "select 'line4' from this journal",
            trigger: ".o_bank_rec_st_line:contains('line4')",
        },
        {
            content: "balance is $222.22",
            extra_trigger: ".o_bank_rec_selected_st_line:contains('line4')",
            trigger: ".btn-secondary:contains('$ 222.22')",
            run: () => {},
        },
        {
            content: "Select the liquidity line",
            trigger: "tr.o_bank_rec_liquidity_line td[field='debit']",
        },
        {
            content: "Modify the liquidity line amount",
            extra_trigger: "div.tab-pane.active input[id='form_balance']:focus",
            trigger: "div.tab-pane.active input[id='form_balance']",
            run: "text -333.33",
        },
        {
            content: "balance displays $-333.33",
            extra_trigger: ".btn-secondary:contains('$ -333.33')",
            trigger: ".btn-secondary:contains('$ -333.33')",
            run: () => {},
        },
        {
            content: "Modify the label",
            trigger: "div.tab-pane.active input[id='form_name']",
            run: "text Spontaneous Combustion",
        },
        {
            content: "statement line displays combustion and $-333.33",
            extra_trigger: ".o_bank_rec_selected_st_line:contains('Combustion'):contains('$ -333.33')",
            trigger: ".o_bank_rec_selected_st_line:contains('Combustion'):contains('$ -333.33')",
            run: () => {},
        },
        // Test that changing the balance in the list view updates the right side of the kanban view
        // (including reapplying matching rules)
        {
            content: "select matched 'line2'",
            trigger: ".o_bank_rec_st_line:contains('line2')",
        },
        {
            content: "'line2' should be selected, reset it",
            extra_trigger: ".o_bank_rec_selected_st_line:contains('line2')",
            trigger: "button[name='button_reset']"
        },
        {
            content: "Liquidity line displays debit '$ 100.00'",
            extra_trigger: ".o_bank_rec_selected_st_line:contains('line2'):not(:has(div.badge))",
            trigger: "div[name='lines_widget'] table.o_list_table tr.o_bank_rec_liquidity_line td[field='debit']:contains('$ 100.00')",
            run: () => {},
        },
        {
            content: "Switch to list view",
            extra_trigger: ".o_switch_view.o_kanban.active",
            trigger: ".o_switch_view.o_list",
        },
        {
            content: "Click amount field of 'line2'; Selects the row",
            trigger: "table.o_list_table tr.o_data_row:contains('line2') td[name='amount']",
        },
        {
            content: "Set balance of 'line2' (selected row) to 500.00",
            trigger: "table.o_list_table tr.o_data_row.o_selected_row td[name='amount'] input",
            run: "text 500.00",
        },
        {
            content: "Switch back to kanban",
            extra_trigger: ".o_switch_view.o_list.active",
            trigger: ".o_switch_view.o_kanban",
        },
        {
            content: "'line2' is still selected",
            trigger: ".o_bank_rec_st_line:contains('line2')",
            run: () => {},
        },
        {
            content: "Liquidity line displays debit '$ 500.00'",
            trigger: "div[name='lines_widget'] table.o_list_table tr.o_bank_rec_liquidity_line td[field='debit']:contains('$ 500.00')",
            run: () => {},
        },
        {
            content: "'INV/2019/00001' has been selected as a matching existing entry by matching rules (matching rules were triggered)",
            trigger: "div.o_widget_bank_rec_form_list table.o_list_table tr.o_rec_widget_list_selected_item td[name='name']:contains('INV/2019/00001')",
            run: () => {},
        },
        // End
        tour.stepUtils.toggleHomeMenu(),
        ...tour.stepUtils.goToAppSteps(
            'account_accountant.menu_accounting',
            "Reset back to accounting module"
        ),
        {
            content: "check that we're back on the dashboard",
            trigger: 'a:contains("Customer Invoices")',
            run() {},
        }
    ]
);
